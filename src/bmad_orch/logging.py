import functools
import logging
import sys
from collections import OrderedDict, defaultdict, deque
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import TypeVar

import structlog
from structlog.types import EventDict, Processor

from bmad_orch.engine.events import LogLevel

T = TypeVar("T")

# Global storage for per-step logs
STEP_LOGS: dict[str, deque[dict[str, object]]] = defaultdict(deque)
STEP_ORDER: OrderedDict[str, None] = OrderedDict()
MAX_GLOBAL_ENTRIES = 50000
_current_total_entries = 0

# Severity Icons for Human Mode
SEVERITY_ICONS = {
    LogLevel.DEBUG: "🔍",
    LogLevel.INFO: "ℹ️ ",
    LogLevel.WARNING: "⚠️ ",
    LogLevel.ERROR: "❌",
    LogLevel.CRITICAL: "🚨",
}

# Fixed-width Severity Tags for Machine Mode
SEVERITY_TAGS = {
    LogLevel.DEBUG: "DEBUG",
    LogLevel.INFO: "INFO ",
    LogLevel.WARNING: "WARN ",
    LogLevel.ERROR: "ERROR",
    LogLevel.CRITICAL: "CRIT ",
}

INTERNAL_FIELDS = (
    "level_no",
    "level_icon",
    "level_name",
    "level",
    "timestamp",
    "event",
    "_record",
    "_from_structlog",
    "_logger",
    "_processors_meta",
)

def add_timestamp(_: object, __: str, event_dict: EventDict) -> EventDict:
    """Add ISO-8601 timestamp with microsecond precision."""
    if "timestamp" not in event_dict:
        event_dict["timestamp"] = datetime.now(UTC).isoformat(timespec="microseconds").replace("+00:00", "Z")
    return event_dict

def add_severity(_: object, method_name: str, event_dict: EventDict) -> EventDict:
    """Map method name to LogLevel and add to event_dict."""
    level_name = method_name.upper()
    if level_name == "WARN":
        level_name = "WARNING"
    
    level = event_dict.get("level_no")
    if level is None:
        try:
            level = getattr(LogLevel, level_name, LogLevel.INFO)
        except (AttributeError, TypeError):
            level = LogLevel.INFO
    
    event_dict["level_no"] = level
    event_dict["level_name"] = SEVERITY_TAGS.get(level, str(level_name).ljust(5))
    event_dict["level_icon"] = SEVERITY_ICONS.get(level, "📝")
    return event_dict

def inject_source(logger: object, _: str, event_dict: EventDict) -> EventDict:
    """Inject 'source' as the Python module name if not present."""
    if "source" not in event_dict:
        if hasattr(logger, "name"):
            event_dict["source"] = logger.name  # type: ignore[union-attr]
        elif "_logger" in event_dict: # Handle stdlib wrapper
            event_dict["source"] = event_dict["_logger"].name
        else:
            # Try to get from logger object if it has a context
            event_dict["source"] = "bmad_orch"
    return event_dict

def capture_step_logs(_: object, __: str, event_dict: EventDict) -> EventDict:
    """Capture logs for the current step if step_id is present."""
    step_id = event_dict.get("step_id")
    if step_id:
        global _current_total_entries

        # Capture all context for diagnosis, excluding internal implementation fields
        entry = {
            k: v for k, v in event_dict.items()
            if k not in ("_record", "_from_structlog", "_logger", "_processors_meta")
        }

        # O(1) LRU update via OrderedDict
        STEP_ORDER.pop(step_id, None)
        STEP_ORDER[step_id] = None

        STEP_LOGS[step_id].append(entry)
        _current_total_entries += 1

        # Evict oldest steps when global cap exceeded
        while _current_total_entries > MAX_GLOBAL_ENTRIES and STEP_ORDER:
            oldest_step, _ = STEP_ORDER.popitem(last=False)
            if oldest_step in STEP_LOGS:
                removed_count = len(STEP_LOGS[oldest_step])
                del STEP_LOGS[oldest_step]
                _current_total_entries -= removed_count

    return event_dict

class MachineRenderer:
    """Renders log entries in machine-friendly structured plain text."""
    def __call__(self, _: object, __: str, event_dict: EventDict) -> str:
        # Use .get() instead of .pop() to avoid issues with multiple handlers sharing event_dict
        ts = event_dict.get("timestamp", "UNKNOWN_TS")
        level = event_dict.get("level_name", "INFO ")
        msg = event_dict.get("event", "")

        context = " ".join(f"{k}={v}" for k, v in event_dict.items() if k not in INTERNAL_FIELDS)
        ctx_str = f" [{context}]" if context else ""

        return f"{ts} {level}{ctx_str} {msg}"

class HumanRenderer:
    """Renders log entries in human-friendly format."""
    def __call__(self, _: object, __: str, event_dict: EventDict) -> str:
        ts = event_dict.get("timestamp", "UNKNOWN_TS")
        icon = event_dict.get("level_icon", "ℹ️ ")
        msg = event_dict.get("event", "")
        
        context = ",".join(f"{k}={v}" for k, v in event_dict.items() if k not in INTERNAL_FIELDS)
        ctx_str = f" [{context}]" if context else ""
        
        return f"[{ts}] [{icon}]{ctx_str} {msg}"

def configure_logging(mode: str = "human", level: str = "INFO") -> None:
    """Configure the logging subsystem."""
    if mode not in ("human", "machine"):
        raise ValueError(f"Invalid logging mode: {mode}")
    
    numeric_level = getattr(logging, level.upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError(f"Invalid logging level: {level}")

    # Ensure logs directory exists
    try:
        Path("logs").mkdir(parents=True, exist_ok=True)
    except OSError as e:
        print(f"Warning: Could not create logs directory: {e}", file=sys.stderr)

    # Shared processor chain for stdlib (foreign) log routing
    foreign_pre_chain: list[Processor] = [
        structlog.stdlib.add_log_level,
        structlog.contextvars.merge_contextvars,
        add_timestamp,
        add_severity,
        inject_source,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    handlers: list[logging.Handler] = []

    # File handler always uses machine format
    try:
        file_formatter = structlog.stdlib.ProcessorFormatter(
            processors=[
                structlog.stdlib.ProcessorFormatter.remove_processors_meta,
                MachineRenderer(),
            ],
            foreign_pre_chain=foreign_pre_chain,
        )

        log_file = "logs/bmad.log"
        file_handler = RotatingFileHandler(log_file, maxBytes=10*1024*1024, backupCount=5)
        file_handler.setFormatter(file_formatter)
        handlers.append(file_handler)
    except OSError as e:
        print(f"Warning: Could not initialize file logging: {e}", file=sys.stderr)

    # Console handler — capture_step_logs only here for stdlib logs to avoid double-capture
    console_renderer = HumanRenderer() if mode == "human" else MachineRenderer()
    console_formatter = structlog.stdlib.ProcessorFormatter(
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            console_renderer,
        ],
        foreign_pre_chain=foreign_pre_chain + [capture_step_logs],
    )
    
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(console_formatter)
    handlers.append(console_handler)

    root_logger = logging.getLogger()
    for h in root_logger.handlers[:]:
        root_logger.removeHandler(h)
    
    for h in handlers:
        root_logger.addHandler(h)
    
    root_logger.setLevel(numeric_level)

    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_log_level,
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.PositionalArgumentsFormatter(),
            add_timestamp,
            add_severity,
            inject_source,
            capture_step_logs,
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

def async_task_wrapper(func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:  # noqa: UP047
    """Decorator to ensure structlog contextvars are cleared after async task execution."""
    @functools.wraps(func)
    async def wrapper(*args: object, **kwargs: object) -> T:
        try:
            return await func(*args, **kwargs)
        finally:
            structlog.contextvars.clear_contextvars()
    return wrapper

def get_step_logs(step_id: str) -> list[dict[str, object]]:
    """Retrieve captured logs for a specific step."""
    return list(STEP_LOGS.get(step_id, []))

def consolidate_step_logs(step_id: str) -> str:
    """Format captured logs for a step as a single newline-separated string using machine format."""
    logs = get_step_logs(step_id)
    if not logs:
        return f"--- LOGS FOR STEP {step_id} ---\n(No logs captured)"
    
    renderer = MachineRenderer()
    lines = [f"--- LOGS FOR STEP {step_id} ---"]
    for log in logs:
        # MachineRenderer expectations
        lines.append(renderer(None, "", log))
    
    return "\n".join(lines)

def reset_step_logs() -> None:
    """Reset the global step log buffers."""
    global _current_total_entries
    STEP_LOGS.clear()
    STEP_ORDER.clear()
    _current_total_entries = 0
