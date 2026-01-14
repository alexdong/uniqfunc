"""AST fingerprint similarity helpers.

Usage:
    uv run --env-file .env -m uniqfunc.similarity_ast -h
"""

import argparse
import logging
import pprint
import sys
from collections import Counter
from collections.abc import Iterable, Sequence

from uniqfunc.fingerprint import shingle_tokens

logger = logging.getLogger(__name__)


def _jaccard(left: Iterable[object], right: Iterable[object]) -> float:
    left_set = set(left)
    right_set = set(right)
    if not left_set and not right_set:
        return 1.0
    union = left_set | right_set
    if not union:
        return 0.0
    return len(left_set & right_set) / len(union)


def multiset_jaccard(left: Sequence[str], right: Sequence[str]) -> float:
    left_counts = Counter(left)
    right_counts = Counter(right)
    if not left_counts and not right_counts:
        return 1.0
    intersection = left_counts & right_counts
    union = left_counts | right_counts
    intersection_size = sum(intersection.values())
    union_size = sum(union.values())
    if union_size == 0:
        return 0.0
    return intersection_size / union_size


def ast_similarity(
    left_tokens: Sequence[str],
    right_tokens: Sequence[str],
    shingle_size: int = 5,
) -> float:
    """Compute AST similarity using shingles with a multiset fallback.

    Examples:
        >>> ast_similarity(["A", "B", "C", "D", "E"], ["A", "B", "C", "D", "E"], shingle_size=5)
        1.0
        >>> round(ast_similarity(["A", "B"], ["A", "C"], shingle_size=5), 2)
        0.33
    """
    assert shingle_size > 0, "shingle_size must be positive."
    if len(left_tokens) < shingle_size or len(right_tokens) < shingle_size:
        return multiset_jaccard(left_tokens, right_tokens)
    shingles_left = shingle_tokens(left_tokens, size=shingle_size)
    shingles_right = shingle_tokens(right_tokens, size=shingle_size)
    return _jaccard(shingles_left, shingles_right)


def build_arg_parser() -> argparse.ArgumentParser:
    """Build the argument parser for module diagnostics."""
    parser = argparse.ArgumentParser(description="Score AST fingerprint similarity.")
    parser.add_argument("left", help="Left token stream, comma-separated.")
    parser.add_argument("right", help="Right token stream, comma-separated.")
    return parser


def _parse_tokens(raw: str) -> list[str]:
    return [token for token in raw.split(",") if token]


def main(argv: Sequence[str]) -> int:
    """Run the module entry point.

    Examples:
        $ uv run --env-file .env -m uniqfunc.similarity_ast "A,B,C" "A,B,D"
    """
    parser = build_arg_parser()
    args = parser.parse_args(argv)
    left = _parse_tokens(args.left)
    right = _parse_tokens(args.right)
    pprint.pprint(ast_similarity(left, right))
    return 0


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    raise SystemExit(main(sys.argv[1:]))
