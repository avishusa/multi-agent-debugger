"""Graph domain models.

Pydantic models for nodes and edges. These are the *only* shapes that
should flow between the adapter and the rest of the application. Raw
Mongo dicts stay inside the adapter; everything outside sees typed
objects.

Schema mirrors `agent-memory-graph` so both projects can share a Mongo
cluster (different databases).
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

NodeType = Literal["Task", "Tool", "Fact", "Decision"]
EdgeRelation = Literal[
    "USED_TOOL",
    "LEARNED",
    "MADE_DECISION",
    "RELATED_TO",
    "DEPENDS_ON",
]


def _now_utc() -> datetime:
    """UTC `datetime` with timezone. Never use naive datetimes in storage."""
    return datetime.now(UTC)


def _new_id() -> str:
    """Generate a fresh node/edge id. Hex form of uuid4 keeps it Mongo-friendly."""
    return uuid4().hex


class Node(BaseModel):
    """A node in the knowledge graph."""

    model_config = ConfigDict(extra="allow", frozen=False)

    id: str = Field(default_factory=_new_id, alias="_id")
    type: NodeType
    label: str = Field(min_length=1, max_length=200)
    text: str = Field(default="", max_length=10_000)
    created_at: datetime = Field(default_factory=_now_utc)
    metadata: dict[str, Any] = Field(default_factory=dict)


class Edge(BaseModel):
    """A directed edge connecting two nodes."""

    model_config = ConfigDict(extra="allow", frozen=False)

    id: str = Field(default_factory=_new_id, alias="_id")
    from_id: str
    to_id: str
    relation: EdgeRelation
    created_at: datetime = Field(default_factory=_now_utc)
    metadata: dict[str, Any] = Field(default_factory=dict)
