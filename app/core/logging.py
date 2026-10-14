import logging

from app.core.constants import LOG_FORMAT


def configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format=LOG_FORMAT,
    )
