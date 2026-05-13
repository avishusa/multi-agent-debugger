"""Graph adapter contract.

A `Protocol` defining what every graph backend must provide. Agents
depend on this Protocol, never on a concrete implementation. This is
the seam that lets us:
  - Swap MongoDB for another backend (Neo4j, in-memory, etc.)
  - Mock the graph in tests without a real database
  - Reason about graph operations in domain terms, not Mongo terms
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from multi_agent_debugger.graph_models import (
    Edge,
    EdgeRelation,
    Node,
    NodeType,
)


@runtime_checkable
class GraphAdapter(Protocol):
    """Read/write contract for the shared knowledge graph."""

    # --- Lifecycle --------------------------------------------------------

    def connect(self) -> None:
        """Establish the connection. Must be called before any other method."""
        ...

    def close(self) -> None:
        """Release connection resources. Safe to call multiple times."""
        ...

    def ping(self) -> bool:
        """Return True iff the backend is reachable. Used for health checks."""
        ...

    # --- Writes -----------------------------------------------------------

    def upsert_node(self, node: Node) -> Node:
        """Insert or update a node by id. Returns the persisted node."""
        ...

    def add_edge(self, edge: Edge) -> Edge:
        """Insert an edge. Returns the persisted edge. Idempotent on `id`."""
        ...

    # --- Reads ------------------------------------------------------------

    def get_node(self, node_id: str) -> Node | None:
        """Return the node with this id, or None."""
        ...

    def find_nodes(
        self,
        node_type: NodeType,
        text_query: str | None = None,
        limit: int = 10,
    ) -> list[Node]:
        """Find nodes of `node_type`. Optional substring/text filter on `text`."""
        ...

    def neighbors(
        self,
        node_id: str,
        relation: EdgeRelation | None = None,
        direction: str = "out",
    ) -> list[Node]:
        """Return immediate neighbors of `node_id` along `relation`."""
        ...

    def traverse(
        self,
        start_id: str,
        relation: EdgeRelation,
        max_depth: int = 2,
    ) -> list[Node]:
        """Walk the graph from `start_id` along `relation`, up to `max_depth` hops."""
        ...
