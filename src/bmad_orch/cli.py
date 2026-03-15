import asyncio
import hashlib
import pathlib
import subprocess
import sys
import time
import traceback
import uuid
from typing import Annotated, Literal

import typer
from rich.console import Console
from rich.live import Live
from rich.text import Text

from bmad_orch.config import (
    get_config,
    load_config_file,
    validate_config,
    validate_provider_availability,
)
from bmad_orch.engine.runner import Runner
from bmad_orch.exceptions import BmadOrchError, ConfigProviderError, StateError
from bmad_orch.providers import get_adapter, get_registry
from bmad_orch.rendering.summary import render_playbook_summary
from bmad_orch.state import RunState, StateManager

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
    except ConfigProviderError as e:
        error_console.print(f"[red]{e}[/red]")
        raise typer.Exit(code=2) from e
    except BmadOrchError as e:
        error_console.print(f"[red]{e}[/red]")
        raise typer.Exit(code=2) from e

    config_hash = get_config_hash(source_path)
    state_path = source_path.parent / "bmad-orch-state.json"
    
    # AC8: Use StateManager.load for state discovery, loading, and validation
    try:
        state = StateManager.load(state_path, expected_hash=config_hash)
        # config_changed = state.config_hash != config_hash  # StateManager.load already warns
        first_run = not state_path.exists() or not state.run_history
        config_changed = state.config_hash != config_hash
    except StateError as e:
        error_console.print(f"[yellow]Warning: Previous state file issue: {e}. Starting fresh state.[/yellow]")
        state = RunState(run_id=str(uuid.uuid4()), config_hash=config_hash)
        first_run = True
        config_changed = False

    # Pre-flight logic
    if dry_run:
        render_playbook_summary(cfg, dry_run=True)
        raise typer.Exit(code=0)
    
    if not no_preflight:
        render_playbook_summary(cfg, dry_run=False)
        
        action = "proceed"
        if first_run or config_changed:
            action = handle_confirmation(source_path)
        else:
            action = handle_auto_dismiss()
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
                    get_error_console().print(f"[red]Invalid config: {e}[/red]")
                    get_console().print("\n[bold cyan]Options:[/bold cyan] [e]dit again, [q]uit")
                    while True:
                        c = typer.getchar().lower()
                        if c == "e":
                            action = "modify"
                            break
                        elif c == "q":
                            action = "quit"
                            break
            else:
                action = handle_confirmation(source_path)

        if action == "quit":
            raise typer.Exit(code=130)

    # Save state with config hash (atomic write via StateManager)
    state = RunState(run_id=str(uuid.uuid4()), config_hash=config_hash)
    try:
        StateManager.save(state, state_path)
    except StateError as e:
        error_console.print(f"[red]Warning: Could not save state file: {e}[/red]")

    # Initialize and run
    runner = Runner(config=cfg, state_path=state_path, adapter_factory=get_adapter)
    asyncio.run(runner.run(dry_run=False))

@app.command()
def resume(
    config: Annotated[str | None, typer.Option("--config", "-c", help="Path to bmad-orch.yaml")] = None,
) -> None:
    """Resume execution from last completed step."""
    _ = config
    typer.echo("Resuming bmad-orch...")


@app.command()
def status() -> None:
    """View current orchestrator state."""
    typer.echo("Status of bmad-orch...")


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
