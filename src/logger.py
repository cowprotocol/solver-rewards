"""Easy universal log configuration """

import logging.config
from logging import Logger

from src.constants import LOG_CONFIG_FILE


# TODO - use this in every file that logs (and prints).
def set_log(name: str) -> Logger:
    """Removes redundancy when setting log in each file"""

    log = logging.getLogger(name)

    logging.config.fileConfig(
        fname=LOG_CONFIG_FILE.absolute(), disable_existing_loggers=False
    )
    return log
