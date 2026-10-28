import ast

from lint.banned import import_origins, qualified_name
from lint.core import report
from lint.schemas import Rule, SourceFile, Violation
from lint.syntax import (
    Function,
    all_scopes,
    assigned_targets,
    dotted_tail,
    functions,
    is_store,
    parameter_names,
    root_name,
    scope_nodes,
)

REASSIGNMENT = Rule(
    "BOS301",
    "`{}` is already bound in this scope. Bind each name once: pick a new name. "
    "If it is set in both arms of an if/else, try/except or match, extract a "
    "function that returns the value from each arm.",
)
OUTER_REBINDING = Rule(
    "BOS301",
    "`{}` is declared nonlocal or global to rebind a name from an outer scope. "
    "Bind each name once: return the new value from the function instead.",
)
PARAMETER_CHANGE = Rule(
    "BOS302",
    "Parameter `{}` is changed here. Treat parameters as read-only and build "
    "a new value instead.",
)
RESPONSE_CHANGE = Rule(
    "BOS302",
    "Parameter `{}` is changed here. Instead of setting response.status_code or "
    "headers, return a response object, e.g. JSONResponse(content, status_code=201).",
)
MUTATING_METHODS = frozenset(
    {
        "append",
        "extend",
        "insert",
        "pop",
        "popitem",
        "remove",
        "clear",
        "update",
        "setdefault",
        "add",
        "discard",
        "sort",
        "reverse",
        "intersection_update",
        "difference_update",
        "symmetric_difference_update",
        "appendleft",
        "extendleft",
        "rotate",
        "popleft",
        "__setitem__",
        "__delitem__",
        "__setattr__",
        "__delattr__",
    },
)
ATTRIBUTE_SETTERS = frozenset({"setattr", "delattr", "__setattr__", "__delattr__"})
CONTAINER_TYPES = frozenset(
    {
        "list",
        "dict",
        "set",
        "bytearray",
        "deque",
        "OrderedDict",
        "defaultdict",
        "Counter",
        "object",
    },
)
OPERATOR_MUTATORS = (
    "setitem",
    "delitem",
    "iadd",
    "isub",
    "imul",
    "imatmul",
    "itruediv",
    "ifloordiv",
    "imod",
    "ipow",
    "ilshift",
    "irshift",
    "iand",
    "ixor",
    "ior",
    "iconcat",
)
OPERATOR_FUNCTIONS = frozenset(
    f"operator.{name}"
    for mutator in OPERATOR_MUTATORS
    for name in (mutator, f"__{mutator}__")
)


def annotation_only_ids(scope: ast.AST) -> set[int]:
    return {
        id(node.target)
        for node in scope_nodes(scope)
        if isinstance(node, ast.AnnAssign) and node.value is None
    }


def stored_names(scope: ast.AST) -> list[ast.Name]:
    declaration_ids = annotation_only_ids(scope)
    return [
        node
        for node in scope_nodes(scope)
        if isinstance(node, ast.Name)
        and is_store(node)
        and id(node) not in declaration_ids
    ]


def rebinding_violations(scope: ast.AST) -> list[Violation]:
    names = [node for node in stored_names(scope) if node.id != "_"]
    first_bindings = {node.id: node for node in reversed(names)}
    return [
        report(REASSIGNMENT, node, node.id)
        for node in names
        if first_bindings[node.id] is not node
    ]


def reassignment_violations(source: SourceFile) -> list[Violation]:
    return [
        violation
        for scope in all_scopes(source.tree)
        for violation in rebinding_violations(scope)
    ]


def outer_rebinding_violations(source: SourceFile) -> list[Violation]:
    return [
        report(OUTER_REBINDING, node, ", ".join(node.names))
        for node in ast.walk(source.tree)
        if isinstance(node, ast.Nonlocal | ast.Global)
    ]


def is_changed(node: ast.AST) -> bool:
    return isinstance(getattr(node, "ctx", None), ast.Store | ast.Del)


def changed_expressions(function: Function) -> list[ast.AST]:
    return [
        node
        for statement in scope_nodes(function)
        for target in assigned_targets(statement)
        for node in ast.walk(target)
        if is_changed(node)
    ]


def method_receivers(call: ast.Call) -> list[ast.expr]:
    method = call.func
    return (
        [method.value]
        if isinstance(method, ast.Attribute) and method.attr in MUTATING_METHODS
        else []
    )


def setter_targets(call: ast.Call) -> list[ast.expr]:
    return call.args[:1] if dotted_tail(call.func) in ATTRIBUTE_SETTERS else []


def unbound_method_targets(call: ast.Call) -> list[ast.expr]:
    unbound = any(
        dotted_tail(receiver) in CONTAINER_TYPES for receiver in method_receivers(call)
    )
    return call.args[:1] if unbound else []


def operator_targets(call: ast.Call, origins: dict[str, str]) -> list[ast.expr]:
    operator_name = qualified_name(call.func, origins)
    return call.args[:1] if operator_name in OPERATOR_FUNCTIONS else []


def call_targets(call: ast.Call, origins: dict[str, str]) -> list[ast.expr]:
    return [
        *method_receivers(call),
        *setter_targets(call),
        *unbound_method_targets(call),
        *operator_targets(call, origins),
    ]


def mutated_expressions(function: Function, origins: dict[str, str]) -> list[ast.expr]:
    return [
        target
        for node in ast.walk(function)
        if isinstance(node, ast.Call)
        for target in call_targets(node, origins)
    ]


def parameter_rule(name: str) -> Rule:
    return RESPONSE_CHANGE if name == "response" else PARAMETER_CHANGE


def function_parameter_violations(
    function: Function,
    origins: dict[str, str],
) -> list[Violation]:
    parameters = parameter_names(function)
    changed_nodes = [
        *changed_expressions(function),
        *mutated_expressions(function, origins),
    ]
    changed_nodes_by_id = {id(node): node for node in changed_nodes}
    return [
        report(parameter_rule(root_name(node)), node, root_name(node))
        for node in changed_nodes_by_id.values()
        if root_name(node) in parameters
    ]


def parameter_change_violations(source: SourceFile) -> list[Violation]:
    origins = import_origins(source.tree)
    return [
        violation
        for function in functions(source.tree)
        for violation in function_parameter_violations(function, origins)
    ]
