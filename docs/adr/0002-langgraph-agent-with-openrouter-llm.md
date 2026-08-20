# 2. LangGraph for the agent pipeline, OpenRouter as the LLM provider

## Status

Accepted

## Context

The explanation step (`GET /tx/{hash}/explain`) needs to turn a grounded
`TransactionSummary` into natural language, and the roadmap (structured
triage flow, developer/support/auditor modes, multi-transaction analysis —
see `docs/nimbus.md` bonus features) means this step will grow branches and
state, not stay a single prompt-in/text-out call forever.

Two independent decisions were needed: how to structure the LLM step, and
which LLM provider to call.

### Pipeline: plain function call vs. a graph framework

A single `llm.invoke(messages)` call would satisfy today's requirement with
less code. But the bonus features are explicitly branching flows (triage
asks clarifying questions before concluding; modes change what the agent
does with the same input; multi-tx analysis correlates more than one
`explain` step). Modeling that as nested `if`/`while` around a growing
function signature turns into an unreadable state machine by the second
branch. A graph framework makes each step a node with explicit edges, and
gets checkpointing (resumable, inspectable runs keyed by `thread_id`) for
free — which a hand-rolled pipeline would have to reimplement.

LangGraph was chosen over alternatives (CrewAI, plain LCEL chains) because:
- It's the lowest-level of the LangChain-ecosystem orchestrators — a graph
  of nodes/edges over an explicit state object, not an opinionated
  multi-agent framework we'd have to fight for a single-assistant use case.
- `MessagesState` + a `BaseCheckpointSaver` gives per-thread conversation
  memory (keyed by `tx_hash` today) without writing our own persistence.
- It composes with `langchain_openai.ChatOpenAI`, which we already need for
  the OpenRouter integration below.

The graph is intentionally one node (`explain`) today — see
`chainwise/agent/graph.py`. That's not a placeholder; it's the honest
representation of the current pipeline. Branches get added as new
nodes/edges when triage or modes are implemented, not scaffolded in advance.

### LLM provider: direct provider SDK vs. OpenRouter

ChainWise must stay usable regardless of which model the evaluator or a
future user has API access to (`docs/nimbus.md` mentions OpenRouter access
to GPT-4o, Claude, DeepSeek, etc. as an example). Calling a single vendor's
SDK directly would mean rewriting `chainwise/agent/llm.py` and its error
handling for every provider we want to support. OpenRouter exposes one
OpenAI-compatible endpoint in front of dozens of providers/models, so
`langchain_openai.ChatOpenAI` pointed at OpenRouter's base URL is enough —
no per-provider adapter code. Swapping models is a config change
(`OPENROUTER_MODEL`), consistent with the network config-driven portability
principle applied elsewhere in this project.

## Decision

- Use LangGraph (`StateGraph` + `MessagesState`) for the agent pipeline,
  starting as a single `explain` node, with a Postgres-backed checkpointer
  so runs are resumable per `thread_id`.
- Use OpenRouter as the only LLM provider, accessed through
  `langchain_openai.ChatOpenAI` pointed at
  `https://openrouter.ai/api/v1`, configured via `OPENROUTER_API_KEY` and
  `OPENROUTER_MODEL`.

## Consequences

- New agent behavior (triage, modes, multi-tx) is added as new
  nodes/conditional edges in `graph.py`, not as new control flow bolted onto
  a plain function — the graph shape stays legible as it grows.
- Model choice is a one-line env change (`OPENROUTER_MODEL`), with no code
  or adapter changes — cheap/fast models can be used for local testing and
  swapped for stronger ones without touching `llm.py`.
- Adds two dependencies (`langgraph`, `langgraph-checkpoint-postgres`) and a
  hard runtime dependency on Postgres being reachable at startup
  (`create_checkpointer` is entered once in the app's lifespan) — an
  acceptable cost since the project already uses Postgres-shaped local infra
  (`docker-compose.yml`).
- Single point of LLM failure: if OpenRouter itself is down, every model
  behind it is unreachable. Acceptable for this project's scope; a future
  fallback would mean adding a second provider client, not swapping this
  one out.
