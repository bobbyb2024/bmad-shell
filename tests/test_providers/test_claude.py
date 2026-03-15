from unittest.mock import patch

import pytest

from bmad_orch.exceptions import ProviderCrashError, ProviderError, ProviderTimeoutError, ProviderTransientError
from bmad_orch.providers.claude import ClaudeAdapter
from bmad_orch.types import OutputChunk


@pytest.fixture(autouse=True)
def _reset_claude_class_state():
    """Reset class-level state between tests."""
    yield
    ClaudeAdapter._cli_path = None
    ClaudeAdapter._cli_version = "unknown"

def test_detect_success():
    with patch("shutil.which", return_value="/usr/local/bin/claude"):
        with patch("subprocess.check_output") as mock_exec:
            mock_exec.return_value = b"claude 0.1.0\n"
            adapter = ClaudeAdapter()
            assert adapter.detect() is True
            assert ClaudeAdapter._cli_path == "/usr/local/bin/claude"
            assert ClaudeAdapter._cli_version == "claude 0.1.0"

def test_detect_failure():
    with patch("shutil.which", return_value=None):
        adapter = ClaudeAdapter()
        assert adapter.detect() is False

def test_list_models_fallback():
    adapter = ClaudeAdapter()
    with patch("shutil.which", return_value=None):
        models = adapter.list_models()
        assert len(models) == 2
        assert models[0]["id"] == "claude-3-5-sonnet-latest"

@pytest.mark.asyncio
async def test_execute_auth_propagation():
    adapter = ClaudeAdapter()
    with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}, clear=False):
        mock_chunks = [OutputChunk(content="Hello", timestamp=1.0)]
        async def mock_spawn(*args, **kwargs):
            assert kwargs["env"]["ANTHROPIC_API_KEY"] == "test-key"
            for c in mock_chunks:
                yield c

        with patch("bmad_orch.providers.claude.spawn_pty_process", side_effect=mock_spawn):
            chunks = []
            async for chunk in adapter.execute("test prompt"):
                chunks.append(chunk)

            assert len(chunks) == 2 # Data chunk + Completion chunk
            assert chunks[0].content == "Hello"
            assert chunks[1].metadata["status"] == "completed"

@pytest.mark.asyncio
async def test_execute_no_api_key():
    adapter = ClaudeAdapter()
    with patch.dict("os.environ", {}, clear=True):
        with pytest.raises(ProviderError, match="ANTHROPIC_API_KEY environment variable is mandatory"):
            async for _ in adapter.execute("test prompt"):
                pass

@pytest.mark.asyncio
async def test_execute_defensive_parsing_html():
    adapter = ClaudeAdapter()
    with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}, clear=False):
        mock_chunks = [OutputChunk(content="<html><body>Error</body></html>", timestamp=1.0)]
        async def mock_spawn(*args, **kwargs):
            for c in mock_chunks:
                yield c

        with patch("bmad_orch.providers.claude.spawn_pty_process", side_effect=mock_spawn):
            with pytest.raises(ProviderTransientError, match="Transient Provider Error detected: <html>"):
                async for _ in adapter.execute("test prompt"):
                    pass

@pytest.mark.asyncio
async def test_execute_defensive_parsing_binary():
    adapter = ClaudeAdapter()
    with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}, clear=False):
        mock_chunks = [OutputChunk(content="Some data \x00 corrupted", timestamp=1.0)]
        async def mock_spawn(*args, **kwargs):
            for c in mock_chunks:
                yield c

        with patch("bmad_orch.providers.claude.spawn_pty_process", side_effect=mock_spawn):
            with pytest.raises(ProviderError, match=r"Impactful Provider Error \(binary detected\)."):
                async for _ in adapter.execute("test prompt"):
                    pass

@pytest.mark.asyncio
async def test_execute_timeout_cleanup():
    adapter = ClaudeAdapter()
    ClaudeAdapter._cli_version = "v1.2.3"
    with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}, clear=False):
        async def mock_spawn(*args, **kwargs):
            raise ProviderTimeoutError("Timeout")
            yield

        with patch("bmad_orch.providers.claude.spawn_pty_process", side_effect=mock_spawn):
            with pytest.raises(ProviderTimeoutError, match="v1.2.3"):
                async for _ in adapter.execute("test prompt"):
                    pass

@pytest.mark.asyncio
async def test_execute_crash_cleanup():
    adapter = ClaudeAdapter()
    ClaudeAdapter._cli_version = "v1.2.3"
    with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}, clear=False):
        async def mock_spawn(*args, **kwargs):
            raise ProviderCrashError("Crash")
            yield

        with patch("bmad_orch.providers.claude.spawn_pty_process", side_effect=mock_spawn):
            with pytest.raises(ProviderCrashError, match="v1.2.3"):
                async for _ in adapter.execute("test prompt"):
                    pass
