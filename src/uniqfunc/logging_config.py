"""Logging configuration for uniqfunc runs.

Usage:
    uv run --env-file .env -m uniqfunc.logging_config -h
"""

import argparse
import logging
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class LogConfig:
    path: Path


def configure_logging(run_dir: Path) -> LogConfig:
    assert run_dir, "configure_logging requires a run directory path."
    run_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S-%f")
    log_path = run_dir / f"uniqfunc-{timestamp}.log"
    formatter = logging.Formatter(
        "%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    handler = logging.FileHandler(log_path, encoding="utf-8")
    handler.setFormatter(formatter)
    root = logging.getLogger()
    root.setLevel(logging.DEBUG)
    root.addHandler(handler)
    logger.debug("Configured logging at %s", log_path)
    return LogConfig(path=log_path)


def build_arg_parser() -> argparse.ArgumentParser:
    """Build the argument parser for module diagnostics."""
    parser = argparse.ArgumentParser(description="Configure uniqfunc logging.")
    parser.add_argument(
        "--run-dir",
        default="run",
        help="Directory where log files are written.",
    )
    return parser


def main(argv: Sequence[str]) -> int:
    """Run the module entry point.

    Examples:
        $ uv run --env-file .env -m uniqfunc.logging_config --run-dir run
    """
    parser = build_arg_parser()
    args = parser.parse_args(argv)
    config = configure_logging(Path(args.run_dir))
    print(config.path)
    return 0


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    raise SystemExit(main(sys.argv[1:]))
