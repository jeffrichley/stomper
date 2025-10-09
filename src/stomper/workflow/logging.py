"""Logging configuration for workflow."""

import logging
from pathlib import Path

from rich.logging import RichHandler


def setup_workflow_logging(
    level: str = "INFO",
    log_file: Path | None = None,
) -> None:
    """Setup logging for workflow.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR)
        log_file: Optional file to write logs to
    """
    handlers: list[logging.Handler] = [
        RichHandler(
            rich_tracebacks=True,
            markup=True,
            show_time=True,
            show_path=False,
        )
    ]

    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(
            logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        )
        handlers.append(file_handler)

    logging.basicConfig(
        level=level,
        format="%(message)s",
        handlers=handlers,
    )
