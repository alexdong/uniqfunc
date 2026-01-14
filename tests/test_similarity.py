from pathlib import Path

from uniqfunc.model import FuncRef, ReuseSuggestion
from uniqfunc.parser import ParseOutcome, parse_function_defs
from uniqfunc.similarity import reuse_suggestions

SIMILARITY_THRESHOLD = 0.7
TOP_K = 2


def _parse_functions(source: str, path: Path) -> list[FuncRef]:
    result = parse_function_defs(source, path)
    assert isinstance(result, ParseOutcome)
    return result.functions


def _suggestion_by_name(
    suggestions: list[ReuseSuggestion],
    name: str,
) -> ReuseSuggestion:
    for suggestion in suggestions:
        if suggestion.target.name == name:
            return suggestion
    raise AssertionError(f"Missing reuse suggestion for {name}.")


def test_similarity_returns_candidates_above_threshold() -> None:
    source = "\n".join(
        [
            "def clamp(x: int, lo: int, hi: int) -> int:",
            "    if x < lo:",
            "        return lo",
            "    if x > hi:",
            "        return hi",
            "    return x",
            "",
            "def clamp_value(value: int, minimum: int, maximum: int) -> int:",
            "    if value < minimum:",
            "        return minimum",
            "    if value > maximum:",
            "        return maximum",
            "    return value",
            "",
        ],
    )
    functions = _parse_functions(source, Path("sample.py"))
    suggestions = reuse_suggestions(functions, SIMILARITY_THRESHOLD)
    clamp_suggestion = _suggestion_by_name(suggestions, "clamp")
    candidate_names = [candidate.name for candidate in clamp_suggestion.candidates]
    assert "clamp_value" in candidate_names
    assert all(
        candidate.score >= SIMILARITY_THRESHOLD
        for candidate in clamp_suggestion.candidates
    )


def test_similarity_respects_threshold() -> None:
    source = "\n".join(
        [
            "def add(a: int, b: int) -> int:",
            "    return a + b",
            "",
            "def read_file(path: str) -> str:",
            "    return path.strip()",
            "",
        ],
    )
    functions = _parse_functions(source, Path("dissimilar.py"))
    suggestions = reuse_suggestions(functions, 0.9)
    assert suggestions == []


def test_similarity_limits_top_k_and_sorts() -> None:
    sources = [
        ("def alpha(x: int) -> int:\n    return x + 1\n", Path("a.py")),
        ("def alpha_one(x: int) -> int:\n    return x + 1\n", Path("b.py")),
        ("def alpha_two(x: int) -> int:\n    return x + 1\n", Path("c.py")),
        ("def alpha_three(x: int) -> int:\n    return x + 1\n", Path("d.py")),
    ]
    functions: list[FuncRef] = []
    for source, path in sources:
        functions.extend(_parse_functions(source, path))
    suggestions = reuse_suggestions(functions, 0.2, top_k=TOP_K)
    alpha_suggestion = _suggestion_by_name(suggestions, "alpha")
    assert len(alpha_suggestion.candidates) == TOP_K
    keys = [
        (
            -candidate.score,
            candidate.path.as_posix(),
            candidate.line,
            candidate.name,
        )
        for candidate in alpha_suggestion.candidates
    ]
    assert keys == sorted(keys)
