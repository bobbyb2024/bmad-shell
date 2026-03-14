import asyncio
import json
import os
import re
import shutil
import subprocess
import time
from collections.abc import AsyncIterator
from typing import Any
from dataclasses import replace

from bmad_orch.exceptions import ProviderCrashError, ProviderError, ProviderTimeoutError, ProviderTransientError
from bmad_orch.providers.base import ProviderAdapter
from bmad_orch.providers.utils import spawn_pty_process
from bmad_orch.types import OutputChunk


class ClaudeAdapter(ProviderAdapter):
    """Adapter for official Claude CLI (claude-code)."""

    install_hint: str = "npm install -g @anthropic-ai/claude-code"
    
    _cli_path: str | None = None
    _cli_version: str = "unknown"

    def __init__(self, **config: Any) -> None:
        self.config = config
        # Regex for AC7: Corrupted/HTML Provider Output
        self._corruption_patterns = [
            re.compile(r"<html>", re.IGNORECASE),
            re.compile(r"502 Bad Gateway", re.IGNORECASE),
            re.compile(r"Cloudflare", re.IGNORECASE),
        ]

    def detect(self, cli_path: str | None = None) -> bool:
        """Detect if the 'claude' command is available on the system."""
        # AC1: Use provided cli_path or default "claude"
        target = cli_path or "claude"
        path = shutil.which(target)
        if path:
            # We only cache the path if it's the default or if we don't have one yet
            # but for simplicity we'll cache the last detected successful path.
            ClaudeAdapter._cli_path = path
            try:
                # Use absolute path found by which
                version_out = subprocess.check_output([path, "--version"], stderr=subprocess.STDOUT)  # noqa: S603
                ClaudeAdapter._cli_version = version_out.decode().strip()
            except (subprocess.SubprocessError, UnicodeDecodeError):
                ClaudeAdapter._cli_version = "unknown-claude-cli"
            return True
        return False

    def list_models(self) -> list[dict[str, Any]]:
        """List available models for Claude. AC2: Discover via CLI with fallback."""
        # Attempt to discover models via CLI
        path = self.config.get("cli") or ClaudeAdapter._cli_path or shutil.which("claude")
        if path:
            try:
                # Early versions of 'claude' CLI might use 'models list' or similar.
                output = subprocess.check_output([path, "models", "list", "--json"], stderr=subprocess.STDOUT)  # noqa: S603
                models = json.loads(output)
                if isinstance(models, list) and len(models) > 0 and all(isinstance(m, dict) and "id" in m for m in models):
                    return models
            except (subprocess.SubprocessError, json.JSONDecodeError, UnicodeDecodeError):
                pass

        # Fallback list as mandated by AC2.
        fallback = self.config.get("default_models") or [
            {"id": "claude-3-5-sonnet-latest", "name": "Claude 3.5 Sonnet"},
            {"id": "claude-3-opus-latest", "name": "Claude 3 Opus"}
        ]
        return fallback

    async def _execute(self, prompt: str, **kwargs: Any) -> AsyncIterator[OutputChunk]:
        """Implementation of prompt execution via spawn_pty_process. AC3-8."""
        model = kwargs.get("model") or self.config.get("model") or "claude-3-5-sonnet-latest"
        api_key = kwargs.get("api_key") or self.config.get("api_key") or os.environ.get("ANTHROPIC_API_KEY")
        
        if not api_key:
            raise ProviderError("ANTHROPIC_API_KEY environment variable is mandatory for ClaudeAdapter.")

        # Construct env dict per AC3 (mandatory + optional)
        env = {
            "PATH": os.environ.get("PATH", ""),
            "HOME": os.environ.get("HOME", ""),
            "LANG": os.environ.get("LANG", ""),
        }
        env["ANTHROPIC_API_KEY"] = api_key
        
        log_level = self.config.get("log_level") or os.environ.get("CLAUDE_LOG_LEVEL")
        if log_level:
            env["CLAUDE_LOG_LEVEL"] = log_level
        
        # Use config'd cli path, cached path, or "claude"
        executable = self.config.get("cli") or ClaudeAdapter._cli_path or "claude"
        cmd = [executable, "--model", model, prompt]
        
        timeout = float(kwargs.get("timeout") or self.config.get("timeout", 60.0))
        
        # AC8: Configurable grace period (config -> env -> default)
        try:
            grace_period = float(
                self.config.get("termination_grace_period") 
                or os.environ.get("CLAUDE_TERMINATION_GRACE_PERIOD", 2.0)
            )
        except (ValueError, TypeError):
            grace_period = 2.0

        # AC9: Exponential backoff retry logic (config -> env -> default)
        try:
            max_retries = int(
                self.config.get("max_retries") 
                or os.environ.get("CLAUDE_MAX_RETRIES", 0)
            )
        except (ValueError, TypeError):
            max_retries = 0
            
        try:
            backoff_factor = float(
                self.config.get("retry_backoff_factor") 
                or os.environ.get("CLAUDE_RETRY_BACKOFF_FACTOR", 2.0)
            )
        except (ValueError, TypeError):
            backoff_factor = 2.0
            
        try:
            initial_delay = float(
                self.config.get("retry_initial_delay") 
                or os.environ.get("CLAUDE_RETRY_INITIAL_DELAY", 1.0)
            )
        except (ValueError, TypeError):
            initial_delay = 1.0

        # Prepare base metadata once to ensure stable execution_id across retries. AC4.
        base_meta = self._get_base_metadata(**kwargs)
        # Inject execution_id back into kwargs so the base class uses the same one.
        kwargs["execution_id"] = base_meta["execution_id"]
        
        # Shared execution metadata
        execution_meta = {
            **base_meta,
            "provider": "claude",
            "model": model,
            "version": ClaudeAdapter._cli_version,
        }

        attempts = 0
        while True:
            attempts += 1
            # AC7: Defensive Parsing state
            buffer_checked_count = 0
            initial_buffer = ""
            sliding_window = ""
            # Window size should be enough to catch split patterns (max pattern is ~20 chars)
            window_size = 128 

            # Attempt-specific metadata
            current_meta = {**execution_meta, "attempt": attempts}

            try:
                async for chunk in spawn_pty_process(cmd, timeout=timeout, env=env, grace_period=grace_period):
                    # AC7: Defensive Parsing
                    content = chunk.content
                    
                    # 1. Accumulation for first 2KB
                    if buffer_checked_count < 2048:
                        initial_buffer += content
                        buffer_checked_count = len(initial_buffer)
                        check_text = initial_buffer
                    else:
                        # 2. Sliding window check to prevent split-chunk misses
                        check_text = sliding_window + content
                    
                    # Update window for next chunk
                    sliding_window = (sliding_window + content)[-window_size:]

                    # Regex checks
                    for pattern in self._corruption_patterns:
                        if pattern.search(check_text):
                            raise ProviderTransientError(f"Transient Provider Error detected: {pattern.pattern}")

                    # Binary check
                    if "\x00" in content:
                        raise ProviderError("Impactful Provider Error (binary detected).")

                    # AC4: Merge metadata
                    new_metadata = {**current_meta, **chunk.metadata}
                    chunk = replace(chunk, metadata=new_metadata)
                    
                    yield chunk

                # AC5: Successful completion
                yield OutputChunk(
                    content="",
                    timestamp=time.time(),
                    metadata={**current_meta, "status": "completed"}
                )
                break 

            except asyncio.CancelledError:
                raise
            except (ProviderTimeoutError, ProviderCrashError, ProviderTransientError) as e:
                # AC6: Append version info
                msg = f"{e} (Claude CLI Version: {ClaudeAdapter._cli_version})"
                
                # AC9: Retry logic for both crash (non-zero exit) and transient (parsed) errors
                is_retryable = isinstance(e, (ProviderCrashError, ProviderTransientError))
                if is_retryable and attempts <= max_retries:
                    delay = initial_delay * (backoff_factor ** (attempts - 1))
                    await asyncio.sleep(delay)
                    continue

                if isinstance(e, ProviderTimeoutError):
                    raise ProviderTimeoutError(msg) from e
                if isinstance(e, ProviderTransientError):
                    raise ProviderTransientError(msg) from e
                raise ProviderCrashError(msg) from e
