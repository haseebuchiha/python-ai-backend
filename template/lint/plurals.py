import ast

import inflection

from lint.core import report
from lint.schemas import Binding, Rule, SourceFile, Violation
from lint.syntax import (
    Function,
    assigned_targets,
    dotted_tail,
    functions,
    is_ellipsis,
    scope_nodes,
    unsubscripted,
)

type Aliases = dict[str, str]

SEQUENCE = "sequence"
MAPPING = "mapping"
FIXED = "fixed"
TUPLE_TYPE_NAMES = frozenset({"tuple", "Tuple"})
WRAPPER_TYPE_NAMES = frozenset(
    {
        "Optional",
        "Union",
        "Annotated",
        "Final",
        "ClassVar",
        "Required",
        "NotRequired",
        "ReadOnly",
    },
)
SEQUENCE_TYPE_NAMES = (
    "list",
    "tuple",
    "set",
    "frozenset",
    "Sequence",
    "Iterable",
    "Iterator",
    "Generator",
    "AsyncIterable",
    "AsyncIterator",
    "AsyncGenerator",
    "List",
    "Tuple",
    "Set",
    "FrozenSet",
)
MAPPING_TYPE_NAMES = (
    "dict",
    "Dict",
    "Mapping",
    "MutableMapping",
    "defaultdict",
    "OrderedDict",
    "Counter",
)
KINDS_BY_TYPE_NAME = {
    **dict.fromkeys(SEQUENCE_TYPE_NAMES, SEQUENCE),
    **dict.fromkeys(MAPPING_TYPE_NAMES, MAPPING),
}
KINDS_BY_NODE_TYPE: dict[type[object], str] = {
    ast.List: SEQUENCE,
    ast.Tuple: SEQUENCE,
    ast.Set: SEQUENCE,
    ast.ListComp: SEQUENCE,
    ast.SetComp: SEQUENCE,
    ast.GeneratorExp: SEQUENCE,
    ast.Dict: MAPPING,
    ast.DictComp: MAPPING,
}
EXTRA_PLURALS = frozenset({"feet", "teeth", "geese"})
UNCOUNTABLE_WORDS = frozenset(
    {
        "advice",
        "baggage",
        "content",
        "equipment",
        "evidence",
        "feedback",
        "furniture",
        "history",
        "information",
        "inventory",
        "knowledge",
        "luggage",
        "merchandise",
        "metadata",
        "news",
        "progress",
        "research",
        "software",
        "staff",
        "stock",
        "traffic",
    },
)
PLURAL_SEQUENCE = Rule(
    "BOS801",
    "`{}` holds a sequence, so its last word must be plural "
    "(orders, statuses, prices).",
)
PLURAL_MAPPING = Rule(
    "BOS802",
    "`{}` holds a mapping, so name it with a plural word: prices, or prices_by_sku.",
)
RULES_BY_KIND = {SEQUENCE: PLURAL_SEQUENCE, MAPPING: PLURAL_MAPPING}


def is_plural(word: str) -> bool:
    singular = inflection.singularize(word)
    listed = word in EXTRA_PLURALS or word in UNCOUNTABLE_WORDS
    uncountable = listed or word in inflection.UNCOUNTABLES
    return uncountable or (singular != word and inflection.pluralize(singular) == word)


def naming_subject(binding: Binding) -> str:
    lowered = binding.name.strip("_").lower()
    subject = lowered.split("_by_")[0] if binding.kind == MAPPING else lowered
    return subject.rsplit("_", 1)[-1]


def is_plural_binding(binding: Binding) -> bool:
    return binding.kind not in RULES_BY_KIND or is_plural(naming_subject(binding))


def import_aliases(tree: ast.Module) -> Aliases:
    return {
        alias.asname: alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
        for alias in node.names
        if alias.asname
    }


def parsed_text(text: str) -> ast.expr:
    try:
        return ast.parse(text, mode="eval").body
    except SyntaxError:
        return ast.Constant(None)


def parsed_annotation(annotation: ast.expr) -> ast.expr:
    if isinstance(annotation, ast.Constant) and isinstance(annotation.value, str):
        return parsed_text(annotation.value)
    return annotation


def type_name(annotation: ast.expr, aliases: Aliases) -> str:
    name = dotted_tail(unsubscripted(annotation))
    return aliases.get(name, name)


def type_members(annotation: ast.expr) -> list[ast.expr]:
    if isinstance(annotation, ast.BinOp):
        return [annotation.left, annotation.right]
    inner = annotation.slice if isinstance(annotation, ast.Subscript) else annotation
    return inner.elts if isinstance(inner, ast.Tuple) else [inner]


def is_wrapper(annotation: ast.expr, aliases: Aliases) -> bool:
    union = isinstance(annotation, ast.BinOp) and isinstance(annotation.op, ast.BitOr)
    wrapped = isinstance(annotation, ast.Subscript) and (
        type_name(annotation, aliases) in WRAPPER_TYPE_NAMES
    )
    return union or wrapped


def is_fixed_tuple(annotation: ast.expr, aliases: Aliases) -> bool:
    subscripted = isinstance(annotation, ast.Subscript)
    tuple_type = type_name(annotation, aliases) in TUPLE_TYPE_NAMES
    open_ended = any(is_ellipsis(member) for member in type_members(annotation)[-1:])
    return subscripted and tuple_type and not open_ended


def member_kind(annotation: ast.expr, aliases: Aliases) -> str:
    kinds = [annotation_kind(member, aliases) for member in type_members(annotation)]
    return next((kind for kind in kinds if kind), "")


def plain_kind(annotation: ast.expr, aliases: Aliases) -> str:
    if is_fixed_tuple(annotation, aliases):
        return FIXED
    return KINDS_BY_TYPE_NAME.get(type_name(annotation, aliases), "")


def annotation_kind(annotation: ast.expr | None, aliases: Aliases) -> str:
    if annotation is None:
        return ""
    expression = parsed_annotation(annotation)
    if is_wrapper(expression, aliases):
        return member_kind(expression, aliases)
    return plain_kind(expression, aliases)


def value_kind(value: ast.AST | None) -> str:
    return KINDS_BY_NODE_TYPE.get(type(value), "")


def is_single_yield(function: Function) -> bool:
    yields = [
        node
        for node in scope_nodes(function)
        if isinstance(node, ast.Yield | ast.YieldFrom)
    ]
    return len(yields) == 1 and isinstance(yields[0], ast.Yield)


def function_bindings(tree: ast.Module, aliases: Aliases) -> list[Binding]:
    return [
        Binding(node.name, node, annotation_kind(node.returns, aliases))
        for node in functions(tree)
        if not is_single_yield(node)
    ]


def assignment_bindings(tree: ast.Module) -> list[Binding]:
    return [
        Binding(target.id, target, value_kind(node.value))
        for node in ast.walk(tree)
        if isinstance(node, ast.Assign | ast.NamedExpr)
        for target in assigned_targets(node)
        if isinstance(target, ast.Name)
    ]


def annotated_bindings(tree: ast.Module, aliases: Aliases) -> list[Binding]:
    return [
        Binding(
            node.target.id,
            node.target,
            annotation_kind(node.annotation, aliases) or value_kind(node.value),
        )
        for node in ast.walk(tree)
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name)
    ]


def parameter_bindings(tree: ast.Module, aliases: Aliases) -> list[Binding]:
    return [
        Binding(node.arg, node, annotation_kind(node.annotation, aliases))
        for node in ast.walk(tree)
        if isinstance(node, ast.arg)
    ]


def plural_violations(source: SourceFile) -> list[Violation]:
    tree = source.tree
    aliases = import_aliases(tree)
    bindings = [
        *function_bindings(tree, aliases),
        *assignment_bindings(tree),
        *annotated_bindings(tree, aliases),
        *parameter_bindings(tree, aliases),
    ]
    return [
        report(RULES_BY_KIND[binding.kind], binding.node, binding.name)
        for binding in bindings
        if not is_plural_binding(binding)
    ]
