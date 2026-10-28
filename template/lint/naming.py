import ast
import re

from lint.core import report
from lint.schemas import NameCheck, Rule, SourceFile, Violation
from lint.syntax import assigned_targets

NAME_LENGTH = Rule(
    "BOS701",
    "Name length: {}. Names are 3 to 40 characters; only id, ok and _ are shorter.",
)
ABBREVIATION = Rule("BOS702", "Abbreviation {}. Spell the word out.")
TYPE_PREFIX = Rule(
    "BOS703",
    "Type prefix {}. Drop it and name what the value means.",
)
VAGUE_NAME = Rule(
    "BOS704",
    "`{}` is too vague on its own. Say what it holds, e.g. customer_data.",
)
CONSTANT_CASE = Rule(
    "BOS705",
    "Module-level `{}` holds a literal, a tuple of literals, arithmetic or "
    "concatenation of literals, or None, so name it in UPPER_CASE.",
)
MIN_NAME_LENGTH = 3
MAX_NAME_LENGTH = 40
SHORT_NAME_EXCEPTIONS = frozenset({"id", "ok", "_"})
WORD_PATTERN = re.compile(r"[A-Z]+(?![a-z])|[A-Z]?[a-z]+|\d+")
TYPE_PREFIXES = (
    "str_",
    "int_",
    "num_",
    "arr_",
    "obj_",
    "bool_",
    "bln_",
    "fn_",
    "func_",
    "lst_",
    "dict_",
)
VAGUE_NAMES = frozenset(
    {
        "data",
        "result",
        "res",
        "ret",
        "item",
        "obj",
        "val",
        "tmp",
        "temp",
        "foo",
        "bar",
        "info",
        "stuff",
        "thing",
        "handle",
        "handler",
        "process",
        "manager",
        "helper",
        "util",
        "utils",
        "cb",
        "fn",
        "func",
        "arr",
        "str",
        "num",
        "flag",
        "results",
        "output",
        "payload",
        "qty",
        "amt",
        "cnt",
    },
)
REPLACEMENTS_BY_ABBREVIATION = {
    "acc": "accumulator",
    "amt": "amount",
    "arg": "argument",
    "arr": "array",
    "attr": "attribute",
    "attrs": "attributes",
    "btn": "button",
    "cb": "callback",
    "cfg": "config",
    "cnt": "count",
    "conf": "config",
    "conn": "connection",
    "ctx": "context",
    "cur": "current",
    "curr": "current",
    "db": "database",
    "def": "definition",
    "dest": "destination",
    "dev": "development",
    "dir": "directory",
    "dirs": "directories",
    "doc": "document",
    "docs": "documents",
    "dst": "destination",
    "e": "error",
    "el": "element",
    "elem": "element",
    "envs": "environments",
    "err": "error",
    "ev": "event",
    "evt": "event",
    "exc": "error",
    "ext": "extension",
    "exts": "extensions",
    "fn": "function",
    "func": "function",
    "i": "index",
    "idx": "index",
    "j": "index",
    "len": "length",
    "lib": "library",
    "mod": "module",
    "msg": "message",
    "num": "number",
    "obj": "object",
    "opts": "options",
    "param": "parameter",
    "pkg": "package",
    "prev": "previous",
    "prod": "production",
    "prop": "property",
    "props": "properties",
    "qty": "quantity",
    "ref": "reference",
    "refs": "references",
    "rel": "relative",
    "req": "request",
    "res": "response",
    "resp": "response",
    "ret": "return_value",
    "retval": "return_value",
    "sep": "separator",
    "src": "source",
    "str": "string",
    "tbl": "table",
    "temp": "temporary",
    "tit": "title",
    "tmp": "temporary",
    "val": "value",
    "var": "variable",
    "vars": "variables",
    "ver": "version",
}
NAME_ATTRIBUTES_BY_TYPE: dict[type[object], str] = {
    ast.FunctionDef: "name",
    ast.AsyncFunctionDef: "name",
    ast.ClassDef: "name",
    ast.arg: "arg",
    ast.ExceptHandler: "name",
    ast.alias: "asname",
    ast.MatchAs: "name",
    ast.MatchStar: "name",
}


def name_words(name: str) -> list[str]:
    return [word.lower() for word in WORD_PATTERN.findall(name)]


def short_name_hint(name: str) -> str:
    return (
        f"; if it is a field name from outside, use a descriptive name with "
        f"Field(alias='{name}')"
        if len(name) < MIN_NAME_LENGTH
        else ""
    )


def length_problems(name: str) -> list[str]:
    exempt = name in SHORT_NAME_EXCEPTIONS
    fits = MIN_NAME_LENGTH <= len(name) <= MAX_NAME_LENGTH
    problem = f"`{name}` has {len(name)} characters{short_name_hint(name)}"
    return [] if exempt or fits else [problem]


def abbreviation_problems(name: str) -> list[str]:
    return [
        f"`{word}` in `{name}`: write `{REPLACEMENTS_BY_ABBREVIATION[word]}`"
        for word in name_words(name)
        if word in REPLACEMENTS_BY_ABBREVIATION
    ]


def prefix_problems(name: str) -> list[str]:
    bare_name = name.lstrip("_").lower()
    return [
        f"`{prefix}` in `{name}`"
        for prefix in TYPE_PREFIXES
        if bare_name.startswith(prefix)
    ]


def vague_problems(name: str) -> list[str]:
    return [name] if name.strip("_").lower() in VAGUE_NAMES else []


LENGTH_CHECK = NameCheck(NAME_LENGTH, length_problems)
ABBREVIATION_CHECK = NameCheck(ABBREVIATION, abbreviation_problems)
PREFIX_CHECK = NameCheck(TYPE_PREFIX, prefix_problems)
VAGUE_CHECK = NameCheck(VAGUE_NAME, vague_problems)
NAME_CHECKS = (LENGTH_CHECK, ABBREVIATION_CHECK, PREFIX_CHECK, VAGUE_CHECK)
TEST_NAME_CHECKS = (LENGTH_CHECK, ABBREVIATION_CHECK, PREFIX_CHECK)


def defined_name(node: ast.AST) -> str:
    stored = isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store)
    attribute = "id" if stored else NAME_ATTRIBUTES_BY_TYPE.get(type(node), "")
    return str(getattr(node, attribute, "") or "")


def binding_violations(
    name: str,
    node: ast.AST,
    checks: tuple[NameCheck, ...],
) -> list[Violation]:
    return [
        report(check.rule, node, problem)
        for check in checks
        for problem in check.finder(name)
    ]


def naming_violations(source: SourceFile) -> list[Violation]:
    checks = TEST_NAME_CHECKS if source.is_test else NAME_CHECKS
    return [
        violation
        for node in ast.walk(source.tree)
        if defined_name(node)
        for violation in binding_violations(defined_name(node), node, checks)
    ]


def is_literal(value: ast.AST | None) -> bool:
    if isinstance(value, ast.UnaryOp):
        return is_literal(value.operand)
    if isinstance(value, ast.BinOp):
        return is_literal(value.left) and is_literal(value.right)
    return is_literal_tuple(value) or isinstance(value, ast.Constant)


def is_literal_tuple(value: ast.AST | None) -> bool:
    return isinstance(value, ast.Tuple) and all(
        is_literal(element) for element in value.elts
    )


def is_constant_name(name: str) -> bool:
    dunder = name.startswith("__") and name.endswith("__")
    return dunder or name.isupper()


def literal_targets(tree: ast.Module) -> list[ast.Name]:
    return [
        target
        for statement in tree.body
        if isinstance(statement, ast.Assign | ast.AnnAssign)
        and is_literal(statement.value)
        for target in assigned_targets(statement)
        if isinstance(target, ast.Name)
    ]


def constant_case_violations(source: SourceFile) -> list[Violation]:
    return [
        report(CONSTANT_CASE, target, target.id)
        for target in literal_targets(source.tree)
        if not is_constant_name(target.id)
    ]
