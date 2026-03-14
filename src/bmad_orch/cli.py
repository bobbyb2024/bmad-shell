from typing import Annotated

import typer
from rich.console import Console

from bmad_orch.config import get_config
from bmad_orch.errors import BmadOrchError

app = typer.Typer(help="BMAD Orchestrator - End-to-end automated story execution.")
console = Console()


@app.command()
def start(
    config: Annotated[str | None, typer.Option("--config", "-c", help="Path to bmad-orch.yaml")] = None,
    dry_run: bool = typer.Option(False, "--dry-run", help="Show execution plan without invoking providers"),
    headless: bool = typer.Option(False, "--headless", help="Run without TUI"),
) -> None:
    """Start a new orchestrator run."""
    _ = config, dry_run, headless
    typer.echo("Starting bmad-orch...")


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
    try:
        cfg = get_config(config)
        console.print("[green]✓ Configuration is valid.[/green]")

        # Report providers and models
        console.print("\n[bold]Detected Configuration:[/bold]")
        for pid, pcfg in cfg.providers.items():
            console.print(f"  [blue]Provider {pid}:[/blue] {pcfg.name} (model: {pcfg.model})")

    except BmadOrchError as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(code=2) from e
    except Exception as e:
        console.print(f"[red]✗ Unexpected error: {e}[/red]")
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
