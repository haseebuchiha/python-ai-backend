from pathlib import Path
from textwrap import dedent

import pytest

from lint.checker import text_violations
from lint.tests.reporting import all_reported_codes, reported_codes

REBOUND_SNIPPETS = [
    "total = compute()\ntotal = compute()\n",
    """
    def build() -> int:
        total = compute()
        total += 2
        return total
    """,
    """
    def pick(ready: bool) -> int:
        if ready:
            label = 1
        else:
            label = 2
        return label
    """,
    """
    def build() -> int:
        first = (count := 1)
        second = (count := 2)
        return first + second + count
    """,
    "first, total = compute()\ntotal = compute()\n",
]
SINGLE_BINDING_SNIPPETS = [
    "_ = first()\n_ = second()\n",
    """
    def first() -> int:
        total = compute()
        return total

    def second() -> int:
        total = compute()
        return total
    """,
    "total: int\ntotal = compute()\n",
    """
    doubled = [order * 2 for order in orders]
    tripled = [order * 3 for order in orders]
    """,
]
PARAMETER_CHANGE_SNIPPETS = [
    "def build(order: dict) -> None:\n    order = {}\n",
    "def build(order: Order) -> None:\n    order.total = 1\n",
    "def build(order: dict) -> None:\n    order['total'] = 1\n",
    "def build(order: Order) -> None:\n    order.lines[0] = 1\n",
    "def build(count: int) -> None:\n    count += 1\n",
    "def build(order: dict) -> None:\n    del order['total']\n",
    "async def build(*, order: Order) -> None:\n    order.total = 1\n",
    "def build(**options: int) -> None:\n    options['retries'] = 1\n",
    "def build(lines: list[str]) -> None:\n    lines.append('x')\n",
    "def build(lines: list[str]) -> None:\n    lines.extend(['x'])\n",
    "def build(lines: list[str]) -> None:\n    lines.insert(0, 'x')\n",
    "def build(lines: list[str]) -> str:\n    return lines.pop()\n",
    "def build(lines: list[str]) -> None:\n    lines.remove('x')\n",
    "def build(lines: list[str]) -> None:\n    lines.clear()\n",
    "def build(lines: list[str]) -> None:\n    lines.sort()\n",
    "def build(prices: dict) -> None:\n    prices.update(total=1)\n",
    "def build(prices: dict) -> int:\n    return prices.setdefault('total', 1)\n",
    "def build(skus: set[str]) -> None:\n    skus.add('x')\n",
    "def build(skus: set[str]) -> None:\n    skus.discard('x')\n",
    "def build(order: Order) -> None:\n    order.lines.append(1)\n",
    "def build(orders: list) -> None:\n    orders[0].lines.clear()\n",
    "def build(order: Order, name: str) -> None:\n    setattr(order, name, 1)\n",
    "def build(order: Order, name: str) -> None:\n    delattr(order, name)\n",
    "def build(order: Order) -> None:\n    object.__setattr__(order, 'total', 1)\n",
    "def build(prices: dict) -> None:\n    prices.__setitem__('total', 1)\n",
    "def build(lines: list) -> list:\n    return [lines.append(x) for x in 'ab']\n",
    "def build(lines: list) -> None:\n    list.append(lines, 'x')\n",
    "def build(prices: dict) -> None:\n    dict.update(prices, total=1)\n",
    "def build(skus: set) -> None:\n    set.add(skus, 'x')\n",
    "def build(prices: dict) -> None:\n    dict.__setitem__(prices, 'total', 1)\n",
    "def build(lines: deque) -> None:\n    deque.appendleft(lines, 'x')\n",
    "def build(lines: deque) -> None:\n    collections.deque.appendleft(lines, 1)\n",
    "def build(counts: Counter) -> None:\n    Counter.update(counts, 'x')\n",
    "def build(order: Order) -> None:\n    object.__delattr__(order, 'total')\n",
    """
    import operator

    def build(prices: dict) -> None:
        operator.setitem(prices, 'total', 1)
    """,
    """
    import operator

    def build(prices: dict) -> None:
        operator.delitem(prices, 'total')
    """,
    """
    from operator import setitem as put

    def build(prices: dict) -> None:
        put(prices, 'total', 1)
    """,
    """
    from operator import iadd

    def build(lines: list) -> list:
        return iadd(lines, ['x'])
    """,
    """
    import operator as operations

    def build(lines: list) -> list:
        return operations.__iadd__(lines, ['x'])
    """,
    """
    from operator import ior

    def build(skus: set) -> set:
        return ior(skus, {'x'})
    """,
    "def build(skus: set) -> None:\n    skus.intersection_update({'x'})\n",
    "def build(skus: set) -> None:\n    skus.difference_update({'x'})\n",
    "def build(skus: set) -> None:\n    skus.symmetric_difference_update({'x'})\n",
    "def build(lines: deque) -> None:\n    lines.appendleft('x')\n",
    "def build(lines: deque) -> None:\n    lines.extendleft(['x'])\n",
    "def build(lines: deque) -> None:\n    lines.rotate(1)\n",
    "def build(lines: deque) -> str:\n    return lines.popleft()\n",
]
PARAMETER_SAFE_SNIPPETS = [
    "def build(order: dict) -> dict:\n    return {**order, 'total': 1}\n",
    """
    def build(order: Order) -> Order:
        copied = order.model_copy()
        copied.total = 1
        return copied
    """,
    """
    def build(lines: list[str]) -> list[str]:
        copied = list(lines)
        copied.append('x')
        return copied
    """,
    "def build(lines: list[str]) -> list[str]:\n    return sorted(lines)\n",
    "def build(prices: dict) -> dict:\n    return prices.copy()\n",
    "def build(order: Order) -> int:\n    return getattr(order, 'total')\n",
    """
    def build(monkeypatch: MonkeyPatch) -> None:
        monkeypatch.setattr(sys, 'argv', [])
    """,
    """
    def build(defaults: dict) -> dict:
        merged = {}
        merged.update(defaults)
        return merged
    """,
    """
    def build(lines: list) -> list:
        copied = list(lines)
        list.append(copied, 'x')
        return copied
    """,
    "def build(lines: list) -> int:\n    return list.count(lines, 'x')\n",
    """
    def setitem(table: dict, key: str) -> None:
        print(table, key)

    def build(prices: dict) -> None:
        setitem(prices, 'total')
    """,
    """
    import operator

    def build(prices: dict) -> int:
        return operator.getitem(prices, 'total')
    """,
    """
    from operator import add

    def build(total: int) -> int:
        return add(total, 1)
    """,
]
OUTER_REBINDING_SNIPPETS = [
    """
    def outer() -> Callable[[], int]:
        count = 0

        def bump() -> int:
            nonlocal count
            count += 1
            return count

        return bump
    """,
    """
    def reset() -> None:
        global COUNTER
        COUNTER = 0
    """,
]


@pytest.mark.parametrize("snippet", REBOUND_SNIPPETS)
def test_reassignments_are_reported(snippet: str) -> None:
    assert "BOS301" in reported_codes(snippet)


@pytest.mark.parametrize("snippet", SINGLE_BINDING_SNIPPETS)
def test_single_bindings_are_allowed(snippet: str) -> None:
    assert "BOS301" not in reported_codes(snippet)


@pytest.mark.parametrize("snippet", PARAMETER_CHANGE_SNIPPETS)
def test_parameter_changes_are_reported(snippet: str) -> None:
    assert "BOS302" in reported_codes(snippet)


@pytest.mark.parametrize("snippet", PARAMETER_SAFE_SNIPPETS)
def test_new_values_from_parameters_pass(snippet: str) -> None:
    assert "BOS302" not in reported_codes(snippet)


def test_unbound_setter_is_one_violation() -> None:
    snippet = (
        "def build(order: Order) -> None:\n    object.__setattr__(order, 'x', 1)\n"
    )
    assert all_reported_codes(snippet).count("BOS302") == 1


def test_rebound_parameter_is_one_violation() -> None:
    codes = reported_codes("def build(count: int) -> int:\n    count = 2\n")
    assert "BOS302" in codes
    assert "BOS301" not in codes


def reported_messages(snippet: str, code: str) -> list[str]:
    return [
        violation.message
        for violation in text_violations(dedent(snippet), Path("app/routes/orders.py"))
        if violation.code == code
    ]


@pytest.mark.parametrize("snippet", OUTER_REBINDING_SNIPPETS)
def test_outer_rebinding_is_reported(snippet: str) -> None:
    messages = reported_messages(snippet, "BOS301")
    assert len(messages) == 1
    assert "nonlocal or global" in messages[0]


def test_nonlocal_closure_is_not_movable() -> None:
    assert not reported_messages(OUTER_REBINDING_SNIPPETS[0], "BOS601")


def test_branch_rebinding_suggests_function() -> None:
    messages = reported_messages(REBOUND_SNIPPETS[2], "BOS301")
    assert "extract a function that returns the value" in messages[0]


def test_response_change_suggests_returning() -> None:
    snippet = """
    def create(response: Response) -> int:
        response.status_code = 201
        return 1
    """
    messages = reported_messages(snippet, "BOS302")
    assert len(messages) == 1
    assert "return a response object" in messages[0]
