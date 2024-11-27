"""Easy universal log configuration """

import logging.config
from logging import Logger

from solver_rewards.config import IOConfig
from solver_rewards.utils.print_store import PrintStore

io_config = IOConfig.from_env()


def set_log(name: str) -> Logger:
    """Removes redundancy when setting log in each file"""

    log = logging.getLogger(name)

    logging.config.fileConfig(
        fname=io_config.log_config_file.absolute(),
        disable_existing_loggers=False,
    )
    return log


log_saver = PrintStore()
