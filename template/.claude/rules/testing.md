---
paths:
  - "tests/**"
  - "lint/tests/**"
  - "conftest.py"
---

# Testing rules

These cover tests. The project-wide rules are in `architecture.md` and `code-style.md`.

- Tests follow the same lint rules, with four exceptions: they may use `assert`, skip the statement limit, use vague names, and define classes.
- Those exceptions apply only inside the real test folders: top-level `tests/`, `lint/tests/`, and a top-level `conftest.py`. A `test_*.py` or `conftest.py` anywhere else, like `app/services/test_quotes.py`, gets the normal rules.
- Use LangGraph's in-memory checkpointer and store instead of Postgres.
- Every lint rule in `lint/` has a passing and a failing example in `lint/tests/`.
- How we test the app itself, including agents without calling a real model, is still open in `decisions.md`.
