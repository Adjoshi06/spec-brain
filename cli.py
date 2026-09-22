"""Interactive Spec Brain session for the live demo."""

import os
import sys
import webbrowser
from pathlib import Path

from rich.panel import Panel
from rich.prompt import Prompt

import agent as spec_agent
from agent import console, parse_approval_prompt

ROOT = Path(__file__).resolve().parent

LEGEND = (
    "[bold]Spec Brain[/bold] — a practising architect's personal memory, as an agent.\n"
    "[cyan][PERSONAL][/cyan] own notes & decisions   [cyan][OFFICE STANDARD][/cyan] company data   "
    "[green][PUBLIC][/green] manufacturer pages via Bright Data\n"
    "[magenta][CALCULATION][/magenta] deterministic check in a Docker sandbox   "
    "[yellow]approval gate[/yellow] before anything is sent\n"
    "Commands: /graph  /before  /quit"
)

BEFORE_QUESTION = "Have we made any substitution decision on the Mission St ceiling? What is on record?"


def cli_ask(prompt: str, **_) -> str:
    payload = parse_approval_prompt(prompt)
    if payload:
        body = payload.get("body", "")
        console.print(Panel(
            f"[bold]To:[/bold] {payload.get('to')}\n[bold]Subject:[/bold] {payload.get('subject')}\n\n{body}",
            title="APPROVAL REQUIRED — send_substitution_request", border_style="yellow", expand=False,
        ))
    else:
        console.print(Panel(prompt, title="APPROVAL REQUIRED", border_style="yellow", expand=False))
    return Prompt.ask("[yellow]Send it?[/yellow] (y/n)", default="n").strip().lower()


def main() -> int:
    console.print(Panel(LEGEND, border_style="blue", expand=False))
    agent = spec_agent.build_agent(ask=cli_ask)
    while True:
        try:
            text = Prompt.ask("\n[bold blue]you[/bold blue]").strip()
        except (EOFError, KeyboardInterrupt):
            console.print()
            return 0
        if not text:
            continue
        if text in {"/quit", "/exit", "q"}:
            return 0
        if text == "/graph":
            for name in ("personal", "office", "public"):
                path = ROOT / "graph" / f"{name}.html"
                if path.exists():
                    webbrowser.open(path.as_uri())
            continue
        if text == "/before":
            text = BEFORE_QUESTION
            console.print(f"[dim]{text}[/dim]")
        console.print("[bold green]spec brain[/bold green] ", end="")
        try:
            agent(text)
        except KeyboardInterrupt:
            console.print("\n[dim]interrupted[/dim]")
        except Exception as exc:  # noqa: BLE001 - keep the demo alive, show the error
            console.print(f"\n[red]error:[/red] {type(exc).__name__}: {exc}")


if __name__ == "__main__":
    os.chdir(ROOT)
    sys.exit(main())
