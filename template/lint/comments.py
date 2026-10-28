import ast
import io
import re
import tokenize

from lint.core import report
from lint.schemas import Rule, SourceFile, Violation

NO_COMMENTS = Rule(
    "BOS101",
    "Comments are not allowed. Put the intent in a well-named function "
    "or variable instead.",
)
NO_DOCSTRINGS = Rule(
    "BOS102",
    "Docstrings and bare strings are not allowed. Name things so they explain "
    "themselves; LangChain tool descriptions go in @tool(description=...).",
)
NO_SUPPRESSIONS = Rule(
    "BOS103",
    "Suppression comments ({}) are not allowed. Fix the code, or change the "
    "shared lint config if the rule itself is wrong.",
)
SUPPRESSION_PATTERN = re.compile(
    r"noqa|type:\s*ignore|pyright:|mypy:|ruff:|pylint:|pragma:|fmt:|isort:",
    re.IGNORECASE,
)


def comment_tokens(text: str) -> list[tokenize.TokenInfo]:
    tokens = tokenize.generate_tokens(io.StringIO(text).readline)
    return [token for token in tokens if token.type == tokenize.COMMENT]


def is_shebang(token: tokenize.TokenInfo) -> bool:
    return token.start == (1, 0) and token.string.startswith("#!")


def comment_violation(token: tokenize.TokenInfo) -> Violation:
    suppression = SUPPRESSION_PATTERN.search(token.string)
    rule = NO_SUPPRESSIONS if suppression else NO_COMMENTS
    detail = suppression.group() if suppression else ""
    line, column = token.start
    return Violation(line, column + 1, rule.code, rule.message.format(detail))


def comment_violations(source: SourceFile) -> list[Violation]:
    return [
        comment_violation(token)
        for token in comment_tokens(source.text)
        if not is_shebang(token)
    ]


def is_bare_string(node: ast.AST) -> bool:
    return (
        isinstance(node, ast.Expr)
        and isinstance(node.value, ast.Constant)
        and isinstance(node.value.value, str)
    )


def docstring_violations(source: SourceFile) -> list[Violation]:
    return [
        report(NO_DOCSTRINGS, node)
        for node in ast.walk(source.tree)
        if is_bare_string(node)
    ]
