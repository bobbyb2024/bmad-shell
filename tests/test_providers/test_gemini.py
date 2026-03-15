import asyncio
import os
import subprocess
from unittest.mock import patch

import pytest

from bmad_orch.exceptions import ProviderCrashError, ProviderError, ProviderTimeoutError, ProviderTransientError
from bmad_orch.providers.gemini import GeminiAdapter
from bmad_orch.types import OutputChunk


@pytest.fixture(autouse=True)
def _reset_gemini_class_state():
    """Reset class-level state between tests to prevent leakage."""
    yield
    GeminiAdapter._cli_path = None
    GeminiAdapter._cli_version = "Version Unknown"

def test_detect_success():
    with patch("shutil.which", return_value="/usr/bin/gemini"):
        with patch("subprocess.check_output") as mock_exec:
            mock_exec.return_value = b"gemini version 1.0.0\n"
            adapter = GeminiAdapter() # Should work without kwargs
            assert adapter.detect() is True
            assert GeminiAdapter._cli_path == "/usr/bin/gemini"
            assert GeminiAdapter._cli_version == "gemini version 1.0.0"
            mock_exec.assert_called_with(["/usr/bin/gemini", "--version"], stderr=subprocess.STDOUT)

def test_instantiation_with_config():
    config = {"some": "config", "default_models": [{"id": "m1"}]}
    adapter = GeminiAdapter(**config)
    assert adapter.config == config

def test_list_models_configurable_fallback():
    custom_models = [{"id": "custom-model", "name": "Custom Model"}]
    adapter = GeminiAdapter(default_models=custom_models)
    with patch("shutil.which", return_value=None):
        models = adapter.list_models()
        assert models == custom_models

def test_list_models_raise_on_real_failure():
    adapter = GeminiAdapter()
    with patch("shutil.which", return_value="/usr/bin/gemini"):
        # Not a 127 or "unknown command" error
        err = subprocess.CalledProcessError(1, "cmd", output=b"Fatal internal error")
        with patch("subprocess.check_output", side_effect=err):
            with pytest.raises(ProviderError, match="Gemini CLI models list failed"):
                adapter.list_models()

def test_list_models_raise_on_malformed_json():
    adapter = GeminiAdapter()
    with patch("shutil.which", return_value="/usr/bin/gemini"):
        with patch("subprocess.check_output", return_value=b"not json"):
            with pytest.raises(ProviderError, match="malformed JSON"):
                adapter.list_models()

def test_list_models_fallback_on_missing_subcommand():
    adapter = GeminiAdapter()
    with patch("shutil.which", return_value="/usr/bin/gemini"):
        # 127 is standard for command not found (or subcommand not found in some shells/wrappers)
        err = subprocess.CalledProcessError(127, "cmd", output=b"")
        with patch("subprocess.check_output", side_effect=err):
            models = adapter.list_models()
            assert len(models) == 2 # Standard fallback

        # Also check "unknown command" in output
        err = subprocess.CalledProcessError(1, "cmd", output=b"Error: unknown command 'models'")
        with patch("subprocess.check_output", side_effect=err):
            models = adapter.list_models()
            assert len(models) == 2

def test_detect_failure():
    with patch("shutil.which", return_value=None):
        adapter = GeminiAdapter()
        assert adapter.detect() is False

def test_list_models_fallback():
    adapter = GeminiAdapter()
    with patch("shutil.which", return_value="/usr/bin/gemini"):
        # Use 127 to trigger fallback
        with patch("subprocess.check_output", side_effect=subprocess.CalledProcessError(127, "cmd")):
            models = adapter.list_models()
            assert len(models) >= 2
            ids = [m["id"] for m in models]
            assert any("flash" in id.lower() for id in ids)
            assert any("pro" in id.lower() for id in ids)

def test_list_models_success():
    adapter = GeminiAdapter()
    with patch("shutil.which", return_value="/usr/bin/gemini"):
        with patch("subprocess.check_output") as mock_exec:
            mock_exec.return_value = b'[{"id": "gemini-1.5-flash", "name": "Gemini 1.5 Flash"}]'
            models = adapter.list_models()
            assert len(models) == 1
            assert models[0]["id"] == "gemini-1.5-flash"

@pytest.mark.asyncio
async def test_execute_auth_propagation_gemini_key():
    adapter = GeminiAdapter()
    with patch.dict("os.environ", {"GEMINI_API_KEY": "gemini-test-key"}, clear=False):
        async def mock_spawn(*args, **kwargs):
            assert kwargs["env"]["GEMINI_API_KEY"] == "gemini-test-key"
            assert kwargs["env"]["GOOGLE_API_KEY"] == "gemini-test-key"
            assert "PATH" in kwargs["env"]
            yield OutputChunk(content="Hello", timestamp=1.0)

        with patch("bmad_orch.providers.gemini.spawn_pty_process", side_effect=mock_spawn):
            chunks = []
            async for chunk in adapter.execute("test prompt"):
                chunks.append(chunk)
            assert len(chunks) == 2
            assert chunks[0].content == "Hello"
            assert chunks[1].content == ""
            assert chunks[1].metadata["status"] == "completed"

@pytest.mark.asyncio
async def test_execute_auth_propagation_google_key():
    adapter = GeminiAdapter()
    # Build env with only GOOGLE_API_KEY, explicitly excluding GEMINI_API_KEY
    clean_env = {k: v for k, v in os.environ.items() if k != "GEMINI_API_KEY"}
    clean_env["GOOGLE_API_KEY"] = "google-test-key"
    with patch.dict("os.environ", clean_env, clear=True):
        async def mock_spawn(*args, **kwargs):
            assert kwargs["env"]["GEMINI_API_KEY"] == "google-test-key"
            assert kwargs["env"]["GOOGLE_API_KEY"] == "google-test-key"
            yield OutputChunk(content="Hello", timestamp=1.0)

        with patch("bmad_orch.providers.gemini.spawn_pty_process", side_effect=mock_spawn):
            chunks = []
            async for chunk in adapter.execute("test prompt"):
                chunks.append(chunk)
            assert len(chunks) == 2
            assert chunks[0].content == "Hello"
            assert chunks[1].metadata["status"] == "completed"

@pytest.mark.asyncio
async def test_execute_no_api_key():
    adapter = GeminiAdapter()
    with patch.dict("os.environ", {}, clear=True):
        with pytest.raises(ProviderError, match="GEMINI_API_KEY or GOOGLE_API_KEY environment variable is mandatory"):
            async for _ in adapter.execute("test prompt"):
                pass

@pytest.mark.asyncio
async def test_execute_metadata_merging():
    adapter = GeminiAdapter()
    GeminiAdapter._cli_version = "gemini 1.0"
    with patch.dict("os.environ", {"GEMINI_API_KEY": "key"}, clear=False):
        async def mock_spawn(*args, **kwargs):
            yield OutputChunk(content="Hi", timestamp=1.0, metadata={"some": "meta"})

        with patch("bmad_orch.providers.gemini.spawn_pty_process", side_effect=mock_spawn):
            chunks = []
            async for chunk in adapter.execute("test prompt", execution_id="exec-123", model="gemini-flash"):
                chunks.append(chunk)
            
            assert len(chunks) == 2
            meta = chunks[0].metadata
            assert meta["execution_id"] == "exec-123"
            assert meta["model"] == "gemini-flash"
            assert meta["provider"] == "gemini"
            assert meta["version"] == "gemini 1.0"
            assert meta["some"] == "meta"
            
            assert chunks[1].metadata["status"] == "completed"
            assert chunks[1].metadata["execution_id"] == "exec-123"

@pytest.mark.asyncio
async def test_execute_defensive_parsing_html():
    adapter = GeminiAdapter()
    with patch.dict("os.environ", {"GEMINI_API_KEY": "key"}, clear=False):
        async def mock_spawn(*args, **kwargs):
            yield OutputChunk(content="<html><body>502 Bad Gateway</body></html>", timestamp=1.0)

        with patch("bmad_orch.providers.gemini.spawn_pty_process", side_effect=mock_spawn):
            with pytest.raises(ProviderTransientError, match="Transient Provider Error detected: <html>"):
                async for _ in adapter.execute("test prompt"):
                    pass

@pytest.mark.asyncio
async def test_execute_defensive_parsing_cloudflare():
    adapter = GeminiAdapter()
    with patch.dict("os.environ", {"GEMINI_API_KEY": "key"}, clear=False):
        async def mock_spawn(*args, **kwargs):
            yield OutputChunk(content="Cloudflare error occurred", timestamp=1.0)

        with patch("bmad_orch.providers.gemini.spawn_pty_process", side_effect=mock_spawn):
            with pytest.raises(ProviderTransientError, match="Transient Provider Error detected: Cloudflare"):
                async for _ in adapter.execute("test prompt"):
                    pass

@pytest.mark.asyncio
async def test_execute_defensive_parsing_permission_denied():
    adapter = GeminiAdapter()
    with patch.dict("os.environ", {"GEMINI_API_KEY": "key"}, clear=False):
        async def mock_spawn(*args, **kwargs):
            yield OutputChunk(content="Error: PERMISSION_DENIED", timestamp=1.0)

        with patch("bmad_orch.providers.gemini.spawn_pty_process", side_effect=mock_spawn):
            with pytest.raises(ProviderError, match="Impactful Provider Error detected: PERMISSION_DENIED"):
                async for _ in adapter.execute("test prompt"):
                    pass

@pytest.mark.asyncio
async def test_execute_grace_period():
    adapter = GeminiAdapter()
    with patch.dict("os.environ", {
        "GEMINI_API_KEY": "key",
        "GEMINI_TERMINATION_GRACE_PERIOD": "3.0"
    }, clear=False):
        async def mock_spawn(*args, **kwargs):
            assert kwargs["grace_period"] == 3.0
            yield OutputChunk(content="Ok", timestamp=1.0)

        with patch("bmad_orch.providers.gemini.spawn_pty_process", side_effect=mock_spawn):
            async for _ in adapter.execute("test prompt"):
                pass

@pytest.mark.asyncio
async def test_execute_crash_cleanup():
    adapter = GeminiAdapter()
    GeminiAdapter._cli_version = "v1.2.3"
    with patch.dict("os.environ", {"GEMINI_API_KEY": "key"}, clear=False):
        async def mock_spawn(*args, **kwargs):
            raise ProviderCrashError("Crash")
            yield

        with patch("bmad_orch.providers.gemini.spawn_pty_process", side_effect=mock_spawn):
            with pytest.raises(ProviderCrashError, match="v1.2.3"):
                async for _ in adapter.execute("test prompt"):
                    pass

@pytest.mark.asyncio
async def test_execute_completion_chunk():
    adapter = GeminiAdapter()
    with patch.dict("os.environ", {"GEMINI_API_KEY": "key"}, clear=False):
        async def mock_spawn(*args, **kwargs):
            yield OutputChunk(content="Done", timestamp=1.0)

        with patch("bmad_orch.providers.gemini.spawn_pty_process", side_effect=mock_spawn):
            chunks = []
            async for chunk in adapter.execute("test prompt"):
                chunks.append(chunk)
            
            assert len(chunks) == 2
            assert chunks[0].content == "Done"
            assert chunks[1].content == ""
            assert chunks[1].metadata["status"] == "completed"

def test_detect_version_error():
    with patch("shutil.which", return_value="/usr/bin/gemini"):
        with patch("subprocess.check_output", side_effect=subprocess.SubprocessError()):
            adapter = GeminiAdapter()
            assert adapter.detect() is True
            assert GeminiAdapter._cli_version == "Version Unknown"

@pytest.mark.asyncio
async def test_execute_auth_via_kwargs():
    adapter = GeminiAdapter()
    with patch.dict("os.environ", {}, clear=True):
        async def mock_spawn(*args, **kwargs):
            assert kwargs["env"]["GEMINI_API_KEY"] == "kwarg-key"
            assert kwargs["env"]["GOOGLE_API_KEY"] == "kwarg-key"
            yield OutputChunk(content="Ok", timestamp=1.0)

        with patch("bmad_orch.providers.gemini.spawn_pty_process", side_effect=mock_spawn):
            async for _ in adapter.execute("test prompt", api_key="kwarg-key"):
                pass

@pytest.mark.asyncio
async def test_execute_invalid_grace_period():
    adapter = GeminiAdapter()
    with patch.dict("os.environ", {
        "GEMINI_API_KEY": "key",
        "GEMINI_TERMINATION_GRACE_PERIOD": "invalid"
    }, clear=False):
        async def mock_spawn(*args, **kwargs):
            assert kwargs["grace_period"] == 2.0
            yield OutputChunk(content="Ok", timestamp=1.0)

        with patch("bmad_orch.providers.gemini.spawn_pty_process", side_effect=mock_spawn):
            async for _ in adapter.execute("test prompt"):
                pass

@pytest.mark.asyncio
async def test_execute_defensive_parsing_binary():
    adapter = GeminiAdapter()
    with patch.dict("os.environ", {"GEMINI_API_KEY": "key"}, clear=False):
        async def mock_spawn(*args, **kwargs):
            yield OutputChunk(content="Some \x00 binary", timestamp=1.0)

        with patch("bmad_orch.providers.gemini.spawn_pty_process", side_effect=mock_spawn):
            with pytest.raises(ProviderError, match=r"Impactful Provider Error \(binary detected\)."):
                async for _ in adapter.execute("test prompt"):
                    pass

@pytest.mark.asyncio
async def test_execute_timeout_cleanup():
    adapter = GeminiAdapter()
    GeminiAdapter._cli_version = "v1.2.3"
    with patch.dict("os.environ", {"GEMINI_API_KEY": "key"}, clear=False):
        async def mock_spawn(*args, **kwargs):
            raise ProviderTimeoutError("Timeout")
            yield

        with patch("bmad_orch.providers.gemini.spawn_pty_process", side_effect=mock_spawn):
            with pytest.raises(ProviderTimeoutError, match="v1.2.3"):
                async for _ in adapter.execute("test prompt"):
                    pass

@pytest.mark.asyncio
async def test_execute_cancellation():
    adapter = GeminiAdapter()
    with patch.dict("os.environ", {"GEMINI_API_KEY": "key"}, clear=False):
        async def mock_spawn(*args, **kwargs):
            raise asyncio.CancelledError()
            yield

        with patch("bmad_orch.providers.gemini.spawn_pty_process", side_effect=mock_spawn):
            with pytest.raises(asyncio.CancelledError):
                async for _ in adapter.execute("test prompt"):
                    pass

@pytest.mark.asyncio
async def test_execute_retry_logic():
    adapter = GeminiAdapter()
    with patch.dict("os.environ", {
        "GEMINI_API_KEY": "key",
        "GEMINI_MAX_RETRIES": "2",
        "GEMINI_RETRY_INITIAL_DELAY": "0.01"
    }, clear=False):
        
        call_count = 0
        async def mock_spawn(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                raise ProviderCrashError("Transient failure")
            yield OutputChunk(content="Success", timestamp=1.0)

        with patch("bmad_orch.providers.gemini.spawn_pty_process", side_effect=mock_spawn):
            chunks = []
            async for chunk in adapter.execute("test prompt"):
                chunks.append(chunk)
            
            assert call_count == 3
            assert chunks[0].content == "Success"
            assert chunks[0].metadata["attempt"] == 3

@pytest.mark.asyncio
async def test_execute_retry_limit_exceeded():
    adapter = GeminiAdapter()
    with patch.dict("os.environ", {
        "GEMINI_API_KEY": "key",
        "GEMINI_MAX_RETRIES": "1",
        "GEMINI_RETRY_INITIAL_DELAY": "0.01"
    }, clear=False):
        
        call_count = 0
        async def mock_spawn(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            raise ProviderCrashError("Permanent failure")
            yield

        with patch("bmad_orch.providers.gemini.spawn_pty_process", side_effect=mock_spawn):
            with pytest.raises(ProviderCrashError, match="Permanent failure"):
                async for _ in adapter.execute("test prompt"):
                    pass
            
            assert call_count == 2 # Initial attempt + 1 retry

@pytest.mark.asyncio
async def test_execute_invalid_retry_config():
    adapter = GeminiAdapter()
    with patch.dict("os.environ", {
        "GEMINI_API_KEY": "key",
        "GEMINI_MAX_RETRIES": "invalid",
        "GEMINI_RETRY_BACKOFF_FACTOR": "invalid",
        "GEMINI_RETRY_INITIAL_DELAY": "invalid"
    }, clear=False):
        async def mock_spawn(*args, **kwargs):
            yield OutputChunk(content="Ok", timestamp=1.0)

        with patch("bmad_orch.providers.gemini.spawn_pty_process", side_effect=mock_spawn):
            async for _ in adapter.execute("test prompt"):
                pass

@pytest.mark.asyncio
async def test_execute_defensive_parsing_beyond_2kb():
    """AC7: Corruption patterns must trigger at any point in the stream, not just first 2KB."""
    adapter = GeminiAdapter()
    with patch.dict("os.environ", {"GEMINI_API_KEY": "key"}, clear=False):
        async def mock_spawn(*args, **kwargs):
            # Yield >2KB of clean data first
            yield OutputChunk(content="x" * 3000, timestamp=1.0)
            # Then yield corruption pattern after the 2KB window
            yield OutputChunk(content="<html>502 Bad Gateway</html>", timestamp=2.0)

        with patch("bmad_orch.providers.gemini.spawn_pty_process", side_effect=mock_spawn):
            with pytest.raises(ProviderTransientError, match="Transient Provider Error detected: <html>"):
                async for _ in adapter.execute("test prompt"):
                    pass

@pytest.mark.asyncio
async def test_execute_defensive_parsing_binary_beyond_2kb():
    """AC7: Binary data must be detected at any point in the stream."""
    adapter = GeminiAdapter()
    with patch.dict("os.environ", {"GEMINI_API_KEY": "key"}, clear=False):
        async def mock_spawn(*args, **kwargs):
            yield OutputChunk(content="x" * 3000, timestamp=1.0)
            yield OutputChunk(content="binary \x00 data", timestamp=2.0)

        with patch("bmad_orch.providers.gemini.spawn_pty_process", side_effect=mock_spawn):
            with pytest.raises(ProviderError, match=r"Impactful Provider Error \(binary detected\)."):
                async for _ in adapter.execute("test prompt"):
                    pass

@pytest.mark.asyncio
async def test_execute_defensive_parsing_403_forbidden():
    """AC7: 403 Forbidden must be detected as a corruption pattern."""
    adapter = GeminiAdapter()
    with patch.dict("os.environ", {"GEMINI_API_KEY": "key"}, clear=False):
        async def mock_spawn(*args, **kwargs):
            yield OutputChunk(content="403 Forbidden", timestamp=1.0)

        with patch("bmad_orch.providers.gemini.spawn_pty_process", side_effect=mock_spawn):
            with pytest.raises(ProviderError, match="Impactful Provider Error detected: 403 Forbidden"):
                async for _ in adapter.execute("test prompt"):
                    pass
