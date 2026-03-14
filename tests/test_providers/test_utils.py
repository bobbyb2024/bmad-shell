import pytest
import asyncio
import os
import sys
from bmad_orch.providers.utils import spawn_pty_process
from bmad_orch.exceptions import ProviderTimeoutError, ProviderCrashError
from bmad_orch.types import OutputChunk


def test_spawn_pty_process_success():
    async def run_test():
        # Simple echo command
        chunks = []
        async for chunk in spawn_pty_process(["echo", "hello world"]):
            chunks.append(chunk)

        assert any("hello world" in c.content for c in chunks)
        assert all(isinstance(c, OutputChunk) for c in chunks)

    asyncio.run(run_test())


def test_spawn_pty_process_timeout():
    async def run_test():
        # Sleep command that will exceed timeout
        with pytest.raises(ProviderTimeoutError):
            async for _ in spawn_pty_process(["sleep", "10"], timeout=0.1):
                pass

    asyncio.run(run_test())


def test_spawn_pty_process_crash():
    async def run_test():
        # Command that exits with non-zero
        with pytest.raises(ProviderCrashError):
            async for _ in spawn_pty_process(["false"]):
                pass

    asyncio.run(run_test())


def test_spawn_pty_process_decoding():
    async def run_test():
        # Test that it decodes UTF-8
        # We use python to write raw bytes to stdout
        python_cmd = [sys.executable, "-c", "import sys; sys.stdout.buffer.write(b'hello \\xc3\\xa9'); sys.stdout.buffer.flush()"]
        chunks = []
        async for chunk in spawn_pty_process(python_cmd):
            chunks.append(chunk)

        full_text = "".join(c.content for c in chunks)
        assert "hello é" in full_text

    asyncio.run(run_test())


def test_spawn_pty_process_non_posix(monkeypatch):
    """AC6: Non-POSIX platforms must raise NotImplementedError."""
    monkeypatch.setattr(os, "name", "nt")

    async def run_test():
        with pytest.raises(NotImplementedError):
            async for _ in spawn_pty_process(["echo", "hello"]):
                pass

    asyncio.run(run_test())


def test_spawn_pty_process_ansi_preservation():
    """AC6: OutputChunk must preserve all ANSI escape sequences."""
    async def run_test():
        # Emit ANSI color codes via python subprocess
        python_cmd = [
            sys.executable, "-c",
            r"print('\033[31mRED\033[0m \033[1mBOLD\033[0m')"
        ]
        chunks = []
        async for chunk in spawn_pty_process(python_cmd):
            chunks.append(chunk)

        full_text = "".join(c.content for c in chunks)
        assert "\033[31m" in full_text
        assert "\033[0m" in full_text
        assert "\033[1m" in full_text

    asyncio.run(run_test())
