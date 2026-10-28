import ast

from lint.branching import without_unary
from lint.core import is_inside, report
from lint.schemas import Rule, SourceFile, Violation
from lint.syntax import dotted_tail, name_of

type ApiUse = tuple[ast.AST, str]

BANNED_API = Rule("BOS901", "Banned API {}")
ENVIRONMENT_ACCESS = Rule(
    "BOS902",
    "`{}` touches environment variables, which only app/config/ may do. Add a "
    "field to the pydantic-settings class there and pass the setting in.",
)
TYPE_CHECKING_BODY = Rule(
    "BOS903",
    "Only imports go under `if TYPE_CHECKING:` and its else. A typed stub there "
    "and an untyped definition in the else is a cast in disguise. Import the real "
    "typed object, or define it once.",
)
CONFIG_FOLDER: tuple[str, str] = ("app", "config")
DATACLASS_REASON = (
    "no dataclasses. Use a TypedDict for internal data, or a Pydantic model for "
    "data from outside, in app/schemas/."
)
CAST_REASON = (
    "cast() silently switches off type checking. Narrow with isinstance, or "
    "validate with a Pydantic model."
)
NO_TYPE_CHECK_REASON = (
    "no_type_check silently switches off type checking. Fix the types instead."
)
REASONS_BY_API = {
    "dataclasses": DATACLASS_REASON,
    "pydantic.dataclasses": DATACLASS_REASON,
    "typing.cast": CAST_REASON,
    "typing_extensions.cast": CAST_REASON,
    "typing.no_type_check": NO_TYPE_CHECK_REASON,
    "typing_extensions.no_type_check": NO_TYPE_CHECK_REASON,
}
SYSTEM_MODULES = ("os", "posix", "nt")
SYSTEM_ENVIRONMENT_MEMBERS = (
    "environ",
    "environb",
    "getenv",
    "getenvb",
    "putenv",
    "unsetenv",
)
DOTENV_MODULES = ("dotenv", "dotenv.main")
DOTENV_MEMBERS = ("load_dotenv", "dotenv_values", "find_dotenv")
ENVIRONMENT_APIS = frozenset(
    {
        *(
            f"{module}.{member}"
            for module in SYSTEM_MODULES
            for member in SYSTEM_ENVIRONMENT_MEMBERS
        ),
        *(
            f"{module}.{member}"
            for module in DOTENV_MODULES
            for member in DOTENV_MEMBERS
        ),
    },
)


def plain_imports(tree: ast.Module) -> list[ast.alias]:
    return [
        alias
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    ]


def from_imports(tree: ast.Module) -> list[tuple[ast.ImportFrom, ast.alias]]:
    return [
        (node, alias)
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
        for alias in node.names
    ]


def bound_module(alias: ast.alias) -> tuple[str, str]:
    top_module = alias.name.partition(".")[0]
    return (alias.asname, alias.name) if alias.asname else (top_module, top_module)


def import_origins(tree: ast.Module) -> dict[str, str]:
    plain_origins = dict(bound_module(alias) for alias in plain_imports(tree))
    from_origins = {
        alias.asname or alias.name: f"{node.module}.{alias.name}"
        for node, alias in from_imports(tree)
    }
    return {**plain_origins, **from_origins}


def qualified_name(expression: ast.expr, origins: dict[str, str]) -> str:
    if isinstance(expression, ast.Attribute):
        base = qualified_name(expression.value, origins)
        return f"{base}.{expression.attr}" if base else ""
    return origins.get(name_of(expression), "")


def imported_apis(tree: ast.Module) -> list[ApiUse]:
    modules: list[ApiUse] = [(alias, alias.name) for alias in plain_imports(tree)]
    members: list[ApiUse] = [
        (node, f"{node.module}.{alias.name}") for node, alias in from_imports(tree)
    ]
    return [*modules, *members]


def api_uses(tree: ast.Module) -> list[ApiUse]:
    origins = import_origins(tree)
    attribute_uses: list[ApiUse] = [
        (node, qualified_name(node, origins))
        for node in ast.walk(tree)
        if isinstance(node, ast.Attribute)
    ]
    return [*imported_apis(tree), *attribute_uses]


def banned_api(name: str) -> str:
    return next(
        (api for api in REASONS_BY_API if name == api or name.startswith(f"{api}.")),
        "",
    )


def banned_api_violations(source: SourceFile) -> list[Violation]:
    matches = [(node, name, banned_api(name)) for node, name in api_uses(source.tree)]
    return [
        report(BANNED_API, node, f"`{name}`: {REASONS_BY_API[api]}")
        for node, name, api in matches
        if api
    ]


def environment_violations(source: SourceFile) -> list[Violation]:
    allowed = is_inside(source.path, CONFIG_FOLDER)
    return [
        report(ENVIRONMENT_ACCESS, node, name)
        for node, name in api_uses(source.tree)
        if name in ENVIRONMENT_APIS and not allowed
    ]


def is_type_checking(test: ast.expr) -> bool:
    return dotted_tail(without_unary(test)) == "TYPE_CHECKING"


def guarded_statements(node: ast.If) -> list[ast.stmt]:
    return [
        inner
        for statement in [*node.body, *node.orelse]
        for inner in leaf_statements(statement)
    ]


def leaf_statements(statement: ast.stmt) -> list[ast.stmt]:
    return (
        guarded_statements(statement) if isinstance(statement, ast.If) else [statement]
    )


def type_checking_violations(source: SourceFile) -> list[Violation]:
    return [
        report(TYPE_CHECKING_BODY, statement)
        for node in ast.walk(source.tree)
        if isinstance(node, ast.If) and is_type_checking(node.test)
        for statement in guarded_statements(node)
        if not isinstance(statement, ast.Import | ast.ImportFrom)
    ]
