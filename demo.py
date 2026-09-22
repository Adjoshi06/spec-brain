"""Non-interactive end-to-end run of the demo script. Writes out/demo-transcript.md.

Usage: python demo.py [--no-send]   (--no-send answers "n" at the approval gate)
"""

import datetime as dt
import os
import sys
import time
from pathlib import Path

import agent as spec_agent
from agent import console, parse_approval_prompt

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "out"

TURNS = [
    ("before", "Have we made any substitution decision on the Mission St ceiling? What is on record?"),
    ("inbox", "Anything in my inbox this week I should worry about on Mission St?"),
    ("substitute", "Find me a substitute for the Mission St ceiling tile and check it against our standard."),
    ("send", "Send the substitution request to the BuildCo PM."),
    ("after", "Have we made any substitution decision on the Mission St ceiling? What is on record?"),
]


def main(argv) -> int:
    auto = "n" if "--no-send" in argv else "y"

    def auto_ask(prompt: str, **_) -> str:
        payload = parse_approval_prompt(prompt)
        console.print(f"[yellow]approval gate:[/yellow] {payload.get('subject', prompt[:80])} -> {auto}")
        return auto

    OUT.mkdir(exist_ok=True)
    agent = spec_agent.build_agent(ask=auto_ask)
    transcript = [f"# Spec Brain demo transcript — {dt.datetime.now().isoformat(timespec='seconds')}\n"]
    for label, question in TURNS:
        console.rule(f"[bold]{label}[/bold]")
        console.print(f"[bold blue]you:[/bold blue] {question}")
        console.print("[bold green]spec brain:[/bold green] ", end="")
        started = time.perf_counter()
        result = agent(question)
        seconds = round(time.perf_counter() - started, 1)
        answer = str(result)
        transcript.append(f"\n## {label} ({seconds}s)\n\n**you:** {question}\n\n**spec brain:** {answer}\n")
    path = OUT / "demo-transcript.md"
    path.write_text("\n".join(transcript), encoding="utf-8")
    console.print(f"\n[dim]transcript written to {path}[/dim]")
    return 0


if __name__ == "__main__":
    os.chdir(ROOT)
    sys.exit(main(sys.argv[1:]))
