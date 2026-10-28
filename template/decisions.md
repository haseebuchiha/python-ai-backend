# Decisions

What we chose and why, and what's still open.

## Setup decisions

- **Python 3.13 with uv** for packages, the virtual environment and the Python version, so one tool sets up the whole environment and `uv.lock` pins exact versions.
- **FastAPI**, installed as `fastapi[standard]`, because that brings the `fastapi` command and uvicorn with it.
- **Folders:** everything lives in `app/`, FastAPI's own convention, so imports read `from app.services import ...`. Inside it, folders are split by what the code does, not by feature, so each kind of code has one home: `routes/`, `services/`, `models/`, `schemas/` and `config/`. `main.py` only creates the app and plugs in the routes.
- **Layers:** routes → services → models → config → schemas, and nothing imports upward, so every decision ends up in services and every read or write of data in models. import-linter enforces it, so the layout can't drift.
- **`models/` is the only place that reads or writes data**, outside systems and LangGraph's store, so data access has one home and makes no decisions.
- **Agents:** LangChain's `create_agent`, because it builds the LangGraph graph for us. A pause for a person's approval is its `HumanInTheLoopMiddleware` on the tool that needs it.
- **Model:** `ChatOpenAI` from `langchain-openai`, with `base_url` from settings, so any OpenAI-compatible endpoint or model can be swapped in.
- **Memory:** LangGraph's Postgres checkpointer saves each conversation under its `thread_id`, and LangGraph's store holds anything needed across conversations. Both share one psycopg connection pool, because `from_conn_string` opens a single connection that every request shares and that never reconnects. Both create their own tables with `setup()` and run as their async versions under FastAPI.
- **No ORM and no tables of our own** until the project needs them, because LangGraph manages its own Postgres tables.
- **No LangGraph Agent Server:** self-hosting it in production needs a paid LangSmith license, and FastAPI plus the checkpointer covers what we need.
- **The lifespan** in `app/config/` opens the Postgres pool once at startup and hands the checkpointer and store to every request, so nothing else opens a connection. Services receive the checkpointer only to pass it to `create_agent`.
- **Pydantic at the edges:** data entering from outside (request bodies, replies from outside systems, environment settings and tool arguments) is checked once, with Pydantic, where it enters, so nothing unchecked gets further in.
- **TypedDict inside**, including the agent state, which extends `langchain.agents.AgentState`, because `create_agent` accepts nothing else and plain dicts keep the inside light.
- **Every class lives in `app/schemas/`**, the bottom layer, which imports nothing from `app`, so every layer can use them. The one exception is the pydantic-settings `BaseSettings` class in `app/config/`. No dataclasses.
- **Environment variables are read only in `app/config/`**, through pydantic-settings, so settings are checked in one place.
- **Library type hints that break under mypy** get typed as `Protocol`s in `app/schemas/`, so strict mypy still checks how we use the library.
- **mypy's pydantic plugin runs without `init_forbid_extra`:** it rejected LangChain's documented `ChatOpenAI(model=..., base_url=...)`, because those are aliased fields. `init_typed` stays on, since documented usage passes with it.
- **Logging:** loguru, one shared logger in `config/`, so there's one place to set the format. FastAPI's `app.exception_handler` sends every uncaught error to it.
- **Standard-library logs reach loguru** (uvicorn, FastAPI, LangChain) through loguru's documented `InterceptHandler` in `app/config/logger.py`, so every log goes through one logger. It's the one class with a method we allow, through a narrow lint exception (see "Lint rules").
- **Tests:** pytest, with no plugins for now, to keep the setup small.
- **Formatting:** ruff format, because ruff already does the linting, so one tool covers both.
- **Checks:** ruff, our own checker in `lint/`, complexipy, import-linter and mypy (strict), all run by pre-commit before each commit, so the rules hold without anyone remembering to run them.
- **SDK first:** get everything we can out of LangChain, LangGraph, FastAPI and Pydantic before writing anything by hand, because SDK code is already tested and maintained.

## Lint rules

Everything runs in pre-commit: ruff (all rules on), our own checker in `lint/` (rule ids `BOS…`), complexipy, import-linter and mypy (strict). No `# noqa` or `# type: ignore` anywhere; to change a rule, change the config.

- **No comments or docstrings**, only a shebang: `BOS101`, `BOS102`. Suppression comments get their own message: `BOS103`. LangChain tool descriptions go in `@tool(description=...)`.
- **No loops** (`for`, `while`, `async for`); comprehensions are fine: `BOS201`. **A comprehension or `map(...)` whose value is thrown away** is a loop too, including one assigned to `_` or an `_`-prefixed name, a bare unpacking like `[*map(f, xs)]`, and a bare `functools.reduce(...)`: `BOS202`.
- **Bind each name once per scope**, `+=` included, `_` exempt: `BOS301`. A name set in both arms of an if/else, try/except or match goes in a function that returns it. `nonlocal` and `global` are banned, since they only exist to rebind: `BOS301`.
- **Never change a parameter**, its attributes or its items, including through mutating methods (`append`, `pop`, `update`, `add`, `popleft`, `rotate`, `intersection_update` and the like), unbound calls like `list.append(param, x)`, `operator.setitem` and the in-place operator functions (`iadd` and kin), `del` or `setattr`: `BOS302`. FastAPI routes return a response object instead of setting `response.status_code`.
- **Classes are data shapes only**: a class must extend some type (BaseModel, TypedDict, LangGraph's `AgentState`, an exception, anything) and can't have methods, except `...` stubs in a `Protocol`: `BOS401`, `BOS402`. A function attached by assignment in a class body (`emit = emit_record`, a lambda, `staticmethod(...)`) counts as a method: `BOS402`.
- **Classes live in `app/schemas/`**, the settings class in `app/config/` and nowhere else, `app/schemas/` included; tests and the checker's own `lint/schemas.py` too: `BOS403`. Paths count from the project root, so `app/services/lint/schemas.py` or a nested `x/app/schemas/` gets no allowance.
- **One exception for loguru's `InterceptHandler`**: `app/config/logger.py`, if it imports loguru, may hold one module-level `class InterceptHandler(logging.Handler)` whose whole body is an undecorated `def emit(self, record: logging.LogRecord) -> None`. It skips `BOS402` and `BOS403` only; `emit` still follows every other rule.
- **No else after a branch that returns or raises**; `elif` chains are fine: `BOS501` (ruff's RET505/RET506 are off because they also flag `elif`).
- **No nested ternaries**: `BOS502`. **No negated condition with an else**, and the message spells out the flipped version, so ruff's suggested `a if not x else b` becomes `b if x else a`: `BOS503`. **At most 2 `and`/`or` in one expression**: `BOS504`.
- **At most 3 arguments**, the third can be an options object: ruff PLR0913, PLR0917, plus `BOS602`, which also counts `_`-prefixed parameters and counts `*args` and `**kwargs` as one each (`self` and `cls` are free).
- **Complexity at most 3**: ruff C901. **Cognitive complexity at most 5**: complexipy.
- **At most 8 statements per function, 10 in `routes/`**: ruff PLR0915, with `app/routes/ruff.toml` raising it there. **A nested ruff config must extend the root and change only that limit, to at most 10**: `python -m lint.configs`, its own pre-commit hook.
- **One level of block nesting**: ruff PLR1702 (a preview rule, switched on by name).
- **Return straight away** instead of assigning then returning: ruff RET504. **Return the condition** instead of `if x: return True`: ruff SIM103.
- **No print**: ruff T20. **Security, timezone-aware datetimes, pytest style**: ruff S, DTZ, PT.
- **A nested function that uses nothing from its parent moves to module level**: `BOS601`.
- **Names are 3 to 40 characters** (`id`, `ok`, `_` exempt): `BOS701`. An outside field like an API's `to` gets a descriptive name and `Field(alias="to")`. **No abbreviations** (unicorn's list plus `qty`, `amt`, `cnt`; `args`, `kwargs`, `params`, `env`, `self`, `cls` allowed): `BOS702`. **No type prefixes** like `str_` or `dict_`: `BOS703`. **No vague whole names** like `data`, `result`, `results`, `output` or `payload` (`response` is fine, FastAPI uses it): `BOS704`. **Module-level constants are UPPER_CASE**: a literal, arithmetic or concatenation of literals, a tuple of literals like `ALLOWED_DECISIONS = ("approve", "reject")`, or None; calls like `app = FastAPI()` stay lowercase: `BOS705`.
- **Collections get plural names**, Rails style via `inflection`: lists, sets, `tuple[X, ...]` and functions returning them `BOS801`; dicts and mappings `BOS802`, where `prices_by_sku` is fine. Fixed-size tuples like `tuple[str, str]` don't count. Optional, union, `Annotated`, quoted and aliased annotations are unwrapped. Uncountable nouns (history, stock, inventory, feedback, staff and similar) count as plural.
- **No dataclasses** (`dataclasses`, `pydantic.dataclasses`), **no `cast`, no `no_type_check`**: `BOS901`. **Environment variables** (`os.environ`, `os.getenv`, `os.putenv` and kin, the same on `posix` and `nt`, and dotenv's `load_dotenv`, `dotenv_values` and `find_dotenv`) **only in `app/config/`**: `BOS902`. **Only imports under `if TYPE_CHECKING:`** and its else, so a typed stub there can't cover an untyped definition (a `cast` without `cast`): `BOS903`.
- **No explicit `Any`**: mypy `disallow_any_explicit`. **Pydantic models are type-checked strictly**: mypy's pydantic plugin, with `init_typed` and `warn_required_dynamic_aliases`. `init_forbid_extra` is off, because it rejected LangChain's documented `ChatOpenAI(model=..., base_url=...)`.
- **Tests** skip the statement limit and the vague-name ban, may define classes, and may use `assert`, only inside the real test folders: top-level `tests/`, `lint/tests/` and a top-level `conftest.py`. A `test_*.py` or `conftest.py` anywhere else gets the normal rules, in our checker and ruff alike.
- **No file-length limit**: long service modules are fine.
- **Layers**: routes → services → models → config → schemas, nothing imports upward, and routes never import models directly: import-linter. **Services never import `pydantic`, `pydantic_core` or `pydantic_settings` directly**, though they may use schemas built on them: import-linter. "Only models talk to the database" waits until we pick a database library.

## Project decisions

_New decisions for this project go here, one line each: the choice, then why._

## Open

- CI: run `uv run pre-commit run --all-files` and `uv run pytest` on every push.
- The SDK-first review: an AI step that flags hand-written code an SDK already covers. A proposal exists; nothing is built yet.
- `.env.example`, written together with the settings class.
- The HTTP client for calling outside systems (httpx or another).
- Agent details, to settle while building:
  - Two messages on the same thread arriving while the agent is still answering.
  - Long chat histories (summarising older messages).
  - Tracing what the agent did.
  - Testing agents without calling a real model.
