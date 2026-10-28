---
paths:
  - "app/main.py"
  - "app/routes/**"
---

# Route rules

These cover `main.py` and the routes. The project-wide rules are in `architecture.md` and `code-style.md`.

- `main.py` only creates the FastAPI app, passing it the lifespan from `config/` once one exists, and includes each route file's router. Nothing else goes in it.
- A route file stays thin: read the request, call one service, return the result.
- Routes may have 10 statements per function. Everything else has 8.
- Routes never import from `models/`. They call services, and may import from `schemas/` and `config/`.
- Request-scoped resources, like LangGraph's checkpointer and store, come from `request.state`, where the lifespan put them.
- Anything coming in from outside is checked with a Pydantic schema from `schemas/` before it goes any further.
