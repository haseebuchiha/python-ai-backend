# python-ai-backend

A copier template for a new Python backend: FastAPI, LangChain agents and LangGraph's Postgres memory. It holds the setup only: tooling, the strict lint rules and our own checker, the folder layout, the typing approach, the AI-assistant rules and pre-commit. A new project passes every check straight after it's created.

## Create a project

```bash
uvx copier copy /Users/apple/Projects/templates/python-ai-backend <dest>
cd <dest> && git init && uv sync && uv run pre-commit install
```

Copier asks for three things: the project name (a human title), the distribution name (kebab-case, taken from the name by default) and a one-line description. The Python package is always `app/`, so imports read `from app.services import ...`.

`uv sync` creates `.venv` and `uv.lock`; the template ships no lockfile, because the lockfile names the project. Commit the new project with git, because `copier update` needs a git repo with a clean tree.

## Pull later template changes

Commit the change in this template repo first, then run this in the project:

```bash
uvx copier update
```

Copier replays your answers, merges the template changes into the project and marks conflicts inline for you to resolve.

## What's included

- Python 3.13 and uv, with the uv build backend packaging `app/`
- FastAPI (`fastapi[standard]`), Pydantic, pydantic-settings, loguru, LangChain with `langchain-openai`, LangGraph with its Postgres checkpointer and store, and psycopg with its pool
- Empty layer packages under `app/`: `routes/` (with its `ruff.toml` raising the statement limit to 10), `services/`, `models/`, `schemas/` and `config/`
- `tests/` with one test, and pytest running it together with the checker's tests
- Strict checks, all run by pre-commit: ruff with every rule on, our own checker in `lint/` (rule ids `BOS…`, with its tests), complexipy, import-linter layer contracts and mypy strict with the pydantic plugin
- Claude Code: `CLAUDE.md`, `AGENTS.md` (Karpathy's guidelines plus an index of the rules) and rule files in `.claude/rules/`
- `decisions.md` with the setup decisions and their reasons, the full lint rule list, and the open questions

## Checks

```bash
uv run pre-commit run --all-files
uv run pytest
```
