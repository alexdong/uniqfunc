"""AST parser for Python function definitions.

Usage:
    uv run --env-file .env -m uniqfunc.parser -h
"""

import argparse
import ast
import logging
import pprint
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from uniqfunc.fingerprint import fingerprint_function
from uniqfunc.model import FuncRef, ScanError

logger = logging.getLogger(__name__)

PARSE_ERROR_CODE = "UQF001"


@dataclass(frozen=True, slots=True)
class ParseOutcome:
    functions: list[FuncRef]


@dataclass(frozen=True, slots=True)
class ParseFailure:
    error: ScanError


ParseResult = ParseOutcome | ParseFailure


def _extract_params(args: ast.arguments) -> list[str]:
    params: list[str] = []
    params.extend(arg.arg for arg in args.posonlyargs)
    params.extend(arg.arg for arg in args.args)
    if args.vararg:
        params.append(f"*{args.vararg.arg}")
    params.extend(arg.arg for arg in args.kwonlyargs)
    if args.kwarg:
        params.append(f"**{args.kwarg.arg}")
    return params


def _format_returns(returns: ast.expr | None) -> str | None:
    if returns is None:
        return None
    return ast.unparse(returns)


def _build_func_ref(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
    path: Path,
) -> FuncRef:
    line = node.lineno
    col = node.col_offset + 1
    params = _extract_params(node.args)
    returns = _format_returns(node.returns)
    doc = ast.get_docstring(node)
    return FuncRef(
        path=path,
        line=line,
        col=col,
        name=node.name,
        params=params,
        returns=returns,
        doc=doc,
        ast_fingerprint=fingerprint_function(node),
    )


class _FunctionCollector(ast.NodeVisitor):
    def __init__(self, path: Path) -> None:
        self._path = path
        self.functions: list[FuncRef] = []

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self.functions.append(_build_func_ref(node, self._path))
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self.functions.append(_build_func_ref(node, self._path))
        self.generic_visit(node)


def parse_function_defs(source: str, path: Path) -> ParseResult:
    """Parse function defs from a Python source string.

    Examples:
        >>> outcome = parse_function_defs("def demo():\\n    return 1\\n", Path("a.py"))
        >>> isinstance(outcome, ParseOutcome)
        True
        >>> outcome.functions[0].name
        'demo'
    """
    assert path, "parse_function_defs expects a path for diagnostics."
    try:
        tree = ast.parse(source, filename=path.as_posix())
    except SyntaxError as exc:
        line = exc.lineno or 1
        col = exc.offset or 1
        message = exc.msg or "syntax error"
        return ParseFailure(
            error=ScanError(
                code=PARSE_ERROR_CODE,
                path=path,
                line=line,
                col=col,
                message=f"syntax error: {message}",
            ),
        )
    collector = _FunctionCollector(path)
    collector.visit(tree)
    logger.debug("Parsed %s functions from %s", len(collector.functions), path)
    return ParseOutcome(functions=collector.functions)


def build_arg_parser() -> argparse.ArgumentParser:
    """Build the argument parser for module diagnostics."""
    parser = argparse.ArgumentParser(description="Parse Python source for functions.")
    parser.add_argument("path", help="Python source file to parse.")
    return parser


def main(argv: Sequence[str]) -> int:
    """Run the module entry point.

    Examples:
        $ uv run --env-file .env -m uniqfunc.parser path/to/file.py
    """
    parser = build_arg_parser()
    args = parser.parse_args(argv)
    path = Path(args.path)
    source = path.read_text(encoding="utf-8")
    result = parse_function_defs(source, path)
    if isinstance(result, ParseFailure):
        pprint.pprint(result.error)
        return 1
    pprint.pprint(result.functions)
    return 0


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    raise SystemExit(main(sys.argv[1:]))
