from rich.style import Style

# Central style definitions for the orchestrator
SUCCESS = Style(color="green", bold=True)
ERROR = Style(color="red", bold=True)
WARNING = Style(color="yellow", bold=True)
INFO = Style(color="blue")
DIM = Style(dim=True)
BOLD = Style(bold=True)

# Specific UI element styles
HEADER = Style(color="cyan", bold=True)
TABLE_HEADER = Style(color="magenta", bold=True)
STEP_TYPE_GEN = Style(color="green")
STEP_TYPE_VAL = Style(color="blue")
PROVIDER_ID = Style(color="yellow", bold=True)
