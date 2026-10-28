import ast

from lint.core import report
from lint.schemas import Rule, SourceFile, Violation

ELSE_AFTER_EXIT = Rule(
    "BOS501",
    "No else after a branch that ends in return or raise. Drop the else and "
    "dedent its body.",
)
NESTED_TERNARY = Rule(
    "BOS502",
    "Nested conditional expressions are not allowed. Extract a named function "
    "with early returns.",
)
NEGATED_CONDITION = Rule(
    "BOS503",
    "Negated condition with an else. Test `{}` instead and swap the branches.",
)
NEGATED_TERNARY = Rule(
    "BOS503",
    "Negated condition in a conditional expression. Write `{}` instead.",
)
TOO_MANY_BOOLEAN_OPERATORS = Rule(
    "BOS504",
    "This expression has {} and/or operators; the limit is 2. Name the parts "
    "as booleans or small functions.",
)
MAX_BOOLEAN_OPERATORS = 2
POSITIVE_COMPARISONS: dict[type[ast.cmpop], type[ast.cmpop]] = {
    ast.NotEq: ast.Eq,
    ast.IsNot: ast.Is,
    ast.NotIn: ast.In,
}
NEGATED_COMPARISONS = tuple(POSITIVE_COMPARISONS)


def is_elif(node: ast.If) -> bool:
    return (
        len(node.orelse) == 1
        and isinstance(node.orelse[0], ast.If)
        and node.orelse[0].col_offset == node.col_offset
    )


def has_plain_else(node: ast.If) -> bool:
    return bool(node.orelse) and not is_elif(node)


def ends_in_exit(statements: list[ast.stmt]) -> bool:
    return isinstance(statements[-1], ast.Return | ast.Raise)


def else_after_exit_violations(source: SourceFile) -> list[Violation]:
    return [
        report(ELSE_AFTER_EXIT, node.orelse[0])
        for node in ast.walk(source.tree)
        if isinstance(node, ast.If) and has_plain_else(node) and ends_in_exit(node.body)
    ]


def contains_ternary(node: ast.IfExp) -> bool:
    return any(
        isinstance(inner, ast.IfExp)
        for part in (node.test, node.body, node.orelse)
        for inner in ast.walk(part)
    )


def nested_ternary_violations(source: SourceFile) -> list[Violation]:
    return [
        report(NESTED_TERNARY, node)
        for node in ast.walk(source.tree)
        if isinstance(node, ast.IfExp) and contains_ternary(node)
    ]


def is_negated_comparison(test: ast.expr) -> bool:
    return (
        isinstance(test, ast.Compare)
        and len(test.ops) == 1
        and isinstance(test.ops[0], NEGATED_COMPARISONS)
    )


def is_negated(test: ast.expr) -> bool:
    negated_not = isinstance(test, ast.UnaryOp) and isinstance(test.op, ast.Not)
    return negated_not or is_negated_comparison(test)


def negated_branches(tree: ast.Module) -> list[ast.If | ast.IfExp]:
    return [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.If | ast.IfExp) and is_negated(node.test)
    ]


def has_else(node: ast.If | ast.IfExp) -> bool:
    return isinstance(node, ast.IfExp) or has_plain_else(node)


def flipped_test(test: ast.expr) -> ast.expr:
    if isinstance(test, ast.Compare):
        positive = POSITIVE_COMPARISONS[type(test.ops[0])]()
        return ast.Compare(test.left, [positive], test.comparators)
    return test.operand if isinstance(test, ast.UnaryOp) else test


def negated_violation(node: ast.If | ast.IfExp) -> Violation:
    if isinstance(node, ast.IfExp):
        flipped = ast.IfExp(flipped_test(node.test), node.orelse, node.body)
        return report(NEGATED_TERNARY, node, ast.unparse(flipped))
    return report(NEGATED_CONDITION, node, ast.unparse(flipped_test(node.test)))


def negated_condition_violations(source: SourceFile) -> list[Violation]:
    return [
        negated_violation(node)
        for node in negated_branches(source.tree)
        if has_else(node)
    ]


def operator_count(node: ast.AST) -> int:
    if isinstance(node, ast.BoolOp):
        return (
            len(node.values) - 1 + sum(operator_count(value) for value in node.values)
        )
    if isinstance(node, ast.UnaryOp):
        return operator_count(node.operand)
    return 0


def without_unary(node: ast.AST) -> ast.AST:
    return without_unary(node.operand) if isinstance(node, ast.UnaryOp) else node


def nested_operation_ids(tree: ast.Module) -> set[int]:
    return {
        id(without_unary(value))
        for node in ast.walk(tree)
        if isinstance(node, ast.BoolOp)
        for value in node.values
    }


def boolean_operator_violations(source: SourceFile) -> list[Violation]:
    nested_ids = nested_operation_ids(source.tree)
    return [
        report(TOO_MANY_BOOLEAN_OPERATORS, node, str(operator_count(node)))
        for node in ast.walk(source.tree)
        if isinstance(node, ast.BoolOp)
        and id(node) not in nested_ids
        and operator_count(node) > MAX_BOOLEAN_OPERATORS
    ]
