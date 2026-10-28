import ast

type Function = ast.FunctionDef | ast.AsyncFunctionDef

FUNCTION_TYPES = (ast.FunctionDef, ast.AsyncFunctionDef)
SCOPE_TYPES = (
    *FUNCTION_TYPES,
    ast.Lambda,
    ast.ClassDef,
    ast.ListComp,
    ast.SetComp,
    ast.DictComp,
    ast.GeneratorExp,
)


def scope_nodes(scope: ast.AST) -> list[ast.AST]:
    return [
        descendant
        for child in ast.iter_child_nodes(scope)
        for descendant in subtree_nodes(child)
    ]


def subtree_nodes(node: ast.AST) -> list[ast.AST]:
    inner_nodes: list[ast.AST] = (
        [] if isinstance(node, SCOPE_TYPES) else scope_nodes(node)
    )
    return [node, *inner_nodes]


def all_scopes(tree: ast.Module) -> list[ast.AST]:
    return [tree, *(node for node in ast.walk(tree) if isinstance(node, SCOPE_TYPES))]


def functions(tree: ast.AST) -> list[Function]:
    return [node for node in ast.walk(tree) if isinstance(node, FUNCTION_TYPES)]


def parameter_names(function: Function | ast.Lambda) -> set[str]:
    arguments = function.args
    all_parameters = [
        *arguments.posonlyargs,
        *arguments.args,
        *arguments.kwonlyargs,
        arguments.vararg,
        arguments.kwarg,
    ]
    return {parameter.arg for parameter in all_parameters if parameter}


def assigned_targets(node: ast.AST) -> list[ast.expr]:
    if isinstance(node, ast.Assign | ast.Delete):
        return node.targets
    if isinstance(node, ast.AugAssign | ast.AnnAssign | ast.NamedExpr):
        return [node.target]
    return []


def is_store(node: ast.AST) -> bool:
    return isinstance(getattr(node, "ctx", None), ast.Store)


def name_of(expression: ast.AST) -> str:
    return expression.id if isinstance(expression, ast.Name) else ""


def dotted_tail(expression: ast.AST) -> str:
    return (
        expression.attr
        if isinstance(expression, ast.Attribute)
        else name_of(expression)
    )


def unsubscripted(expression: ast.AST) -> ast.AST:
    return expression.value if isinstance(expression, ast.Subscript) else expression


def root_name(expression: ast.AST) -> str:
    return (
        root_name(expression.value)
        if isinstance(expression, ast.Attribute | ast.Subscript)
        else name_of(expression)
    )


def is_ellipsis(expression: ast.AST) -> bool:
    return isinstance(expression, ast.Constant) and expression.value is Ellipsis


def is_none(expression: ast.AST | None) -> bool:
    return isinstance(expression, ast.Constant) and expression.value is None


def declared_outer_names(scope: ast.AST) -> set[str]:
    return {
        name
        for node in scope_nodes(scope)
        if isinstance(node, ast.Nonlocal | ast.Global)
        for name in node.names
    }
