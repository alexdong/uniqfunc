"""Canonical token fingerprints for Python functions.

Usage:
    uv run --env-file .env -m uniqfunc.fingerprint -h
"""

import argparse
import ast
import logging
import pprint
import sys
from collections import Counter
from collections.abc import Iterable, Sequence
from pathlib import Path

logger = logging.getLogger(__name__)

type Token = str
type Shingle = tuple[Token, ...]

BIN_OP_TOKENS: dict[type[ast.operator], Token] = {
    ast.Add: "+",
    ast.Sub: "-",
    ast.Mult: "*",
    ast.Div: "/",
    ast.FloorDiv: "//",
    ast.Mod: "%",
    ast.Pow: "**",
    ast.MatMult: "@",
    ast.LShift: "<<",
    ast.RShift: ">>",
    ast.BitOr: "|",
    ast.BitAnd: "&",
    ast.BitXor: "^",
}

BOOL_OP_TOKENS: dict[type[ast.boolop], Token] = {
    ast.And: "AND",
    ast.Or: "OR",
}

UNARY_OP_TOKENS: dict[type[ast.unaryop], Token] = {
    ast.Not: "NOT",
    ast.UAdd: "+",
    ast.USub: "-",
    ast.Invert: "~",
}

COMPARE_OP_TOKENS: dict[type[ast.cmpop], Token] = {
    ast.Eq: "==",
    ast.NotEq: "!=",
    ast.Lt: "<",
    ast.LtE: "<=",
    ast.Gt: ">",
    ast.GtE: ">=",
    ast.Is: "IS",
    ast.IsNot: "ISNOT",
    ast.In: "IN",
    ast.NotIn: "NOTIN",
}


def bucket_constant(value: object) -> Token:
    """Bucket literal constants into stable placeholder tokens.

    Examples:
        >>> bucket_constant(42)
        'NUM'
        >>> bucket_constant("hi")
        'STR'
        >>> bucket_constant(True)
        'BOOL'
        >>> bucket_constant(None)
        'NONE'
    """
    if value is None:
        return "NONE"
    if isinstance(value, bool):
        return "BOOL"
    if isinstance(value, int | float | complex):
        return "NUM"
    if isinstance(value, str):
        return "STR"
    return "CONST"


def _call_target_name(node: ast.expr) -> Token:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return "CALLABLE"


class _TokenCollector(ast.NodeVisitor):
    def __init__(self) -> None:
        self.tokens: list[Token] = []

    def _visit_block(self, statements: Iterable[ast.stmt]) -> None:
        for statement in statements:
            self.visit(statement)

    def visit_Return(self, node: ast.Return) -> None:
        self.tokens.append("RETURN")
        if node.value is not None:
            self.visit(node.value)

    def visit_If(self, node: ast.If) -> None:
        self.tokens.append("IF")
        self.visit(node.test)
        self._visit_block(node.body)
        if node.orelse:
            self.tokens.append("ELSE")
            self._visit_block(node.orelse)

    def visit_For(self, node: ast.For) -> None:
        self.tokens.append("FOR")
        self.visit(node.target)
        self.visit(node.iter)
        self._visit_block(node.body)
        if node.orelse:
            self.tokens.append("ELSE")
            self._visit_block(node.orelse)

    def visit_While(self, node: ast.While) -> None:
        self.tokens.append("WHILE")
        self.visit(node.test)
        self._visit_block(node.body)
        if node.orelse:
            self.tokens.append("ELSE")
            self._visit_block(node.orelse)

    def visit_Assign(self, node: ast.Assign) -> None:
        self.tokens.append("ASSIGN")
        self.visit(node.value)
        for target in node.targets:
            self.visit(target)

    def visit_AugAssign(self, node: ast.AugAssign) -> None:
        self.tokens.append("ASSIGN")
        self.tokens.append(BIN_OP_TOKENS.get(type(node.op), "OP"))
        self.visit(node.target)
        self.visit(node.value)

    def visit_BinOp(self, node: ast.BinOp) -> None:
        self.visit(node.left)
        self.tokens.append(BIN_OP_TOKENS.get(type(node.op), "OP"))
        self.visit(node.right)

    def visit_BoolOp(self, node: ast.BoolOp) -> None:
        if not node.values:
            return
        self.visit(node.values[0])
        for value in node.values[1:]:
            self.tokens.append(BOOL_OP_TOKENS.get(type(node.op), "BOOL_OP"))
            self.visit(value)

    def visit_Compare(self, node: ast.Compare) -> None:
        self.visit(node.left)
        for op, comparator in zip(node.ops, node.comparators, strict=True):
            self.tokens.append(COMPARE_OP_TOKENS.get(type(op), "CMP"))
            self.visit(comparator)

    def visit_UnaryOp(self, node: ast.UnaryOp) -> None:
        self.tokens.append(UNARY_OP_TOKENS.get(type(node.op), "UNARY"))
        self.visit(node.operand)

    def visit_Call(self, node: ast.Call) -> None:
        self.tokens.append("CALL")
        self.tokens.append(_call_target_name(node.func))
        for arg in node.args:
            self.visit(arg)
        for keyword in node.keywords:
            if keyword.value is not None:
                self.visit(keyword.value)

    def visit_Attribute(self, _node: ast.Attribute) -> None:
        self.tokens.append("VAR")

    def visit_Name(self, _node: ast.Name) -> None:
        self.tokens.append("VAR")

    def visit_Constant(self, node: ast.Constant) -> None:
        self.tokens.append(bucket_constant(node.value))

    def visit_List(self, node: ast.List) -> None:
        self.tokens.append("LIST")
        self.generic_visit(node)

    def visit_Tuple(self, node: ast.Tuple) -> None:
        self.tokens.append("TUPLE")
        self.generic_visit(node)

    def visit_Set(self, node: ast.Set) -> None:
        self.tokens.append("SET")
        self.generic_visit(node)

    def visit_Dict(self, node: ast.Dict) -> None:
        self.tokens.append("DICT")
        self.generic_visit(node)


def fingerprint_function(node: ast.FunctionDef | ast.AsyncFunctionDef) -> list[Token]:
    """Return a canonical token stream for a function body.

    Examples:
        >>> node = ast.parse("def demo(x):\\n    return x + 1\\n").body[0]
        >>> fingerprint_function(node)
        ['RETURN', 'VAR', '+', 'NUM']
    """
    collector = _TokenCollector()
    for statement in node.body:
        collector.visit(statement)
    return collector.tokens


def shingle_tokens(tokens: Sequence[Token], size: int = 5) -> list[Shingle]:
    """Return contiguous n-gram shingles from a token stream.

    Examples:
        >>> shingle_tokens(["A", "B", "C", "D", "E", "F"], size=5)
        [('A', 'B', 'C', 'D', 'E'), ('B', 'C', 'D', 'E', 'F')]
    """
    assert size > 0, "shingle size must be positive."
    if len(tokens) < size:
        return []
    return [tuple(tokens[i : i + size]) for i in range(len(tokens) - size + 1)]


def token_multiset(tokens: Sequence[Token]) -> Counter[Token]:
    return Counter(tokens)


class _FunctionNodeCollector(ast.NodeVisitor):
    def __init__(self) -> None:
        self.functions: list[ast.FunctionDef | ast.AsyncFunctionDef] = []

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self.functions.append(node)
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self.functions.append(node)
        self.generic_visit(node)


def _collect_function_nodes(
    tree: ast.AST,
) -> list[ast.FunctionDef | ast.AsyncFunctionDef]:
    collector = _FunctionNodeCollector()
    collector.visit(tree)
    return collector.functions


def build_arg_parser() -> argparse.ArgumentParser:
    """Build the argument parser for module diagnostics."""
    parser = argparse.ArgumentParser(description="Fingerprint Python functions.")
    parser.add_argument("path", help="Python source file to fingerprint.")
    return parser


def main(argv: Sequence[str]) -> int:
    """Run the module entry point.

    Examples:
        $ uv run --env-file .env -m uniqfunc.fingerprint path/to/file.py
    """
    parser = build_arg_parser()
    args = parser.parse_args(argv)
    path = Path(args.path)
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=path.as_posix())
    functions = _collect_function_nodes(tree)
    fingerprints = {node.name: fingerprint_function(node) for node in functions}
    pprint.pprint(fingerprints)
    logger.debug("Fingerprinting complete for %s", path)
    return 0


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    raise SystemExit(main(sys.argv[1:]))
