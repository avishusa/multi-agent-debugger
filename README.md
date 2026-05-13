# Multi-Agent Debugger

Three specialized agents — Reproducer, Hypothesizer, Fixer — collaborate to
debug code. They share persistent memory through a MongoDB knowledge graph,
accumulating Facts and Decisions over time. Session N is measurably faster
than session 1 because the agents remember.

Built as a production-grade POC to demonstrate multi-agent orchestration on
top of a shared knowledge graph. The graph layer is reused from
[agent-memory-graph](https://github.com/avishusa/agent-memory-graph).

## Status

🚧 Under construction. See [ROADMAP.md](./ROADMAP.md) for the build plan.

## Stack

| Layer            | Technology                | Why                                     |
| ---------------- | ------------------------- | --------------------------------------- |
| LLM              | Gemini 2.5 Flash          | Best capability on the free tier        |
| Graph storage   | MongoDB Atlas M0 (free)   | `$graphLookup` for traversal            |
| Language         | Python 3.11+              | Industry standard for AI engineering    |
| Package manager  | `uv`                      | Fast, modern, single tool for env+deps  |
| Validation       | Pydantic v2               | Runtime type checking                   |
| Config           | pydantic-settings + .env  | Twelve-factor configuration             |
| Logging          | structlog                 | Structured, machine-parseable logs      |
| Retry            | tenacity                  | Exponential backoff on rate limits      |

## Quickstart

Prerequisites: Python 3.11+, `uv`, MongoDB Atlas account, Google AI Studio API key.

```powershell
git clone https://github.com/avishusa/multi-agent-debugger.git
cd multi-agent-debugger
uv sync
Copy-Item .env.example .env  # then edit .env with real credentials
```

More setup details and the design walkthrough land here as the project grows.