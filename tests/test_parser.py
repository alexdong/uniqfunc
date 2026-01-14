from pathlib import Path

from uniqfunc.parser import ParseFailure, ParseOutcome, parse_function_defs

METHOD_LINE = 2
METHOD_COL = 5
INNER_LINE = 4
INNER_COL = 9
TOP_LINE = 8
TOP_COL = 1


def test_parse_function_defs_extracts_nested_and_methods() -> None:
    source = "\n".join(
        [
            "class Demo:",
            "    def method(self, value: int) -> str:",
            '        """Doc."""',
            "        def inner(flag: bool) -> None:",
            "            return None",
            "        return str(value)",
            "",
            "def top(a, b=1, *args, **kwargs) -> int:",
            "    return a",
            "",
            "async def coro(x: int) -> int:",
            "    return x",
            "",
        ],
    )
    result = parse_function_defs(source, Path("sample.py"))
    assert isinstance(result, ParseOutcome)
    names = [func.name for func in result.functions]
    assert names == ["method", "inner", "top", "coro"]

    method = result.functions[0]
    assert method.params == ["self", "value"]
    assert method.returns == "str"
    assert method.doc == "Doc."
    assert method.line == METHOD_LINE
    assert method.col == METHOD_COL
    assert method.path == Path("sample.py")

    inner = result.functions[1]
    assert inner.params == ["flag"]
    assert inner.returns == "None"
    assert inner.doc is None
    assert inner.line == INNER_LINE
    assert inner.col == INNER_COL

    top = result.functions[2]
    assert top.params == ["a", "b", "*args", "**kwargs"]
    assert top.returns == "int"
    assert top.line == TOP_LINE
    assert top.col == TOP_COL


def test_parse_function_defs_reports_syntax_errors() -> None:
    source = "def broken(:\n    return 1\n"
    result = parse_function_defs(source, Path("bad.py"))
    assert isinstance(result, ParseFailure)
    assert result.error.code == "UQF001"
    assert result.error.path == Path("bad.py")
    assert result.error.line == 1
    assert result.error.col >= 1
