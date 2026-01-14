import ast

from uniqfunc.fingerprint import fingerprint_function, shingle_tokens

SHINGLE_SIZE = 5


def test_fingerprint_normalizes_identifiers_and_constants() -> None:
    source = "\n".join(
        [
            "def demo(x):",
            "    value = 12",
            "    name = 'hi'",
            "    flag = True",
            "    nothing = None",
            "    return x",
            "",
        ],
    )
    node = ast.parse(source).body[0]
    assert isinstance(node, ast.FunctionDef)
    tokens = fingerprint_function(node)
    assert "NUM" in tokens
    assert "STR" in tokens
    assert "BOOL" in tokens
    assert "NONE" in tokens
    assert "value" not in tokens
    assert "name" not in tokens
    assert "flag" not in tokens
    assert "nothing" not in tokens


def test_fingerprint_retains_call_target_names() -> None:
    source = "\n".join(
        [
            "def demo(x):",
            "    helper(x)",
            "    obj.method(x)",
            "",
        ],
    )
    node = ast.parse(source).body[0]
    assert isinstance(node, ast.FunctionDef)
    tokens = fingerprint_function(node)
    assert "CALL" in tokens
    assert "helper" in tokens
    assert "method" in tokens


def test_shingle_tokens_returns_expected_ngrams() -> None:
    tokens = ["A", "B", "C", "D", "E", "F"]
    shingles = shingle_tokens(tokens, size=SHINGLE_SIZE)
    assert shingles == [
        ("A", "B", "C", "D", "E"),
        ("B", "C", "D", "E", "F"),
    ]


def test_shingle_tokens_handles_short_streams() -> None:
    tokens = ["A", "B", "C"]
    shingles = shingle_tokens(tokens, size=SHINGLE_SIZE)
    assert shingles == []
