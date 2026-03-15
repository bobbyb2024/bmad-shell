import asyncio
import hashlib
import pathlib
import signal
import subprocess
import sys
import time
import traceback
from datetime import UTC, datetime
import json
import uuid
from typing import Annotated, Literal

import typer
from pydantic import ValidationError
from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.progress import BarColumn, Progress, TextColumn
from rich.table import Table
from rich.text import Text

from bmad_orch.config import (
    get_config,
    load_config_file,
    validate_config,
    validate_provider_availability,
)
from bmad_orch.engine.errors import NON_RECOVERABLE_ERROR_TYPES
from bmad_orch.engine.runner import Runner
from bmad_orch.exceptions import (
    BmadOrchError,
    ConfigError,
    ConfigProviderError,
    GitError,
    ProviderCrashError,
    ProviderError,
    ProviderTimeoutError,
    ResourceError,
    StateError,
    TemplateVariableError,
)
from bmad_orch.providers import get_adapter, get_registry
from bmad_orch.rendering.summary import render_playbook_summary
from bmad_orch.engine.resume import (
    get_resume_context,
    prepare_rerun,
    prepare_restart_cycle,
    prepare_skip,
    prepare_start_fresh,
)
from bmad_orch.state import RunState, RunStatus, StateManager

app = typer.Typer(help="BMAD Orchestrator - End-to-end automated story execution.")

def get_console() -> Console:
    return Console()

def get_error_console() -> Console:
    return Console(stderr=True)


def get_config_hash(path: pathlib.Path) -> str:
    """Calculate MD5 hash of the normalized config file."""
    with path.open("rb") as f:
        return hashlib.md5(f.read(), usedforsecurity=False).hexdigest()

def handle_confirmation(_config_path: pathlib.Path) -> Literal["proceed", "quit", "modify"]:
    """Handle user confirmation at pre-flight summary."""
    prompt = Text.from_markup("\n[bold cyan]Confirmation:[/bold cyan] [Enter] to proceed, [m] to modify, [q] to quit")
    get_console().print(prompt)
    
    while True:
        try:
            choice = typer.getchar().lower()
        except (EOFError, KeyboardInterrupt):
            return "quit"
        if choice in ("\r", "\n"):
            return "proceed"
        elif choice == "q":
            return "quit"
        elif choice == "m":
            return "modify"

def handle_auto_dismiss() -> Literal["proceed", "pause", "quit"]:
    """Handle 3-second auto-dismiss for subsequent runs (AC3)."""
    import select
    
    start_time = time.time()
    duration = 3.0
    
    # Check if stdin is a TTY for character-at-a-time reading
    is_tty = sys.stdin.isatty()
    old_settings = None
    fd: int = -1
    try:
        fd = sys.stdin.fileno()
    except (AttributeError, ValueError):
        # stdin might not have a fileno() in some environments
        is_tty = False
    
    if is_tty:
        try:
            import termios
            import tty
            old_settings = termios.tcgetattr(fd)
            tty.setcbreak(fd)
        except ImportError:
            is_tty = False
    
    try:
        with Live(console=get_console(), auto_refresh=True) as live:
            while True:
                elapsed = time.time() - start_time
                remaining = max(0.0, duration - elapsed)
                
                if remaining <= 0:
                    return "proceed"
                
                msg = Text.from_markup(
                    f"\nProceeding in {remaining:.1f}s... (any key to skip, [p] to pause, [q] to quit)"
                )
                live.update(msg)
                
                # Check for key press
                if is_tty:
                    if select.select([sys.stdin], [], [], 0.1)[0]:
                        key = sys.stdin.read(1).lower()
                        if key == "p":
                            return "pause"
                        if key == "q":
                            return "quit"
                        return "proceed"
                else:
                    # Non-TTY or failed to set cbreak: just wait
                    time.sleep(0.1)
    finally:
        if is_tty and old_settings:
            import termios
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)

def open_editor(path: pathlib.Path) -> bool:
    """Open the config file in an editor (AC4)."""
    import os
    import shutil
    
    editor = os.environ.get("EDITOR")
    if not editor:
        # Fallback discovery
        for e in ["vim", "vi", "nano"]:
            if shutil.which(e):
                editor = e
                break
    
    if not editor:
        get_error_console().print("[red]Error: No editor found ($EDITOR not set, and vim/vi/nano not found).[/red]")
        return False
    
    # Check if the editor is actually executable
    if not shutil.which(editor):
        get_error_console().print(f"[red]Error: Editor '{editor}' not found or not executable.[/red]")
        return False
    
    try:
        # Use subprocess.run to ensure terminal stays interactive
        subprocess.run([editor, str(path)], check=True)  # noqa: S603
        return True
    except subprocess.CalledProcessError as e:
        get_error_console().print(f"[red]Editor exited with error (code {e.returncode}).[/red]")
        return False
    except Exception as e:
        get_error_console().print(f"[red]Error invoking editor: {e}[/red]")
        return False

async def _run_with_signals(runner: Runner) -> int:
    """Helper to run the orchestrator with SIGINT/SIGTERM handling."""
    loop = asyncio.get_running_loop()
    main_task = asyncio.create_task(runner.run())
    
    # Track which exit code to use if cancelled
    exit_code_container = {"code": 0}

    def signal_handler(sig_name: str, sig_code: int) -> None:
        if runner.in_emergency_flow:
            get_error_console().print(f"\n[yellow]■ Emergency save in progress ({sig_name}), please wait...[/yellow]")
            return
        get_error_console().print(f"\n[yellow]■ Interrupt received ({sig_name}), halting gracefully...[/yellow]")
        exit_code_container["code"] = sig_code
        main_task.cancel()

    for sig, code in [(signal.SIGINT, 130), (signal.SIGTERM, 143)]:
        try:
            loop.add_signal_handler(sig, signal_handler, sig.name, code)
        except (NotImplementedError, ValueError):
            # Fallback for environments where add_signal_handler is not supported (e.g. Windows, some CI)
            pass

    try:
        await main_task
        return 0
    except asyncio.CancelledError:
        return exit_code_container["code"]

@app.command()
def start(
    config: Annotated[str | None, typer.Option("--config", "-c", help="Path to bmad-orch.yaml")] = None,
    dry_run: bool = typer.Option(False, "--dry-run", help="Show execution plan without invoking providers"),
    no_preflight: bool = typer.Option(False, "--no-preflight", help="Skip pre-flight confirmation"),
    _headless: bool = typer.Option(False, "--headless", help="Run without TUI"),
) -> None:
    """Start a new orchestrator run."""
    error_console = get_error_console()
    try:
        cfg, source_path = get_config(config)
        validate_provider_availability(cfg, registry=get_registry())
    except BmadOrchError as e:
        error_console.print(f"[red]{e}[/red]")
        raise typer.Exit(code=2) from e

    config_hash = get_config_hash(source_path)
    state_path = source_path.parent / "bmad-orch-state.json"
    
    try:
        state = StateManager.load(state_path, expected_hash=config_hash)
        first_run = not state_path.exists() or not state.run_history
        config_changed = state.config_hash != config_hash
    except StateError as e:
        error_console.print(f"[yellow]Warning: Previous state file issue: {e}. Starting fresh state.[/yellow]")
        state = RunState(run_id=str(uuid.uuid4()), config_hash=config_hash)
        first_run = True
        config_changed = False

    if dry_run:
        render_playbook_summary(cfg, dry_run=True)
        raise typer.Exit(code=0)
    
    if not no_preflight:
        render_playbook_summary(cfg, dry_run=False)
        action = handle_confirmation(source_path) if (first_run or config_changed) else handle_auto_dismiss()
        if action == "pause":
            action = handle_confirmation(source_path)
        while action == "modify":
            if open_editor(source_path):
                try:
                    data = load_config_file(source_path)
                    cfg = validate_config(data)
                    config_hash = get_config_hash(source_path)
                    render_playbook_summary(cfg, dry_run=False)
                    action = handle_confirmation(source_path)
                except Exception as e:
                    error_console.print(f"[red]Invalid config: {e}[/red]")
                    if typer.confirm("Edit again?", default=True):
                        action = "modify"
                    else:
                        action = "quit"
            else:
                action = handle_confirmation(source_path)
        if action == "quit":
            raise typer.Exit(code=130)

    # Initialize and run
    runner = Runner(config=cfg, state_path=state_path, adapter_factory=get_adapter)
    
    exit_code: int = 0
    try:
        # Cast to int to satisfy Pyright Literal[0] inference
        res = asyncio.run(_run_with_signals(runner))
        exit_code = int(res)
    except Exception as e:
        headline = f"✗ [{str(e)}] — run bmad-orch resume"
        error_console.print(f"\n[bold red]{headline}[/bold red]")
        
        if exit_code == 0:
            if isinstance(e, (ConfigError, ConfigProviderError, TemplateVariableError)):
                exit_code = 2
            elif isinstance(e, (GitError, ResourceError, StateError)):
                exit_code = 3
            elif isinstance(e, (ProviderCrashError, ProviderTimeoutError, ProviderError)):
                exit_code = 4
            else:
                exit_code = 1
            
        raise typer.Exit(code=exit_code) from e

    if exit_code != 0:
        if exit_code in (130, 143):
            error_console.print("\n[bold yellow]■ [Execution Halted by User] — run bmad-orch resume[/bold yellow]")
        raise typer.Exit(code=exit_code)

@app.command()
def resume(
    config_path: Annotated[
        pathlib.Path | None,
        typer.Option("--config", "-c", help="Path to bmad-orch.yaml"),
    ] = None,
    resume_option: Annotated[
        int | None,
        typer.Option("--resume-option", "-r", help="Resume option (1-5)"),
    ] = None,
    force: Annotated[
        bool,
        typer.Option("--force", "-f", help="Bypass warnings and confirmations"),
    ] = False,
    force_unlock: Annotated[
        bool,
        typer.Option("--force-unlock", help="Override RUNNING status lock"),
    ] = False,
) -> None:
    """Resume execution from last failed or halted step."""
    console = get_console()
    error_console = get_error_console()

    # AC 7, 8, 9 Logic — check state file before loading config
    # Determine state path: config-relative if --config provided, else CWD default
    if config_path:
        state_path = config_path.parent / "bmad-orch-state.json"
    else:
        state_path = pathlib.Path(StateManager.DEFAULT_STATE_FILE)

    if not state_path.exists():
        error_console.print("[bold red]✗ No previous run found — use bmad-orch start[/bold red]")
        raise typer.Exit(code=1)

    try:
        state = StateManager.load(state_path)
    except StateError as e:
        error_console.print(f"[bold red]✗ State file is corrupt: {e}[/bold red]")
        raise typer.Exit(code=1) from e

    if state.status == RunStatus.COMPLETED:
        console.print("[bold green]✓ Previous run completed successfully[/bold green]")
        console.print("Suggest: [bold cyan]bmad-orch start[/bold cyan] for a new run.")
        raise typer.Exit(code=0)

    if state.status == RunStatus.RUNNING and not force_unlock:
        error_console.print("[bold red]✗ A run is currently in progress[/bold red]")
        error_console.print("Use [bold cyan]--force-unlock[/bold cyan] to break the lock if it's a zombie process.")
        raise typer.Exit(code=1)

    # Load config for hash comparison and execution
    try:
        orch_config, source_path = get_config(str(config_path) if config_path else None)
    except BmadOrchError as e:
        error_console.print(f"[bold red]✗ Failed to load config: {e}[/bold red]")
        raise typer.Exit(code=1) from e

    # AC 11: Config Hash Mismatch
    current_hash = get_config_hash(source_path)

    if state.config_hash and current_hash != state.config_hash:
        console.print("[bold yellow]⚠ Playbook config has changed since the failed run[/bold yellow]")
        if not force:
            if not sys.stdin.isatty():
                error_console.print("[bold red]✗ Headless mode: aborting config mismatch without --force[/bold red]")
                raise typer.Exit(code=1)
            if not typer.confirm("Continue anyway?"):
                raise typer.Exit(code=0)

    # AC 1: Context Screen
    ctx = get_resume_context(state)
    from rich.panel import Panel
    from rich.table import Table

    table = Table.grid(padding=(0, 1))
    table.add_column(style="cyan")
    table.add_column()
    table.add_row("Halted At:", ctx["halted_at"])
    table.add_row("Failure Point:", ctx["failure_point"])
    table.add_row("Failure Reason:", ctx["failure_reason"])
    table.add_row("Error Type:", ctx["error_type"])
    table.add_row("Summary:", f"{ctx['completed_cycles']} cycles / {ctx['completed_steps']} steps completed")

    console.print(Panel(table, title="[bold yellow]Resume Context[/bold yellow]", border_style="yellow"))

    # Options availability
    failure_point_known = state.failure_point is not None and "/" in state.failure_point
    
    options = [
        f"[1] Re-run failed step ({'Enabled' if failure_point_known else 'Disabled'})",
        f"[2] Skip failed step ({'Enabled' if failure_point_known else 'Disabled'})",
        "[3] Restart current cycle",
        "[4] Start from scratch",
        "[5] Cancel",
    ]
    
    if not failure_point_known:
        error_console.print("[bold red]⚠ failure_point is unknown. Options 1 and 2 are disabled.[/bold red]")

    # AC 10: Headless Mode
    if not sys.stdin.isatty() and resume_option is None:
        error_console.print("[bold red]✗ Headless mode: --resume-option required[/bold red]")
        raise typer.Exit(code=1)

    if resume_option is None:
        console.print("\n[bold cyan]Options:[/bold cyan]")
        for opt in options:
            console.print(opt)
        
        # AC 12: SIGINT Handling
        def signal_handler(sig, frame):
            console.print("\n[bold yellow]Exiting...[/bold yellow]")
            sys.exit(0)
        
        signal.signal(signal.SIGINT, signal_handler)
        
        choice = typer.prompt("\nSelect an option", type=int)
    else:
        choice = resume_option

    # AC 2: Option Execution
    if choice == 5:
        console.print("Cancelled.")
        raise typer.Exit(code=0)
    
    if choice in (1, 2) and not failure_point_known:
        error_console.print(f"[bold red]✗ Option {choice} is disabled because failure_point is unknown.[/bold red]")
        raise typer.Exit(code=1)

    start_cycle_id = None
    start_step_index = 0
    template_context = dict(state.template_context)

    if choice == 1:
        start_cycle_id, start_step_index, template_context = prepare_rerun(state)
    elif choice == 2:
        if not force:
            console.print("[bold yellow]⚠ Skipping this step may cause subsequent steps to fail if they depend on its output context.[/bold yellow]")
            if not typer.confirm("Are you sure?"):
                raise typer.Exit(code=0)
        start_cycle_id, start_step_index, template_context = prepare_skip(state, list(orch_config.cycles.keys()))
    elif choice == 3:
        console.print("[bold yellow]⚠ External side-effects (e.g. written files) from the failed run are not rolled back.[/bold yellow]")
        start_cycle_id, start_step_index, template_context = prepare_restart_cycle(state)
    elif choice == 4:
        prepare_start_fresh(state_path)
        console.print("State reset. Starting from scratch...")
        # Start fresh means no start_cycle_id, start_step_index = 0, template_context = {}
        start_cycle_id = None
        start_step_index = 0
        template_context = {}
    else:
        error_console.print(f"[bold red]✗ Invalid option: {choice}[/bold red]")
        raise typer.Exit(code=1)

    # Validate start_cycle_id exists if it's not a fresh start
    if start_cycle_id and start_cycle_id not in orch_config.cycles:
        error_console.print(f"[bold red]✗ Resume point '{start_cycle_id}' no longer exists in playbook.[/bold red]")
        raise typer.Exit(code=1)

    # Run
    runner = Runner(orch_config, state_path=state_path, adapter_factory=get_adapter)
    try:
        asyncio.run(runner.run(
            template_context=template_context,
            start_cycle_id=start_cycle_id,
            start_step_index=start_step_index
        ))
    except KeyboardInterrupt:
        error_console.print("\n[bold yellow]■ [Execution Halted by User] — run bmad-orch resume[/bold yellow]")
        raise typer.Exit(code=130)
    except BmadOrchError as e:
        error_console.print(f"\n[bold red]✗ {e}[/bold red]")
        raise typer.Exit(code=1) from e
    except Exception as e:
        error_console.print(f"\n[bold red]✗ Unexpected error: {e}[/bold red]")
        traceback.print_exc()
        raise typer.Exit(code=1) from e


def _resolve_state_path(run_id: str | None = None) -> pathlib.Path:
    """Resolves the path to the state file, optionally for a specific run_id."""
    if run_id:
        # Check standard location with run_id prefix
        artifact_dir = pathlib.Path("_bmad-output/implementation-artifacts")
        path = artifact_dir / f"{run_id}-state.json"
        if path.exists():
            return path
        # Fallback to CWD
        path = pathlib.Path(f"{run_id}-state.json")
        if path.exists():
            return path
        # If run_id is provided but not found, return the expected path so caller can report missing
        return artifact_dir / f"{run_id}-state.json"
    
    # Default behavior: check CWD or implementation-artifacts for generic state
    default_path = pathlib.Path(StateManager.DEFAULT_STATE_FILE)
    if default_path.exists():
        return default_path
        
    artifact_path = pathlib.Path("_bmad-output/implementation-artifacts") / StateManager.DEFAULT_STATE_FILE
    return artifact_path

@app.command()
def status(
    run_id: Annotated[str | None, typer.Option("--run-id", help="Filter by specific Run ID")] = None,
    json_output: Annotated[bool, typer.Option("--json", help="Output full state as JSON")] = False,
) -> None:
    """View current orchestrator status and progress."""
    console = get_console()
    error_console = get_error_console()
    
    state_path = _resolve_state_path(run_id)
    
    if not state_path.exists():
        error_console.print(f"[bold red]✗ No previous runs found.[/bold red] (Checked: {state_path})")
        raise typer.Exit(code=1)
        
    try:
        if state_path.stat().st_size == 0:
            raise StateError("State file is empty (0-byte)")
             
        with state_path.open(encoding="utf-8") as f:
            raw_json = f.read()
            state = RunState.model_validate_json(raw_json)
    except (json.JSONDecodeError, ValidationError, StateError) as e:
        error_console.print(f"[bold red]✗ State file is corrupted or unreadable: {e}[/bold red]")
        raise typer.Exit(code=2) from e

    if json_output:
        # AC6: JSON output to stdout only, suppress everything else
        sys.stdout.write(state.model_dump_json(indent=2) + "\n")
        sys.stdout.flush()
        # AC3: Respect exit codes even in JSON mode
        if state.status in (RunStatus.FAILED, RunStatus.HALTED):
            raise typer.Exit(code=3)
        raise typer.Exit(code=0)

    # AC3: Rich-formatted summary
    status_colors = {
        RunStatus.PENDING: "white",
        RunStatus.RUNNING: "cyan",
        RunStatus.COMPLETED: "green",
        RunStatus.FAILED: "red",
        RunStatus.HALTED: "yellow",
    }
    status_color = status_colors.get(state.status, "white")
    
    table = Table.grid(padding=(0, 1))
    table.add_column(style="bold white", width=20)
    table.add_column()
    
    table.add_row("Run ID:", state.run_id)
    table.add_row("Status:", f"[{status_color}]{state.status.value}[/{status_color}]")
    
    # Progress Calculation
    completed_cycles = len(state.run_history)
    # We don't strictly know the total without config, so we'll just show completed
    # unless it's COMPLETED status
    if state.status == RunStatus.COMPLETED:
        total_cycles_str = f"{completed_cycles}/{completed_cycles}"
    else:
        total_cycles_str = f"{completed_cycles} (in-progress)"
    table.add_row("Cycle Progress:", total_cycles_str)
    
    # Last Step
    last_step_info = "[dim]None[/dim]"
    if state.run_history:
        last_cycle = state.run_history[-1]
        if last_cycle.steps:
            last_step = last_cycle.steps[-1]
            last_step_info = f"{last_step.step_id} ([cyan]{last_step.provider_name}[/cyan]) -> {last_step.outcome.value}"
    table.add_row("Last Step:", last_step_info)
    
    # Elapsed Time
    start_time = state.run_history[0].started_at if state.run_history else None
    elapsed_str = "not started"
    if start_time:
        if state.status == RunStatus.PENDING:
            elapsed_str = "not started"
        elif state.status == RunStatus.RUNNING:
            elapsed = datetime.now(UTC) - start_time
            elapsed_str = str(elapsed).split(".")[0]
        else:
            # Terminal state
            end_time = state.halted_at
            if not end_time and state.run_history:
                end_time = state.run_history[-1].finished_at
            
            if end_time:
                elapsed = end_time - start_time
                elapsed_str = str(elapsed).split(".")[0]
            else:
                elapsed_str = "[dim]Unknown[/dim]"
    
    table.add_row("Elapsed Time:", elapsed_str)
    
    console.print()
    console.print(Panel(table, title="[bold cyan]Run Status[/bold cyan]", border_style=status_color))
    
    # AC5: FAILED/HALTED details
    if state.status in (RunStatus.FAILED, RunStatus.HALTED):
        err_table = Table.grid(padding=(0, 1))
        err_table.add_column(style="bold red", width=20)
        err_table.add_column()
        err_table.add_row("Failure Point:", state.failure_point or "Unknown")
        err_table.add_row("Error Type:", state.error_type or "Unknown")
        err_table.add_row("Reason:", state.failure_reason or "Unknown")
        
        console.print(Panel(err_table, title="[bold red]Failure Details[/bold red]", border_style="red"))
        
        # Suggest resume
        if state.error_type not in NON_RECOVERABLE_ERROR_TYPES:
            console.print("\n[bold yellow]💡 Suggestion:[/bold yellow] This error may be recoverable. Run [cyan]bmad-orch resume[/cyan] to continue.")
        else:
            console.print("\n[bold red]✖ Non-Recoverable Error:[/bold red] Restarting from scratch is recommended for this error type.")
            
        raise typer.Exit(code=3)

    raise typer.Exit(code=0)


@app.command()
def validate(
    config: Annotated[str | None, typer.Option("--config", "-c", help="Path to bmad-orch.yaml")] = None,
) -> None:
    """Check config schema and provider availability."""
    console = get_console()
    try:
        cfg, source_path = get_config(config)
        validate_provider_availability(cfg, registry=get_registry())
        msg = f"[green]✓ Configuration is valid and providers are available.[/green] (loaded from {source_path})"
        console.print(msg, soft_wrap=True)

        # Report providers and models
        console.print("\n[bold]Detected Configuration:[/bold]")
        for pid, pcfg in cfg.providers.items():
            console.print(f"  [blue]Provider {pid}:[/blue] {pcfg.name} (model: {pcfg.model})")

    except BmadOrchError as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(code=2) from e
    except Exception as e:
        console.print(f"[red]✗ Unexpected error — {e}[/red]", highlight=False)
        console.print(f"[dim]{traceback.format_exc()}[/dim]", highlight=False)
        raise typer.Exit(code=1) from e



@app.callback()
def main(
    init: bool = typer.Option(False, "--init", help="Run guided configuration wizard"),
) -> None:
    """BMAD Orchestrator CLI."""
    if init:
        typer.echo("Initializing bmad-orch...")
        raise typer.Exit()


if __name__ == "__main__":
    app()
