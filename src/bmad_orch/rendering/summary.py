from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from bmad_orch.config.schema import OrchestratorConfig
from bmad_orch.rendering import styles
from bmad_orch.types import StepType


def render_playbook_summary(config: OrchestratorConfig, dry_run: bool = False) -> None:
    """Render a summary of the execution plan (playbook) to the console."""
    console = Console()

    title_text = (
        "[bold magenta]DRY RUN: PLAYBOOK EXECUTION PLAN[/bold magenta]"
        if dry_run else "[bold cyan]PRE-FLIGHT SUMMARY[/bold cyan]"
    )
    
    # Header panel
    console.print()
    console.print(Panel(
        Text.from_markup(
            f"Project: [bold white]bmad-orch[/bold white]\n"
            f"Cycles: [bold white]{len(config.cycles)}[/bold white]"
        ),
        title=title_text,
        expand=False,
        border_style="magenta" if dry_run else "cyan"
    ))

    # Providers table
    provider_table = Table(
        title="[bold yellow]Providers Registry[/bold yellow]",
        header_style=styles.TABLE_HEADER, box=None,
    )
    provider_table.add_column("ID", justify="right", style=styles.PROVIDER_ID)
    provider_table.add_column("Name", style="white")
    provider_table.add_column("Model", style="blue")
    provider_table.add_column("CLI", style=styles.DIM)

    for p_id, p_conf in sorted(config.providers.items()):
        provider_table.add_row(str(p_id), p_conf.name, p_conf.model, p_conf.cli)
    
    console.print(provider_table)
    console.print()

    # Cycles and Steps table
    plan_table = Table(title="[bold green]Execution Plan[/bold green]", header_style=styles.TABLE_HEADER, box=None)
    plan_table.add_column("Cycle", style="bold white")
    plan_table.add_column("Repeat", justify="right", style=styles.DIM)
    plan_table.add_column("Step", justify="right", style=styles.DIM)
    plan_table.add_column("Skill", style=styles.HEADER)
    plan_table.add_column("Type", style="white")
    plan_table.add_column("Provider", style=styles.PROVIDER_ID)
    plan_table.add_column("Prompt Template", style=styles.DIM, overflow="ellipsis", max_width=40)

    cycle_items = list(config.cycles.items())
    for idx, (cycle_name, cycle) in enumerate(cycle_items):
        for i, step in enumerate(cycle.steps):
            # Only show cycle name and repeat on the first step of the cycle
            c_name = cycle_name if i == 0 else ""
            c_repeat = f"x{cycle.repeat}" if i == 0 else ""

            step_type_style = styles.STEP_TYPE_GEN if step.type == StepType.GENERATIVE else styles.STEP_TYPE_VAL
            step_type_text = Text(step.type.value, style=step_type_style)

            p_name = config.providers[step.provider].name
            p_info = f"[{step.provider}] {p_name}"

            # Truncate prompt for display
            prompt_summary = step.prompt.replace("\n", " ")
            if len(prompt_summary) > 40:
                prompt_summary = prompt_summary[:37] + "..."

            plan_table.add_row(
                c_name,
                c_repeat,
                str(i + 1),
                step.skill,
                step_type_text,
                p_info,
                prompt_summary
            )
        # Add a small spacer between cycles (but not after the last one)
        if idx < len(cycle_items) - 1:
            plan_table.add_row("", "", "", "", "", "", "")

    console.print(plan_table)
    
    if dry_run:
        console.print("[bold yellow]Dry run complete. No providers were invoked.[/bold yellow]")
        console.print()
