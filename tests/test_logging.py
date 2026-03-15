import asyncio
import logging
import os
from pathlib import Path

import pytest
import structlog

from bmad_orch.logging import (
    async_task_wrapper,
    configure_logging,
    consolidate_step_logs,
    get_step_logs,
    reset_step_logs,
)


@pytest.fixture(autouse=True)
def cleanup_logs():
    reset_step_logs()
    yield
    reset_step_logs()

def test_configure_logging_invalid_mode():
    """Verify that configure_logging raises ValueError on invalid mode."""
    with pytest.raises(ValueError, match="Invalid logging mode"):
        configure_logging(mode="invalid")

def test_configure_logging_invalid_level():
    """Verify that configure_logging raises ValueError on invalid level."""
    with pytest.raises(ValueError, match="Invalid logging level"):
        configure_logging(mode="human", level="INVALID")

def test_human_mode_output(capsys):
    """Verify human mode produces colored output with severity icons."""
    configure_logging(mode="human", level="DEBUG")
    logger = structlog.get_logger()
    logger.info("test message", key="value")
    
    captured = capsys.readouterr()
    output = captured.err if captured.err else captured.out
    assert "test message" in output
    assert "key=value" in output
    assert "ℹ️ " in output  # INFO icon

def test_machine_mode_output(capsys):
    """Verify machine mode produces structured plain text with strict positions."""
    configure_logging(mode="machine", level="DEBUG")
    logger = structlog.get_logger()
    logger.info("machine test", step_id="123")
    
    captured = capsys.readouterr()
    output = (captured.err if captured.err else captured.out).strip()
    
    # AC6: TS 1-27, space 28, severity 29-33
    assert len(output) >= 33
    # ts = output[0:27]
    space = output[27]
    severity = output[28:33]
    
    assert space == " "
    assert severity == "INFO "
    assert "step_id=123" in output
    assert "machine test" in output

def test_file_logging(tmp_path):
    """Verify logs are written to logs/bmad.log."""
    log_dir = tmp_path / "logs"
    log_file = log_dir / "bmad.log"
    
    original_cwd = Path.cwd()
    os.chdir(tmp_path)
    try:
        configure_logging(mode="machine")
        logger = structlog.get_logger()
        logger.info("file log test")
        
        assert log_file.exists()
        content = log_file.read_text()
        assert "file log test" in content
    finally:
        os.chdir(original_cwd)

def test_stdlib_bridge(capsys):
    """Verify stdlib logging is routed through structlog."""
    configure_logging(mode="machine", level="DEBUG")
    std_logger = logging.getLogger("test_stdlib_bridge")
    std_logger.info("stdlib bridge message")

    captured = capsys.readouterr()
    output = captured.err if captured.err else captured.out
    assert "stdlib bridge message" in output
    assert "INFO " in output

@pytest.mark.asyncio
async def test_async_context_propagation():
    """Verify async context propagation and isolation."""
    configure_logging(mode="machine")
    
    async def task(name, delay):
        structlog.contextvars.bind_contextvars(task_name=name)
        await asyncio.sleep(delay)
        ctx = structlog.contextvars.get_contextvars()
        return ctx

    results = await asyncio.gather(task("A", 0.1), task("B", 0.05))
    
    assert results[0]["task_name"] == "A"
    assert results[1]["task_name"] == "B"

@pytest.mark.asyncio
async def test_async_task_wrapper_cleanup():
    """Verify async_task_wrapper clears contextvars."""
    configure_logging(mode="machine")
    
    @async_task_wrapper
    async def some_task():
        structlog.contextvars.bind_contextvars(secret="data")  # noqa: S106
        return "done"

    await some_task()
    assert structlog.contextvars.get_contextvars() == {}

def test_per_step_capture():
    """Verify that logs with step_id are captured with all context."""
    configure_logging(mode="machine")
    logger = structlog.get_logger()

    logger.info("step log", step_id="step-1", provider_name="claude", extra_ctx="val")

    logs = get_step_logs("step-1")
    assert len(logs) == 1
    assert logs[0]["event"] == "step log"
    assert logs[0]["step_id"] == "step-1"
    assert logs[0]["provider_name"] == "claude"
    assert logs[0]["extra_ctx"] == "val"

def test_per_step_capture_via_contextvars():
    """Verify that step_id bound via contextvars is captured."""
    configure_logging(mode="machine")
    logger = structlog.get_logger()

    structlog.contextvars.bind_contextvars(step_id="ctx-step", provider_name="gemini")
    try:
        logger.info("contextvar step log")
    finally:
        structlog.contextvars.clear_contextvars()

    logs = get_step_logs("ctx-step")
    assert len(logs) == 1
    assert logs[0]["event"] == "contextvar step log"
    assert logs[0]["step_id"] == "ctx-step"
    assert logs[0]["provider_name"] == "gemini"

def test_per_step_eviction():
    """Verify global LRU eviction of step logs."""
    configure_logging(mode="machine")
    logger = structlog.get_logger()
    
    import bmad_orch.logging
    original_limit = bmad_orch.logging.MAX_GLOBAL_ENTRIES
    bmad_orch.logging.MAX_GLOBAL_ENTRIES = 10
    try:
        logger.info("msg 1", step_id="step-1")
        logger.info("msg 2", step_id="step-2")
        
        # Now add 9 more to step-3, total entries will be 11.
        # This should trigger eviction of oldest step (step-1).
        for i in range(9):
            logger.info(f"msg {i}", step_id="step-3")
            
        assert get_step_logs("step-1") == []
        assert len(get_step_logs("step-2")) == 1
        assert len(get_step_logs("step-3")) == 9
        
        # Add one more to step-4, total entries 11, should evict step-2
        logger.info("msg step 4", step_id="step-4")
        assert get_step_logs("step-2") == []
        assert len(get_step_logs("step-4")) == 1
        assert len(get_step_logs("step-3")) == 9
        
    finally:
        bmad_orch.logging.MAX_GLOBAL_ENTRIES = original_limit

def test_stdlib_bridge_no_double_capture():
    """Verify stdlib logging with step_id captures exactly once (not per-handler)."""
    configure_logging(mode="machine", level="DEBUG")
    std_logger = logging.getLogger("test_double_cap")

    structlog.contextvars.bind_contextvars(step_id="std-step", provider_name="test")
    try:
        std_logger.info("stdlib step message")
    finally:
        structlog.contextvars.clear_contextvars()

    logs = get_step_logs("std-step")
    assert len(logs) == 1, f"Expected 1 log entry, got {len(logs)} (double-capture bug)"
    assert logs[0]["event"] == "stdlib step message"

def test_consolidate_logs():
    """Verify consolidate_step_logs returns formatted string in machine format."""
    configure_logging(mode="machine")
    logger = structlog.get_logger()
    
    logger.info("test log", step_id="step-100", source="test_src", provider_name="claude", extra="val")
    
    output = consolidate_step_logs("step-100")
    assert "--- LOGS FOR STEP step-100 ---" in output
    # TS + INFO + [extra=val provider_name=claude source=test_src step_id=step-100] + test log
    assert "INFO " in output
    assert "extra=val" in output
    assert "provider_name=claude" in output
    assert "source=test_src" in output
    assert "test log" in output
    # Verify strict position 28 space
    lines = output.splitlines()
    log_line = lines[1]
    assert log_line[27] == " "
    assert log_line[28:33] == "INFO "
