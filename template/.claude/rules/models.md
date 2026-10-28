---
paths:
  - "app/models/**"
---

# Model rules

These cover everything that reads or writes data. The project-wide rules are in `architecture.md` and `code-style.md`.

- `models/` is the only place that reads or writes data: outside systems, like an API or a business database, and LangGraph's store.
- There's one file per kind of data, like products, customers or orders, named after what it holds.
- Models make no decisions and never call services. They read, write, and return what they got.
- Data coming back from an outside system is checked with a Pydantic schema from `schemas/` before it's returned.
- Store functions receive the store as a parameter. A model never opens a database connection. The lifespan in `config/` opens one pool at startup.
- Store namespaces are tuples, like `("approvals",)`.
- Use the async store methods (`aput`, `aget`, `asearch`, `adelete`), because the app is async.
- In tests, pass LangGraph's in-memory store instead of Postgres. Models don't care which one they get.
- The HTTP client for calling outside systems is still open in `decisions.md`.
