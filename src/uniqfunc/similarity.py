"""Combine similarity strategies to rank reuse candidates.

Usage:
    uv run --env-file .env -m uniqfunc.similarity -h
"""

import argparse
import logging
import pprint
import sys
from collections.abc import Iterable, Sequence
from pathlib import Path

from uniqfunc.model import FuncRef, ReuseCandidate, ReuseSuggestion
from uniqfunc.parser import ParseFailure, parse_function_defs
from uniqfunc.similarity_ast import ast_similarity
from uniqfunc.similarity_name_signature import name_signature_score

logger = logging.getLogger(__name__)

NAME_SIGNATURE_WEIGHT = 0.4
AST_WEIGHT = 0.6
DEFAULT_TOP_K = 5


def _sorted_functions(functions: Iterable[FuncRef]) -> list[FuncRef]:
    return sorted(
        functions,
        key=lambda func: (func.path.as_posix(), func.line, func.name),
    )


def _score_candidate(target: FuncRef, candidate: FuncRef) -> ReuseCandidate:
    name_score = name_signature_score(target, candidate)
    ast_score = ast_similarity(target.ast_fingerprint, candidate.ast_fingerprint)
    final_score = (NAME_SIGNATURE_WEIGHT * name_score.final_score) + (
        AST_WEIGHT * ast_score
    )
    signals = {
        "name_token_jaccard": name_score.name_token_jaccard,
        "signature_score": name_score.signature_score,
        "ast_score": ast_score,
    }
    return ReuseCandidate(
        path=candidate.path,
        line=candidate.line,
        col=candidate.col,
        name=candidate.name,
        score=final_score,
        signals=signals,
    )


def _filter_and_rank_candidates(
    target: FuncRef,
    functions: Sequence[FuncRef],
    threshold: float,
    top_k: int,
) -> list[ReuseCandidate]:
    scored: list[ReuseCandidate] = []
    for candidate in functions:
        if candidate is target:
            continue
        scored_candidate = _score_candidate(target, candidate)
        if scored_candidate.score < threshold:
            continue
        scored.append(scored_candidate)
    scored.sort(
        key=lambda item: (
            -item.score,
            item.path.as_posix(),
            item.line,
            item.name,
        ),
    )
    return scored[:top_k]


def reuse_suggestions(
    functions: Sequence[FuncRef],
    threshold: float,
    top_k: int = DEFAULT_TOP_K,
) -> list[ReuseSuggestion]:
    """Compute reuse suggestions across a set of functions.

    Examples:
        >>> left = FuncRef(Path("a.py"), 1, 1, "alpha", ["x"], "int", None, ["RETURN", "VAR"])
        >>> right = FuncRef(Path("b.py"), 1, 1, "alpha_copy", ["x"], "int", None, ["RETURN", "VAR"])
        >>> suggestions = reuse_suggestions([left, right], 0.1, top_k=1)
        >>> suggestions[0].target.name
        'alpha'
    """
    assert 0.0 <= threshold <= 1.0, "threshold must be between 0 and 1."
    assert top_k > 0, "top_k must be a positive integer."
    ordered = _sorted_functions(functions)
    suggestions: list[ReuseSuggestion] = []
    for target in ordered:
        candidates = _filter_and_rank_candidates(target, ordered, threshold, top_k)
        if not candidates:
            continue
        suggestions.append(ReuseSuggestion(target=target, candidates=candidates))
    logger.debug("Generated %s reuse suggestions", len(suggestions))
    return suggestions


def build_arg_parser() -> argparse.ArgumentParser:
    """Build the argument parser for module diagnostics."""
    parser = argparse.ArgumentParser(description="Rank reuse candidates.")
    parser.add_argument("path", help="Python file to analyze.")
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.7,
        help="Minimum similarity threshold.",
    )
    return parser


def _load_functions(path: Path) -> list[FuncRef]:
    source = path.read_text(encoding="utf-8")
    result = parse_function_defs(source, path)
    if isinstance(result, ParseFailure):
        logger.error("Failed to parse %s: %s", path, result.error.message)
        return []
    return result.functions


def main(argv: Sequence[str]) -> int:
    """Run the module entry point.

    Examples:
        $ uv run --env-file .env -m uniqfunc.similarity path/to/file.py
    """
    parser = build_arg_parser()
    args = parser.parse_args(argv)
    path = Path(args.path)
    functions = _load_functions(path)
    pprint.pprint(reuse_suggestions(functions, args.threshold))
    return 0


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    raise SystemExit(main(sys.argv[1:]))
