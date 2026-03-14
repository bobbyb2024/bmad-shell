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


class GeminiAdapter(ProviderAdapter):
    """Adapter for Gemini CLI (gemini)."""

    install_hint: str = "npm install -g @google/gemini-cli"

    _cli_path: str | None = None
    _cli_version: str = "Version Unknown"

    def __init__(self, **config: Any) -> None:
        self.config = config
        # Regex for AC7: Corrupted/Provider Error
        self._corruption_patterns = [
            re.compile(r"<html>", re.IGNORECASE),
            re.compile(r"502 Bad Gateway", re.IGNORECASE),
            re.compile(r"Cloudflare", re.IGNORECASE),
            re.compile(r"403 Forbidden", re.IGNORECASE),
            re.compile(r"PERMISSION_DENIED", re.IGNORECASE),
        ]

    def detect(self, cli_path: str | None = None) -> bool:
        """Detect if the 'gemini' command is available on the system. AC1."""
        target = cli_path or "gemini"
        path = shutil.which(target)
        if path:
            GeminiAdapter._cli_path = path
            try:
                # Use absolute path found by which
                version_out = subprocess.check_output([path, "--version"], stderr=subprocess.STDOUT)  # noqa: S603
                GeminiAdapter._cli_version = version_out.decode().strip()
            except (subprocess.SubprocessError, UnicodeDecodeError):
                GeminiAdapter._cli_version = "Version Unknown"
            return True
        return False

    def list_models(self) -> list[dict[str, Any]]:
        """List available models for Gemini. AC2: Discover via CLI with fallback."""
        path = GeminiAdapter._cli_path or shutil.which("gemini")
        if path:
            try:
                # Attempt to discover models via CLI
                output = subprocess.check_output([path, "models", "list", "--json"], stderr=subprocess.STDOUT)  # noqa: S603
                models = json.loads(output)
                if isinstance(models, list) and len(models) > 0 and all(isinstance(m, dict) and "id" in m for m in models):
                    return models
            except subprocess.CalledProcessError as e:
                # AC2: If subcommand is missing or unavailable, fallback.
                # Usually, exit code 127 or 1 with specific error message indicates missing subcommand.
                err_msg = e.output.decode(errors="replace").lower() if e.output else ""
                if e.returncode == 127 or "unknown command" in err_msg or "invalid command" in err_msg:
                    pass # Proceed to fallback
                else:
                    raise ProviderError(f"Gemini CLI models list failed (exit {e.returncode}): {err_msg}") from e
            except (json.JSONDecodeError, UnicodeDecodeError) as e:
                raise ProviderError(f"Gemini CLI returned malformed JSON: {e}") from e
            except subprocess.SubprocessError as e:
                raise ProviderError(f"Gemini CLI execution failed: {e}") from e

        # Fallback list as mandated by AC2. Configurable via adapter config.
        fallback = self.config.get("default_models") or [
            {"id": "gemini-1.5-flash", "name": "Gemini 1.5 Flash"},
            {"id": "gemini-1.5-pro", "name": "Gemini 1.5 Pro"}
        ]
        return fallback

    async def _execute(self, prompt: str, **kwargs: Any) -> AsyncIterator[OutputChunk]:
        """Implementation of prompt execution via spawn_pty_process. AC3-8."""
        model = kwargs.get("model") or self.config.get("model") or "gemini-1.5-flash"
        
        # AC3: Check kwargs, config, and environment
        api_key = (
            kwargs.get("api_key") 
            or self.config.get("api_key") 
            or os.environ.get("GEMINI_API_KEY") 
            or os.environ.get("GOOGLE_API_KEY")
        )
        
        if not api_key:
            raise ProviderError("GEMINI_API_KEY or GOOGLE_API_KEY environment variable is mandatory for GeminiAdapter.")

        # Construct env dict per AC3
        env = {
            "PATH": os.environ.get("PATH", ""),
            "HOME": os.environ.get("HOME", ""),
            "LANG": os.environ.get("LANG", ""),
        }
        env["GEMINI_API_KEY"] = api_key
        env["GOOGLE_API_KEY"] = api_key
            
        executable = GeminiAdapter._cli_path or "gemini"
        cmd = [executable, "--model", model, "--", prompt]
        
        timeout = float(kwargs.get("timeout") or self.config.get("timeout", 60.0))
        
        # AC8: Configurable grace period (config -> env -> default)
        try:
            grace_period = float(
                self.config.get("termination_grace_period") 
                or os.environ.get("GEMINI_TERMINATION_GRACE_PERIOD", 2.0)
            )
        except (ValueError, TypeError):
            grace_period = 2.0
            
        # AC9: Exponential backoff retry logic (config -> env -> default)
        try:
            max_retries = int(
                self.config.get("max_retries") 
                or os.environ.get("GEMINI_MAX_RETRIES", 0)
            )
        except (ValueError, TypeError):
            max_retries = 0
            
        try:
            backoff_factor = float(
                self.config.get("retry_backoff_factor") 
                or os.environ.get("GEMINI_RETRY_BACKOFF_FACTOR", 2.0)
            )
        except (ValueError, TypeError):
            backoff_factor = 2.0
            
        try:
            initial_delay = float(
                self.config.get("retry_initial_delay") 
                or os.environ.get("GEMINI_RETRY_INITIAL_DELAY", 1.0)
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
            "provider": "gemini",
            "model": model,
            "version": GeminiAdapter._cli_version,
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
                            # Distinguish between transient and impactful patterns
                            if any(p in pattern.pattern.upper() for p in ["403", "PERMISSION_DENIED"]):
                                raise ProviderError(f"Impactful Provider Error detected: {pattern.pattern}")
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
                msg = f"{e} (Gemini CLI Version: {GeminiAdapter._cli_version})"
                
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

