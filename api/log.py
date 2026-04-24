import logging

# ── Edit these to change all logging behaviour ──────────────────────────────
LOG_LEVEL  = logging.INFO
LOG_FORMAT = "%(asctime)s [%(levelname)-8s] %(name)s: %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
# ────────────────────────────────────────────────────────────────────────────


def configure_logging() -> None:
    logging.basicConfig(level=LOG_LEVEL, format=LOG_FORMAT, datefmt=DATE_FORMAT)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
