---
paths:
  - "app/services/**"
---

# Service rules

These cover services and the agents. The project-wide rules are in `architecture.md`, including "Writing a service", and `code-style.md`.

## Services

- A service function reads like a list of steps, and each line's output feeds the next.
- Services are long modules. Keep adding helpers to the same file instead of splitting them out.
- Services hold every decision. They read and write data only through `models/`.
- Services never import `pydantic`, `pydantic_core` or `pydantic_settings` directly. Their own shapes are TypedDicts from `schemas/`.
- Before writing something by hand, check whether LangChain, LangGraph or FastAPI already does it.

## Agents

- Agents are built with LangChain's `create_agent`, which builds the LangGraph graph for us. Don't hand-build a `StateGraph` unless `create_agent` can't do the job.
- The model is `ChatOpenAI` from `langchain-openai`. The model name, and the `base_url` when it points at another OpenAI-compatible endpoint, come from settings.
- When a person has to approve an action, put `HumanInTheLoopMiddleware` on the tool that does it, with `allowed_decisions` set to approve and reject. The agent pauses there.
- When the person answers, the agent resumes on the same thread with `Command(resume={"decisions": [{"type": "approve"}]})`, or with a reject decision.
- The `thread_id` is the conversation's ID, so each conversation keeps its own memory. Never use an ID that many conversations share, like a login session.
- The service receives LangGraph's checkpointer and store only to pass them to `create_agent`. It never calls the checkpointer itself.
- Building an agent takes milliseconds, so it's built per request from the checkpointer and store the request carries.
- Tool descriptions go in `@tool(description=...)`, never in docstrings.
- Tools are narrow and typed, each doing one job, like finding a product or saving a draft. The model never gets general write access to an outside system.
- The agent's state is a TypedDict that extends `langchain.agents.AgentState`, defined in `schemas/`.
