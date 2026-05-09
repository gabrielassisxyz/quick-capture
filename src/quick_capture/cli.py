"""Quick Capture CLI — floating terminal inbox capture."""

import argparse
import sys

from prompt_toolkit import prompt
from prompt_toolkit.key_binding import KeyBindings
from rich.console import Console
from rich.panel import Panel

from quick_capture.db import save_capture
from quick_capture.enrich import enrich_capture

console = Console()

MAX_CAPTURE_SIZE = 10_000  # 10KB limit per security threat model


def run_capture_tui() -> str | None:
    """Display capture UI and return multiline text, or None on cancel."""
    console.print(
        Panel(
            "[bold cyan]Quick Capture[/bold cyan]\n"
            "[dim]Type your thought. Ctrl+S to save. Escape to cancel.[/dim]",
            border_style="cyan",
            padding=(0, 1),
        )
    )

    kb = KeyBindings()

    @kb.add("c-s")
    def _submit(event: object) -> None:
        """Submit on Ctrl+S."""
        event.current_buffer.validate_and_handle()

    try:
        text = prompt(
            "💭 ",
            multiline=True,
            key_bindings=kb,
            mouse_support=True,
            prompt_continuation=lambda _width, _line_number, _wrap_count: "... ",
        )
        return text.strip() or None
    except KeyboardInterrupt:
        return None


def main() -> None:
    """Entry point: run TUI or enrich via --enrich flag."""
    parser = argparse.ArgumentParser(description="Quick Capture — frictionless inbox capture")
    parser.add_argument("--enrich", metavar="CAPTURE_ID", help="Enrich a capture by ID")
    args = parser.parse_args()

    if args.enrich:
        try:
            result = enrich_capture(args.enrich)
            console.print(f"[green]✓ Enriched[/green] (bucket: {result['bucket']})")
            sys.exit(0)
        except (ValueError, RuntimeError) as e:
            console.print(f"[red]✗ Enrichment failed:[/red] {e}")
            sys.exit(1)

    try:
        text = run_capture_tui()
        if text:
            if len(text) > MAX_CAPTURE_SIZE:
                console.print(f"[red]✗ Capture too large (max {MAX_CAPTURE_SIZE} chars)[/red]")
                sys.exit(1)
            capture_id = save_capture(text)
            console.print(f"[green]✓ Saved[/green] (id: {capture_id[:8]}...)")
            sys.exit(0)
        else:
            console.print("[dim]Cancelled.[/dim]")
            sys.exit(0)
    except Exception:  # noqa: BLE001
        console.print("[red]✗ Failed to save[/red] — check nexus.db")
        sys.exit(1)

