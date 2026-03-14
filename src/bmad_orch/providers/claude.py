import asyncio
import json
import os
import re
import shutil
import subprocess
from collections.abc import AsyncIterator
from typing import Any

from bmad_orch.exceptions import ProviderCrashError, ProviderError, ProviderTimeoutError
from bmad_orch.providers.base import ProviderAdapter
from bmad_orch.providers.utils import spawn_pty_process
from bmad_orch.types import OutputChunk


class ClaudeAdapter(ProviderAdapter):
    """Adapter for official Claude CLI (claude-code)."""

    def __init__(self) -> None:
        self._version = "unknown"
        # Regex for AC7: Corrupted/HTML Provider Output
        self._corruption_patterns = [
            re.compile(r"<html>", re.IGNORECASE),
            re.compile(r"502 Bad Gateway", re.IGNORECASE),
            re.compile(r"Cloudflare", re.IGNORECASE),
        ]

    def detect(self) -> bool:
        """Detect if the 'claude' command is available on the system."""
        path = shutil.which("claude")
        if path:
            try:
                # Use absolute path found by which
                version_out = subprocess.check_output([path, "--version"], stderr=subprocess.STDOUT)  # noqa: S603
                self._version = version_out.decode().strip()
            except (subprocess.SubprocessError, UnicodeDecodeError):
                self._version = "unknown-claude-cli"
            return True
        return False

    def list_models(self) -> list[dict[str, Any]]:
        """List available models for Claude. AC2: Discover via CLI with fallback."""
        # Attempt to discover models via CLI
        path = shutil.which("claude")
        if path:
            try:
                # Early versions of 'claude' CLI might use 'models list' or similar.
                # If command fails or returns malformed output, we fallback per AC2.
                # Using a generic command that might exist, if not, it will fail and we fallback.
                output = subprocess.check_output([path, "models", "list", "--json"], stderr=subprocess.STDOUT)  # noqa: S603
                # Hypothetical JSON parsing
                models = json.loads(output)
                if isinstance(models, list) and all(isinstance(m, dict) and "id" in m for m in models):
                    return models
            except (subprocess.SubprocessError, json.JSONDecodeError, UnicodeDecodeError):
                pass

        # Fallback list as mandated by AC2.
        fallback = [
            {"id": "claude-3-5-sonnet-latest", "name": "Claude 3.5 Sonnet"},
            {"id": "claude-3-opus-latest", "name": "Claude 3 Opus"}
        ]
        return fallback

    async def _execute(self, prompt: str, **kwargs: Any) -> AsyncIterator[OutputChunk]:
        """Implementation of prompt execution via spawn_pty_process. AC3-8."""
        model = kwargs.get("model", "claude-3-5-sonnet-latest")
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        
        if not api_key:
            raise ProviderError("ANTHROPIC_API_KEY environment variable is mandatory for ClaudeAdapter.")

        env = {**os.environ}
        env["ANTHROPIC_API_KEY"] = api_key
        log_level = os.environ.get("CLAUDE_LOG_LEVEL")
        if log_level:
            env["CLAUDE_LOG_LEVEL"] = log_level
        
        # Merge other env vars if needed or just keep it tight per AC3
        cmd = ["claude", "--model", model, prompt]
        
        timeout = float(kwargs.get("timeout", 60.0))
        
        # Safe float conversion for grace period
        try:
            grace_period = float(os.environ.get("CLAUDE_TERMINATION_GRACE_PERIOD", 2.0))
        except ValueError:
            grace_period = 2.0
            
        buffer_checked = False
        initial_buffer = ""

        try:
            async for chunk in spawn_pty_process(cmd, timeout=timeout, env=env, grace_period=grace_period):
                # AC7: Defensive Parsing (only for the first 1KB)
                if not buffer_checked:
                    initial_buffer += chunk.content
                    for pattern in self._corruption_patterns:
                        if pattern.search(initial_buffer):
                            raise ProviderError("Corrupted/HTML Provider Output detected.")
                    if "\x00" in initial_buffer:
                        raise ProviderError("Corrupted/HTML Provider Output (binary detected).")
                    if len(initial_buffer) >= 1024:
                        buffer_checked = True

                # Yield the chunk
                yield chunk

        except asyncio.CancelledError:
            # AC8: Graceful Cancellation handled partially by spawn_pty_process 
            # but we need to ensure we follow the specific requirements for ClaudeAdapter.
            # spawn_pty_process already does SIGTERM/SIGKILL, but let's make it explicit here if we want 
            # to override grace periods.
            raise
        except (ProviderTimeoutError, ProviderCrashError) as e:
            # AC6: Append version info to exception
            msg = f"{e} (Claude CLI Version: {self._version})"
            if isinstance(e, ProviderTimeoutError):
                raise ProviderTimeoutError(msg) from e
            raise ProviderCrashError(msg) from e
