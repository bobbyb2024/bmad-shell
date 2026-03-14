# 3. Challenges & Friction Points
- **TTY/Terminal Complexity:** Implementing the "any key to dismiss" and pause logic in Story 1.5 required navigating Unix-specific `tty` and `termios` modules, which introduced initial friction in testing.
- **CLI Output Capture:** `typer.testing.CliRunner` limitations with `stderr` capture required refactoring how the `Console` instance was initialized to ensure full observability.
- **FIPS Compliance:** An unexpected requirement for `usedforsecurity=False` in MD5 hashing was identified and fixed during code review.
