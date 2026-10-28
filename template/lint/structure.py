import ast
from pathlib import Path

from lint.banned import import_origins, qualified_name
from lint.core import is_file, is_inside, report
from lint.schemas import Rule, SourceFile, Violation
from lint.syntax import (
    FUNCTION_TYPES,
    Function,
    assigned_targets,
    declared_outer_names,
    dotted_tail,
    functions,
    is_ellipsis,
    is_none,
    is_store,
    name_of,
    parameter_names,
    scope_nodes,
    unsubscripted,
)

NO_LOOPS = Rule(
    "BOS201",
    "Loops are not allowed. Use a comprehension, map/filter, any/all/sum, "
    "or recursion through a named function.",
)
PLAIN_CLASS = Rule(
    "BOS401",
    "Class `{}` extends nothing. Base it on a type such as BaseModel, TypedDict, "
    "an Enum or an exception, or use module-level functions instead.",
)
CLASS_METHOD = Rule(
    "BOS402",
    "Data shapes have no methods. Move `{}` to a module-level function that "
    "takes the shape as an argument.",
)
MISPLACED_CLASS = Rule(
    "BOS403",
    "Class `{}` is defined outside app/schemas/. Pydantic models, TypedDicts, "
    "agent state and exceptions live there; only the pydantic-settings class "
    "lives in app/config/.",
)
MISPLACED_SETTINGS = Rule(
    "BOS403",
    "Settings class `{}` is defined outside app/config/. The pydantic-settings "
    "class lives there and nowhere else.",
)
HANDLER_HINT = (
    " The one exception is loguru's InterceptHandler in app/config/logger.py: "
    "a single module-level `class InterceptHandler(logging.Handler)` whose "
    "whole body is `def emit(self, record: logging.LogRecord) -> None`, "
    "undecorated, in a module that imports loguru."
)
DISCARDED_LOOP = Rule(
    "BOS202",
    "This comprehension, map(...), unpacking or reduce(...) runs only for its side "
    "effects and its value is thrown away (a bare statement, or assigned to an "
    "_-prefixed name), which is a loop in disguise. Use the value, or pass the "
    "whole collection to one call, e.g. sys.stdout.writelines(lines).",
)
MOVABLE_FUNCTION = Rule(
    "BOS601",
    "Nested function `{}` uses nothing from the enclosing function. "
    "Move it to module level.",
)
TOO_MANY_PARAMETERS = Rule(
    "BOS602",
    "{}; the limit is 3. Every parameter counts, _-prefixed ones too, and "
    "*args and **kwargs count as one each (self and cls are free). Group the "
    "rest into an options object.",
)
LOOP_TYPES = (ast.For, ast.AsyncFor, ast.While)
DEFINITION_TYPES = (*FUNCTION_TYPES, ast.ClassDef)
COMPREHENSION_TYPES = (ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)
LAZY_LOOP_CALLS = frozenset({"map", "filter", "starmap"})
CONSUMER_CALLS = frozenset(
    {
        "list",
        "tuple",
        "set",
        "frozenset",
        "dict",
        "sorted",
        "any",
        "all",
        "sum",
        "min",
        "max",
        "deque",
    },
)
UNPACKING_TYPES = (ast.List, ast.Tuple, ast.Set)
REDUCE_CALL = "reduce"
FUNCTION_WRAPPERS = frozenset(
    {
        "staticmethod",
        "classmethod",
        "property",
        "cached_property",
        "partial",
        "partialmethod",
        "MethodType",
    },
)
SCHEMA_FOLDER: tuple[str, str] = ("app", "schemas")
CHECKER_SCHEMAS: tuple[str, str] = ("lint", "schemas.py")
CONFIG_FOLDER: tuple[str, str] = ("app", "config")
LOGGER_FILE: tuple[str, str, str] = ("app", "config", "logger.py")
INTERCEPT_HANDLER = "InterceptHandler"
HANDLER_BASES = ["logging.Handler"]
EMIT_PARAMETERS = [("self", ""), ("record", "logging.LogRecord")]
LOGURU_IMPORTS = frozenset({"loguru", "loguru.logger"})
MAX_PARAMETERS = 3
FREE_PARAMETERS = frozenset({"self", "cls"})


def loop_violations(source: SourceFile) -> list[Violation]:
    return [
        report(NO_LOOPS, node)
        for node in ast.walk(source.tree)
        if isinstance(node, LOOP_TYPES)
    ]


def is_lazy_loop(node: ast.AST) -> bool:
    lazy_call = isinstance(node, ast.Call) and dotted_tail(node.func) in LAZY_LOOP_CALLS
    return lazy_call or isinstance(node, COMPREHENSION_TYPES)


def is_consumed_loop(node: ast.expr) -> bool:
    return (
        isinstance(node, ast.Call)
        and dotted_tail(node.func) in CONSUMER_CALLS
        and any(is_lazy_loop(argument) for argument in node.args)
    )


def is_unpacked_loop(node: ast.expr) -> bool:
    return isinstance(node, UNPACKING_TYPES) and any(
        isinstance(element, ast.Starred) and is_discarded_value(element.value)
        for element in node.elts
    )


def is_discarded_value(node: ast.expr) -> bool:
    reduce_call = isinstance(node, ast.Call) and dotted_tail(node.func) == REDUCE_CALL
    loop = is_lazy_loop(node) or is_consumed_loop(node)
    return loop or reduce_call or is_unpacked_loop(node)


def is_throwaway_assignment(node: ast.Assign | ast.AnnAssign) -> bool:
    throwaway = all(
        name_of(target).startswith("_") for target in assigned_targets(node)
    )
    return throwaway and node.value is not None and is_discarded_value(node.value)


def is_discarded_statement(node: ast.AST) -> bool:
    bare = isinstance(node, ast.Expr) and is_discarded_value(node.value)
    assigned = isinstance(node, ast.Assign | ast.AnnAssign) and (
        is_throwaway_assignment(node)
    )
    return bare or assigned


def discarded_loop_violations(source: SourceFile) -> list[Violation]:
    return [
        report(DISCARDED_LOOP, node)
        for node in ast.walk(source.tree)
        if is_discarded_statement(node)
    ]


def base_names(node: ast.ClassDef) -> set[str]:
    return {dotted_tail(unsubscripted(base)) for base in node.bases}


def is_stub(function: Function) -> bool:
    first = function.body[0]
    return (
        len(function.body) == 1
        and isinstance(first, ast.Expr)
        and is_ellipsis(first.value)
    )


def class_methods(node: ast.ClassDef) -> list[Function]:
    protocol = "Protocol" in base_names(node)
    return [
        statement
        for statement in node.body
        if isinstance(statement, FUNCTION_TYPES)
        and not (protocol and is_stub(statement))
    ]


def is_function_name(name: str) -> bool:
    return name[:1].islower() or (name.startswith("_") and not name.isupper())


def is_function_value(value: ast.expr) -> bool:
    reference = isinstance(value, ast.Name | ast.Attribute) and is_function_name(
        dotted_tail(value)
    )
    wrapped = (
        isinstance(value, ast.Call) and dotted_tail(value.func) in FUNCTION_WRAPPERS
    )
    return isinstance(value, ast.Lambda) or reference or wrapped


def assigned_methods(node: ast.ClassDef) -> list[ast.Assign | ast.AnnAssign]:
    return [
        statement
        for statement in node.body
        if isinstance(statement, ast.Assign | ast.AnnAssign)
        and statement.value is not None
        and is_function_value(statement.value)
    ]


def target_label(statement: ast.Assign | ast.AnnAssign) -> str:
    return ", ".join(ast.unparse(target) for target in assigned_targets(statement))


def is_logging_handler(name: str) -> bool:
    return name.startswith("logging.") and name.endswith("Handler")


def is_handler_in_logger(source: SourceFile, node: ast.ClassDef) -> bool:
    origins = import_origins(source.tree)
    extends_handler = any(
        is_logging_handler(qualified_name(base, origins)) for base in node.bases
    )
    return extends_handler and is_file(source.path, LOGGER_FILE)


def hinted(rule: Rule, source: SourceFile, node: ast.ClassDef) -> Rule:
    hint = HANDLER_HINT if is_handler_in_logger(source, node) else ""
    return Rule(rule.code, rule.message + hint)


def annotation_origin(annotation: ast.expr | None, origins: dict[str, str]) -> str:
    return qualified_name(annotation, origins) if annotation else ""


def has_emit_signature(method: ast.FunctionDef, origins: dict[str, str]) -> bool:
    arguments = method.args
    parameters = [
        (parameter.arg, annotation_origin(parameter.annotation, origins))
        for parameter in arguments.args
    ]
    plain = parameter_names(method) == {"self", "record"} and not arguments.defaults
    return parameters == EMIT_PARAMETERS and plain and is_none(method.returns)


def is_plain_emit(method: ast.FunctionDef, origins: dict[str, str]) -> bool:
    undecorated = method.name == "emit" and not method.decorator_list
    return undecorated and has_emit_signature(method, origins)


def is_emit_method(statement: ast.stmt, origins: dict[str, str]) -> bool:
    return isinstance(statement, ast.FunctionDef) and is_plain_emit(statement, origins)


def is_intercept_shape(node: ast.ClassDef, origins: dict[str, str]) -> bool:
    bases = [qualified_name(base, origins) for base in node.bases]
    plain = not node.keywords and not node.decorator_list
    only_emit = len(node.body) == 1 and is_emit_method(node.body[0], origins)
    return bases == HANDLER_BASES and plain and only_emit


def intercept_handlers(tree: ast.Module) -> list[ast.ClassDef]:
    return [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.ClassDef) and node.name == INTERCEPT_HANDLER
    ]


def is_logger_module(source: SourceFile, origins: dict[str, str]) -> bool:
    imports_loguru = bool(LOGURU_IMPORTS & set(origins.values()))
    return imports_loguru and is_file(source.path, LOGGER_FILE)


def exempt_handlers(source: SourceFile) -> list[ast.ClassDef]:
    origins = import_origins(source.tree)
    handlers = intercept_handlers(source.tree)
    allowed = len(handlers) == 1 and is_logger_module(source, origins)
    return [
        intercept_class
        for intercept_class in handlers
        if allowed
        and intercept_class in source.tree.body
        and is_intercept_shape(intercept_class, origins)
    ]


def single_class_violations(source: SourceFile, node: ast.ClassDef) -> list[Violation]:
    shape_violations: list[Violation] = (
        [] if node.bases else [report(PLAIN_CLASS, node, node.name)]
    )
    method_rule = hinted(CLASS_METHOD, source, node)
    method_violations = [
        report(method_rule, method, method.name) for method in class_methods(node)
    ]
    attached_violations = [
        report(method_rule, statement, target_label(statement))
        for statement in assigned_methods(node)
    ]
    return [*shape_violations, *method_violations, *attached_violations]


def is_settings_class(node: ast.ClassDef) -> bool:
    return "BaseSettings" in base_names(node)


def is_schema_place(path: Path) -> bool:
    return is_inside(path, SCHEMA_FOLDER) or is_file(path, CHECKER_SCHEMAS)


def may_define_class(source: SourceFile, node: ast.ClassDef) -> bool:
    allowed_place = (
        is_inside(source.path, CONFIG_FOLDER)
        if is_settings_class(node)
        else is_schema_place(source.path)
    )
    return source.is_test or allowed_place


def placement_rule(source: SourceFile, node: ast.ClassDef) -> Rule:
    rule = MISPLACED_SETTINGS if is_settings_class(node) else MISPLACED_CLASS
    return hinted(rule, source, node)


def placement_violations(source: SourceFile) -> list[Violation]:
    exempt_nodes = exempt_handlers(source)
    return [
        report(placement_rule(source, node), node, node.name)
        for node in ast.walk(source.tree)
        if isinstance(node, ast.ClassDef)
        and not may_define_class(source, node)
        and node not in exempt_nodes
    ]


def counted_parameters(function: Function | ast.Lambda) -> set[str]:
    return parameter_names(function) - FREE_PARAMETERS


def parameter_count_violations(source: SourceFile) -> list[Violation]:
    return [
        report(
            TOO_MANY_PARAMETERS,
            node,
            f"`{getattr(node, 'name', 'lambda')}` takes "
            f"{len(counted_parameters(node))} parameters",
        )
        for node in ast.walk(source.tree)
        if isinstance(node, (*FUNCTION_TYPES, ast.Lambda))
        and len(counted_parameters(node)) > MAX_PARAMETERS
    ]


def class_violations(source: SourceFile) -> list[Violation]:
    exempt_nodes = exempt_handlers(source)
    return [
        violation
        for node in ast.walk(source.tree)
        if isinstance(node, ast.ClassDef) and node not in exempt_nodes
        for violation in single_class_violations(source, node)
    ]


def assigned_names(nodes: list[ast.AST]) -> set[str]:
    return {node.id for node in nodes if isinstance(node, ast.Name) and is_store(node)}


def bound_names(function: Function) -> set[str]:
    nodes = scope_nodes(function)
    defined_names = {node.name for node in nodes if isinstance(node, DEFINITION_TYPES)}
    local_names = parameter_names(function) | assigned_names(nodes) | defined_names
    return local_names - declared_outer_names(function)


def free_names(function: Function) -> set[str]:
    loaded_names = {
        node.id
        for node in ast.walk(function)
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load)
    }
    outer_names = declared_outer_names(function)
    return (loaded_names - bound_names(function) - {function.name}) | outer_names


def uses_enclosing(nested: Function, enclosing: Function) -> bool:
    return bool(free_names(nested) & bound_names(enclosing))


def movable_functions(function: Function) -> list[Function]:
    return [
        node
        for node in scope_nodes(function)
        if isinstance(node, FUNCTION_TYPES) and not uses_enclosing(node, function)
    ]


def nested_function_violations(source: SourceFile) -> list[Violation]:
    return [
        report(MOVABLE_FUNCTION, nested, nested.name)
        for function in functions(source.tree)
        for nested in movable_functions(function)
    ]
