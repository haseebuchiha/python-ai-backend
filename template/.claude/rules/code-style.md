# Code style

## Rules

- No comments and no docstrings. Names and small functions explain the code.
- No `# noqa` and no `# type: ignore`. Change the code, not the rule.
- Clear names, Rails style. No single letters, no abbreviations, no vague names like `data` or `result`.
- Names that hold or return a collection are plural, like `products`, or `prices_by_sku` for a mapping.
- Functions have 8 statements at most, or 10 in `routes/`. Lines aren't counted.
- Functions take at most 3 parameters. The third can be an options TypedDict.
- One level of nesting, complexity of at most 3, and cognitive complexity of at most 5.
- No loops: use comprehensions. Bind each name once, and never change a parameter.
- No `else` after a `return` or `raise`. Return early instead.
- Classes live only in `schemas/`, as data shapes with no methods. The two exceptions are in `config/`: the settings class, and loguru's `InterceptHandler`.
- Constants that hold a plain value, or a tuple of plain values, are in capitals.
- Processes are built step by step, as shown in "Writing a service" in `architecture.md`.
- The full rule list, and what enforces each rule, is under "Lint rules" in `decisions.md`.

## Typing

- Data coming in from outside is checked with Pydantic, once, at the edge: request bodies, replies from outside systems, settings and tool arguments.
- Everything inside is a TypedDict. The agent's state has to be one anyway, because `create_agent` accepts nothing else.
- No dataclasses, and no `Any` written by us.
- Only imports go under `if TYPE_CHECKING:` and its else.

## Checks

- `uv run pre-commit run --all-files` runs every check. Pre-commit runs them before each commit too.
- `uv run pytest` runs the tests.
- Fix everything the checks report before moving on.
