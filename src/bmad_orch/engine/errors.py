from typing import Final

# Errors that cannot be recovered by bmad-orch resume
# These usually require manual config or codebase changes
NON_RECOVERABLE_ERROR_TYPES: Final[set[str]] = {
    "ConfigError",
    "SchemaValidationError",
    "SystemError"
}
