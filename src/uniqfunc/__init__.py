"""uniqfunc package metadata and quick version check.

Usage:
    uv run --env-file .env -m uniqfunc.__init__ -h
"""

import argparse
import logging
import sys
from collections.abc import Sequence

__all__ = ["__version__"]

__version__ = "0.1.2"


def build_arg_parser() -> argparse.ArgumentParser:
    """Build the argument parser for module diagnostics."""
    parser = argparse.ArgumentParser(description="Show uniqfunc package metadata.")
    parser.add_argument(
        "--version",
        action="store_true",
        help="Print the uniqfunc package version.",
    )
    return parser


def main(argv: Sequence[str]) -> int:
    """Run the module entry point.

    Examples:
        $ uv run --env-file .env -m uniqfunc.__init__ --version
    """
    parser = build_arg_parser()
    parser.parse_args(argv)
    print(__version__)
    return 0


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    raise SystemExit(main(sys.argv[1:]))
