"""Data models and enums for Quick Capture."""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum


class CaptureStatus(StrEnum):
    """Status of a capture through its lifecycle."""

    UNPROCESSED = "unprocessed"
    ENRICHING = "enriching"
    ENRICHED = "enriched"
    DISPATCHED = "dispatched"


class Bucket(StrEnum):
    """Classification bucket for an enriched capture."""

    TASK = "Task"
    IDEA = "Idea"
    REFERENCE = "Reference"
    QUESTION = "Question"


@dataclass
class Capture:
    """A raw captured thought."""

    id: str
    original_text: str
    status: CaptureStatus = CaptureStatus.UNPROCESSED
    created_at: str = field(default_factory=lambda: datetime.now(tz=UTC).isoformat())
    updated_at: str | None = None


@dataclass
class CaptureEnrichment:
    """LLM enrichment of a capture."""

    id: str
    capture_id: str
    bucket: Bucket
    enriched_text: str
    tags: list[str] = field(default_factory=list)
    wikilinks: list[str] = field(default_factory=list)
    opencode_session_id: str | None = None
    created_at: str = field(default_factory=lambda: datetime.now(tz=UTC).isoformat())
