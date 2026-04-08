import sys
import logging

LOG_FORMAT = "%(asctime)s | %(levelname)-7s | %(name)-20s | %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

_handler = logging.StreamHandler(sys.stdout)
_handler.setFormatter(logging.Formatter(LOG_FORMAT, DATE_FORMAT))

_MODULE_NAMES = [
    "be_system",
    "lpr_service",
    "session_store",
    "api_recognize",
]


def setup_logging():
    """Cấu hình logging tập trung cho tất cả module."""
    for name in _MODULE_NAMES:
        logger = logging.getLogger(name)
        logger.setLevel(logging.INFO)
        if not logger.handlers:
            logger.addHandler(_handler)
        logger.propagate = False


def get_logger(name: str) -> logging.Logger:
    """Lấy logger đã cấu hình cho module."""
    logger = logging.getLogger(name)
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        logger.addHandler(_handler)
        logger.propagate = False
    return logger
