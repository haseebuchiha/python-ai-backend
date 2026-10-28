---
paths:
  - "app/config/**"
---

# Config rules

These cover settings, the logger and the startup lifespan. The project-wide rules are in `architecture.md` and `code-style.md`.

## Settings

- `config/` is the only place that reads environment variables, through a pydantic-settings `BaseSettings` class. `os.environ`, `os.getenv` (and the same on `posix` and `nt`) and dotenv's `load_dotenv`, `dotenv_values` and `find_dotenv` are banned everywhere else.
- When you add a setting, add it to `.env.example` too.

## Logger

- There's one shared logger, loguru, set up in `config/`. FastAPI's `app.exception_handler` sends every uncaught error to it.
- `print` is banned. Log instead.
- Standard-library logs (uvicorn, FastAPI, LangChain) reach loguru through loguru's `InterceptHandler`, in `config/logger.py`. It's the one class with a method allowed outside `schemas/`, and only in this exact shape: one module-level `class InterceptHandler(logging.Handler)` whose whole body is `def emit(self, record: logging.LogRecord) -> None`, with no decorators and no attributes, in a module that imports loguru. Any other shape gets the usual `BOS402` and `BOS403` errors.
- `emit` still follows every other rule, so keep it short: look up loguru's level and the caller's depth in module-level functions, then call `logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())`.

## Lifespan

- `config/lifespan.py` holds FastAPI's `lifespan`. It runs once when the app starts.
- It opens one psycopg `AsyncConnectionPool` with `open=False`, inside `async with`, using `{"autocommit": True, "prepare_threshold": 0, "row_factory": dict_row}`.
- It builds `AsyncPostgresSaver` and `AsyncPostgresStore` on that pool, and calls `setup()` on both, which creates their tables.
- It yields `{"checkpointer": ..., "store": ...}`, which every request reads from `request.state`.
- Never use `from_conn_string`. It opens a single connection that every request has to share, and it never reconnects.
- `config/` imports nothing from the layers above it.
