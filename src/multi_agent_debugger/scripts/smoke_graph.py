"""Smoke test for MongoGraphAdapter.

NOT a real test — a manual script you run once to verify the adapter
talks to Mongo correctly. Real tests use a mocked adapter and live in
`tests/`. This script writes a small graph, queries it, then deletes
everything it created, leaving no trace.

Run: uv run python -m multi_agent_debugger.scripts.smoke_graph
"""

from __future__ import annotations

from multi_agent_debugger.graph_models import Edge, Node
from multi_agent_debugger.graph_mongo import MongoGraphAdapter
from multi_agent_debugger.logging_setup import configure_logging, get_logger


def main() -> None:
    configure_logging()
    log = get_logger("smoke.graph")

    graph = MongoGraphAdapter()
    graph.connect()
    log.info("ping", ok=graph.ping())

    # Build a tiny graph: Task -- LEARNED --> Fact
    task = Node(type="Task", label="smoke-task", text="A test task for the smoke run.")
    fact = Node(type="Fact", label="smoke-fact", text="Smoke tests are useful.")
    edge = Edge(from_id=task.id, to_id=fact.id, relation="LEARNED")

    graph.upsert_node(task)
    graph.upsert_node(fact)
    graph.add_edge(edge)
    log.info("wrote_graph", task_id=task.id, fact_id=fact.id, edge_id=edge.id)

    fetched = graph.get_node(task.id)
    log.info("fetched_task", found=fetched is not None, label=fetched.label if fetched else None)

    neighbors = graph.neighbors(task.id, relation="LEARNED", direction="out")
    log.info("neighbors_learned", count=len(neighbors), labels=[n.label for n in neighbors])

    traversed = graph.traverse(task.id, relation="LEARNED", max_depth=2)
    log.info("traverse_learned", count=len(traversed), labels=[n.label for n in traversed])

    # Cleanup so we leave no test data behind.
    nodes_coll = graph._nodes()  # noqa: SLF001  -- intentional in smoke script
    edges_coll = graph._edges()  # noqa: SLF001
    nodes_coll.delete_many({"_id": {"$in": [task.id, fact.id]}})
    edges_coll.delete_one({"_id": edge.id})
    log.info("cleanup_done")

    graph.close()


if __name__ == "__main__":
    main()
