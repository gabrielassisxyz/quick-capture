"""LLM enrichment via opencode run subprocess."""

from __future__ import annotations

import json
import subprocess
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import sqlite3

from quick_capture.db import get_capture, save_enrichment, update_capture

ENRICHMENT_PROMPT = """Analyze this captured thought and provide enrichment.

Classification rules:
- Task: An actionable item that can be completed (has a next step)
- Idea: A creative thought, concept, or inspiration (no immediate action needed)
- Reference: A fact, link, or information to store for later lookup
- Question: Something that needs research or a decision to be made

Enrichment rules:
- Preserve the original meaning — enriched_text expands but never contradicts
- Add context relevant to the thought
- Suggest concrete next steps if applicable

Use wiki-query to pull related context from your Obsidian wiki when enriching.

Return ONLY valid JSON with these fields:
{
  "bucket": "<Task|Idea|Reference|Question>",
  "enriched_text": "<expanded version of the thought>",
  "tags": ["<tag1>", "<tag2>"],
  "wikilinks": ["<WikiPageName>"]
}

Original thought:
"""

VALID_BUCKETS = {"Task", "Idea", "Reference", "Question"}


def _validate_bucket(result: dict[str, Any]) -> None:
    """Validate that the bucket field is one of the valid values."""
    bucket = result.get("bucket", "")
    if bucket not in VALID_BUCKETS:
        msg = f"Invalid bucket: {bucket!r}. Must be one of {VALID_BUCKETS}"
        raise ValueError(msg)


def _extract_json_from_fences(text: str) -> str:
    """Extract JSON content from ```json ... ``` code fences, if present."""
    if "```" not in text:
        return text
    lines = text.split("\n")
    json_lines: list[str] = []
    in_fence = False
    for line in lines:
        if line.strip().startswith("```"):
            if in_fence:
                break
            in_fence = True
            continue
        if in_fence:
            json_lines.append(line)
    if json_lines:
        return "\n".join(json_lines)
    return text


def parse_enrichment_output(output: str) -> dict[str, Any]:
    """Parse enrichment JSON from opencode run output.

    Handles: plain JSON, ```json ... ``` code fences, and mixed output
    with preamble text before the JSON.

    Raises ValueError if no valid JSON with a valid bucket can be found.
    """
    text = _extract_json_from_fences(output.strip())

    # Try parsing the whole output as JSON first
    try:
        result = json.loads(text)
    except json.JSONDecodeError:
        pass
    else:
        _validate_bucket(result)
        return result

    # Try finding the last valid JSON object in the output (line by line from end)
    for raw_line in reversed(output.strip().split("\n")):
        stripped = raw_line.strip()
        if stripped.startswith("{"):
            try:
                result = json.loads(stripped)
            except json.JSONDecodeError:
                continue
            else:
                _validate_bucket(result)
                return result

    msg = "Could not parse enrichment JSON from output"
    raise ValueError(msg)


def enrich_capture(capture_id: str, conn: sqlite3.Connection | None = None) -> dict[str, Any]:
    """Full enrichment pipeline for a capture.

    1. Get capture from DB (ValueError if not found)
    2. Set status to 'enriching'
    3. Run opencode subprocess with enrichment prompt
    4. Parse output and save enrichment
    5. Return enrichment dict

    On failure: resets status to 'unprocessed' and raises RuntimeError.
    """
    capture = get_capture(capture_id, conn=conn)
    if capture is None:
        msg = f"Capture {capture_id} not found"
        raise ValueError(msg)

    # Set status to enriching
    update_capture(capture_id, {"status": "enriching"}, conn=conn)

    prompt = ENRICHMENT_PROMPT + capture["original_text"]

    try:
        result = subprocess.run(  # noqa: S603
            ["opencode", "run", "--format", "json", prompt],  # noqa: S607
            capture_output=True,
            text=True,
            timeout=120,
            check=False,  # We check returncode manually below
            shell=False,  # Security: T-03-01 — prevents command injection
        )
    except subprocess.TimeoutExpired:
        update_capture(capture_id, {"status": "unprocessed"}, conn=conn)
        msg = f"Enrichment timed out after 120s for capture {capture_id}"
        raise RuntimeError(msg) from None

    if result.returncode != 0:
        update_capture(capture_id, {"status": "unprocessed"}, conn=conn)
        msg = f"opencode run failed (exit {result.returncode}): {result.stderr}"
        raise RuntimeError(msg)

    try:
        enrichment = parse_enrichment_output(result.stdout)
    except ValueError:
        update_capture(capture_id, {"status": "unprocessed"}, conn=conn)
        raise

    save_enrichment(
        capture_id=capture_id,
        bucket=enrichment["bucket"],
        enriched_text=enrichment["enriched_text"],
        tags=enrichment.get("tags", []),
        wikilinks=enrichment.get("wikilinks", []),
        conn=conn,
    )

    return enrichment
