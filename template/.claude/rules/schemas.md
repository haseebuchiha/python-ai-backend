---
paths:
  - "app/schemas/**"
---

# Schema rules

These cover every class in the app. The project-wide rules are in `architecture.md` and `code-style.md`, including "Typing".

- Every class lives in `schemas/`. There are two exceptions, both in `config/`: the settings class, and loguru's `InterceptHandler` in `config/logger.py` (see `config.md`).
- A class is a data shape: fields only, no methods. It can extend any type. A function assigned in a class body, like `emit = emit_record` or a lambda, counts as a method.
- Use Pydantic `BaseModel` for data coming in from outside: request bodies, replies from outside systems and tool arguments. It's checked once, at the edge, with `model_validate`.
- Use `TypedDict` for everything inside: shapes our own functions pass to each other.
- The agent's state is a TypedDict that extends `langchain.agents.AgentState`. `create_agent` accepts nothing else.
- No dataclasses.
- An outside field with a name too short for our naming rules, like an API's `to`, gets a descriptive name plus a Pydantic `Field(alias="to")`.
- Custom errors are classes too, so they live here.
- Schemas import nothing from `app`. Every other layer imports them.
- When a library's type hints are wrong under mypy, type the parts we use as `Protocol`s in a `schemas/` file named after the library, and assign the real object to a name of that Protocol type so mypy checks it matches. Add a member, as a `...` or `@property` stub, when you need one. Mark a Protocol `@runtime_checkable` when code narrows to it with `isinstance`.
