"""Logging configuration for the probe station package."""

import logging
import os
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path

_logging_configured = False
_logged_dirs: set[Path] = set()

_LOG_NAMESPACES = ("probe_station", "pymeasure", "pyvisa")


def add_file_log_dir(log_dir: str | Path) -> None:
    """Attach a rotating file handler writing to *log_dir* to each tracked logger.

    Handlers are attached directly to the ``probe_station``, ``pymeasure``, and
    ``pyvisa`` named loggers rather than root, so they survive any root-logger
    reconfiguration done by pymeasure when queuing an experiment.

    Idempotent: calling with a directory that already has a handler is a no-op.
    The directory is created if it does not exist.

    :param log_dir: Directory for the log file.
    """
    log_dir = Path(log_dir).resolve()
    if log_dir in _logged_dirs:
        return
    _logged_dirs.add(log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_filename = f"probe_station_{timestamp}_{os.getpid()}.log"
    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    file_handler = RotatingFileHandler(log_dir / log_filename, maxBytes=5_000_000, backupCount=5, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    for name in _LOG_NAMESPACES:
        logging.getLogger(name).addHandler(file_handler)


def setup_file_logging(log_dir: str | Path = "logs") -> None:
    """Configure the root logger with a rotating file handler and a console handler.

    Call this once at application startup before any other logging occurs.
    Subsequent calls are no-ops.

    :param log_dir: Directory for the log file. Created if it does not exist.
                    Defaults to ``logs/`` in the current working directory.
    """
    global _logging_configured
    if _logging_configured:
        return

    root = logging.getLogger()
    root.setLevel(logging.INFO)

    logging.getLogger("probe_station").setLevel(logging.DEBUG)
    logging.getLogger("pymeasure").setLevel(logging.DEBUG)
    logging.getLogger("pyvisa").setLevel(logging.DEBUG)

    add_file_log_dir(log_dir)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
    root.addHandler(console_handler)
    _logging_configured = True
