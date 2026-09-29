import logging
from pathlib import Path

from PySide6.QtCore import QObject, Signal


class QtLogHandler(logging.Handler, QObject):
    """
    Sends Python logging messages to the Qt UI.
    """

    message = Signal(str)

    def __init__(self):
        QObject.__init__(self)
        logging.Handler.__init__(self)

    def emit(self, record):
        try:
            message = self.format(record)
            self.message.emit(message)
        except Exception:
            pass


def setup_logger(log_directory: Path):
    """
    Configure application logging.
    """

    log_directory.mkdir(
        parents=True,
        exist_ok=True
    )

    log_file = log_directory / "application.log"

    logger = logging.getLogger(
        "gravitydownload"
    )

    logger.setLevel(
        logging.DEBUG
    )

    logger.propagate = False

    if logger.handlers:
        return logger

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(message)s",
        datefmt="%H:%M:%S"
    )

    file_handler = logging.FileHandler(
        log_file,
        encoding="utf-8"
    )

    file_handler.setLevel(
        logging.DEBUG
    )

    file_handler.setFormatter(
        formatter
    )

    console_handler = logging.StreamHandler()

    console_handler.setLevel(
        logging.INFO
    )

    console_handler.setFormatter(
        formatter
    )

    logger.addHandler(
        file_handler
    )

    logger.addHandler(
        console_handler
    )

    return logger


def create_qt_log_handler():
    """
    Create a Qt handler for live UI logging.
    """

    handler = QtLogHandler()

    handler.setFormatter(
        logging.Formatter(
            "%(asctime)s | %(levelname)s | %(message)s",
            datefmt="%H:%M:%S"
        )
    )

    logging.getLogger(
        "gravitydownload"
    ).addHandler(
        handler
    )

    return handler


def get_logger():
    return logging.getLogger(
        "gravitydownload"
    )