"""MongoDB implementation of the GraphAdapter Protocol.

Owns:
  - A lazily-initialized MongoClient (singleton-style)
  - The translation between our Pydantic Node/Edge models and Mongo docs
  - Index management for query performance

Does NOT own:
  - Agent reasoning (no LLM calls here)
  - Settings parsing (uses get_settings())
  - Logging configuration (uses get_logger())
"""

from __future__ import annotations

from typing import Any

from pymongo import ASCENDING, MongoClient
from pymongo.collection import Collection
from pymongo.errors import PyMongoError, ServerSelectionTimeoutError

from multi_agent_debugger.config import get_settings
from multi_agent_debugger.graph_models import (
    Edge,
    EdgeRelation,
    Node,
    NodeType,
)
from multi_agent_debugger.logging_setup import get_logger

log = get_logger("graph.mongo")


class MongoGraphAdapter:
    """MongoDB-backed implementation of `GraphAdapter`."""

    NODES_COLL = "nodes"
    EDGES_COLL = "edges"

    def __init__(self) -> None:
        settings = get_settings()
        self._uri = settings.mongodb_uri.get_secret_value()
        self._db_name = settings.db_name
        self._timeout_ms = settings.mongo_timeout_ms
        self._client: MongoClient[dict[str, Any]] | None = None

    # --- Lifecycle --------------------------------------------------------

    def connect(self) -> None:
        """Open the connection and force-fail if the server is unreachable."""
        if self._client is not None:
            return
        log.info("graph_connect_start", db=self._db_name)
        client: MongoClient[dict[str, Any]] = MongoClient(
            self._uri,
            serverSelectionTimeoutMS=self._timeout_ms,
            uuidRepresentation="standard",
        )
        try:
            client.admin.command("ping")
        except ServerSelectionTimeoutError as exc:
            log.error("graph_connect_failed", error=str(exc))
            raise
        self._client = client
        self._ensure_indexes()
        log.info("graph_connect_ok", db=self._db_name)

    def close(self) -> None:
        if self._client is None:
            return
        self._client.close()
        self._client = None
        log.info("graph_disconnect")

    def ping(self) -> bool:
        try:
            self._require_client().admin.command("ping")
            return True
        except PyMongoError:
            return False

    # --- Writes -----------------------------------------------------------

    def upsert_node(self, node: Node) -> Node:
        doc = node.model_dump(by_alias=True)
        self._nodes().update_one(
            {"_id": node.id},
            {"$set": doc},
            upsert=True,
        )
        log.debug("node_upsert", id=node.id, type=node.type, label=node.label)
        return node

    def add_edge(self, edge: Edge) -> Edge:
        doc = edge.model_dump(by_alias=True)
        self._edges().update_one(
            {"_id": edge.id},
            {"$setOnInsert": doc},
            upsert=True,
        )
        log.debug(
            "edge_upsert",
            id=edge.id,
            from_id=edge.from_id,
            to_id=edge.to_id,
            relation=edge.relation,
        )
        return edge

    # --- Reads ------------------------------------------------------------

    def get_node(self, node_id: str) -> Node | None:
        doc = self._nodes().find_one({"_id": node_id})
        return self._node_from_doc(doc) if doc else None

    def find_nodes(
        self,
        node_type: NodeType,
        text_query: str | None = None,
        limit: int = 10,
    ) -> list[Node]:
        query: dict[str, Any] = {"type": node_type}
        if text_query:
            # Case-insensitive substring match. For real search we would use
            # a text index; for POC scale this is fine and predictable.
            query["text"] = {"$regex": text_query, "$options": "i"}
        cursor = self._nodes().find(query).limit(limit)
        return [self._node_from_doc(doc) for doc in cursor]

    def neighbors(
        self,
        node_id: str,
        relation: EdgeRelation | None = None,
        direction: str = "out",
    ) -> list[Node]:
        if direction not in {"in", "out", "both"}:
            raise ValueError(f"direction must be 'in', 'out', or 'both', got {direction!r}")
        edge_query: dict[str, Any] = {}
        if relation is not None:
            edge_query["relation"] = relation
        node_id_field, neighbor_field = self._direction_fields(direction)

        if direction == "both":
            edge_query["$or"] = [{"from_id": node_id}, {"to_id": node_id}]
        else:
            edge_query[node_id_field] = node_id

        edges = list(self._edges().find(edge_query))
        if direction == "both":
            neighbor_ids = [
                e["to_id"] if e["from_id"] == node_id else e["from_id"] for e in edges
            ]
        else:
            neighbor_ids = [e[neighbor_field] for e in edges]

        if not neighbor_ids:
            return []
        docs = self._nodes().find({"_id": {"$in": neighbor_ids}})
        return [self._node_from_doc(doc) for doc in docs]

    def traverse(
        self,
        start_id: str,
        relation: EdgeRelation,
        max_depth: int = 2,
    ) -> list[Node]:
        """Recursive graph traversal via `$graphLookup`."""
        pipeline: list[dict[str, Any]] = [
            {"$match": {"_id": start_id}},
            {
                "$graphLookup": {
                    "from": self.EDGES_COLL,
                    "startWith": "$_id",
                    "connectFromField": "to_id",
                    "connectToField": "from_id",
                    "restrictSearchWithMatch": {"relation": relation},
                    "as": "_chain",
                    "maxDepth": max_depth,
                    "depthField": "_hop",
                }
            },
        ]
        result = list(self._nodes().aggregate(pipeline))
        if not result:
            return []
        chain_ids = [edge["to_id"] for edge in result[0].get("_chain", [])]
        if not chain_ids:
            return []
        docs = self._nodes().find({"_id": {"$in": chain_ids}})
        return [self._node_from_doc(doc) for doc in docs]

    # --- Internals --------------------------------------------------------

    def _ensure_indexes(self) -> None:
        """Create indexes if missing. Idempotent — safe to call on every connect."""
        nodes, edges = self._nodes(), self._edges()
        nodes.create_index([("type", ASCENDING)], name="idx_nodes_type")
        nodes.create_index(
            [("type", ASCENDING), ("label", ASCENDING)], name="idx_nodes_type_label"
        )
        edges.create_index([("from_id", ASCENDING)], name="idx_edges_from_id")
        edges.create_index([("to_id", ASCENDING)], name="idx_edges_to_id")
        edges.create_index(
            [("from_id", ASCENDING), ("relation", ASCENDING)],
            name="idx_edges_from_relation",
        )
        edges.create_index(
            [("to_id", ASCENDING), ("relation", ASCENDING)],
            name="idx_edges_to_relation",
        )
        log.debug("indexes_ensured")

    def _require_client(self) -> MongoClient[dict[str, Any]]:
        if self._client is None:
            raise RuntimeError("MongoGraphAdapter not connected. Call connect() first.")
        return self._client

    def _nodes(self) -> Collection[dict[str, Any]]:
        return self._require_client()[self._db_name][self.NODES_COLL]

    def _edges(self) -> Collection[dict[str, Any]]:
        return self._require_client()[self._db_name][self.EDGES_COLL]

    @staticmethod
    def _direction_fields(direction: str) -> tuple[str, str]:
        # (field to match on, field to read the neighbor id from)
        if direction == "out":
            return ("from_id", "to_id")
        return ("to_id", "from_id")

    @staticmethod
    def _node_from_doc(doc: dict[str, Any]) -> Node:
        return Node.model_validate(doc)
