"""Name and signature similarity helpers for reuse suggestions.

Usage:
    uv run --env-file .env -m uniqfunc.similarity_name_signature -h
"""

import argparse
import logging
import pprint
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from difflib import SequenceMatcher
from pathlib import Path

from uniqfunc.model import FuncRef

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class NameSignatureScore:
    name_token_jaccard: float
    name_edit_similarity: float
    signature_score: float
    final_score: float


def snake_tokens(name: str) -> set[str]:
    return {token for token in name.lower().split("_") if token}


def name_token_jaccard(name_a: str, name_b: str) -> float:
    tokens_a = snake_tokens(name_a)
    tokens_b = snake_tokens(name_b)
    if not tokens_a and not tokens_b:
        return 1.0
    union = tokens_a | tokens_b
    if not union:
        return 0.0
    return len(tokens_a & tokens_b) / len(union)


def name_edit_similarity(name_a: str, name_b: str) -> float:
    if not name_a and not name_b:
        return 1.0
    return SequenceMatcher(None, name_a, name_b).ratio()


def _normalize_param(param: str) -> str:
    return param.lstrip("*").lower()


def param_name_jaccard(params_a: Sequence[str], params_b: Sequence[str]) -> float:
    names_a = {_normalize_param(name) for name in params_a}
    names_b = {_normalize_param(name) for name in params_b}
    if not names_a and not names_b:
        return 1.0
    union = names_a | names_b
    if not union:
        return 0.0
    return len(names_a & names_b) / len(union)


def param_count_similarity(count_a: int, count_b: int) -> float:
    assert count_a >= 0, "param_count_similarity expects non-negative counts."
    assert count_b >= 0, "param_count_similarity expects non-negative counts."
    if count_a == 0 and count_b == 0:
        return 1.0
    if max(count_a, count_b) == 0:
        return 0.0
    return 1.0 - (abs(count_a - count_b) / max(count_a, count_b))


def return_annotation_match(ret_a: str | None, ret_b: str | None) -> float:
    if ret_a is None and ret_b is None:
        return 1.0
    if ret_a is None or ret_b is None:
        return 0.0
    return 1.0 if ret_a == ret_b else 0.0


def signature_similarity(left: FuncRef, right: FuncRef) -> float:
    count_score = param_count_similarity(len(left.params), len(right.params))
    name_score = param_name_jaccard(left.params, right.params)
    return_score = return_annotation_match(left.returns, right.returns)
    return (count_score + name_score + return_score) / 3.0


def name_signature_score(left: FuncRef, right: FuncRef) -> NameSignatureScore:
    """Compute the combined name + signature similarity.

    Examples:
        >>> left = FuncRef(Path("a.py"), 1, 1, "epoch_to_datetime", ["epoch"], "datetime", None, [])
        >>> right = FuncRef(Path("b.py"), 1, 1, "epoch_to_aware_datetime", ["epoch_seconds"], "datetime", None, [])
        >>> score = name_signature_score(left, right)
        >>> round(score.name_token_jaccard, 2)
        0.75
    """
    token_score = name_token_jaccard(left.name, right.name)
    edit_score = name_edit_similarity(left.name, right.name)
    name_score = (token_score + edit_score) / 2.0
    signature_score = signature_similarity(left, right)
    final_score = (name_score + signature_score) / 2.0
    return NameSignatureScore(
        name_token_jaccard=token_score,
        name_edit_similarity=edit_score,
        signature_score=signature_score,
        final_score=final_score,
    )


def build_arg_parser() -> argparse.ArgumentParser:
    """Build the argument parser for module diagnostics."""
    parser = argparse.ArgumentParser(description="Score name and signature similarity.")
    parser.add_argument("left", help="Left function name.")
    parser.add_argument("right", help="Right function name.")
    return parser


def main(argv: Sequence[str]) -> int:
    """Run the module entry point.

    Examples:
        $ uv run --env-file .env -m uniqfunc.similarity_name_signature left right
    """
    parser = build_arg_parser()
    args = parser.parse_args(argv)
    left = FuncRef(Path("left.py"), 1, 1, args.left, [], None, None, [])
    right = FuncRef(Path("right.py"), 1, 1, args.right, [], None, None, [])
    pprint.pprint(name_signature_score(left, right))
    return 0


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    raise SystemExit(main(sys.argv[1:]))
