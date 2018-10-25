from typing import Callable

from select_proxy import create_logger
from select_proxy import formatter
import logging

logger = create_logger(__name__)
fh = logging.FileHandler('error_log')
fh.setLevel(logging.WARN)
fh.setFormatter(formatter)
logger.addHandler(fh)


def ignore_all_error(func: Callable):

    def wrapper(*args, **kwargs):
        while True:
            try:
                func(*args, **kwargs)
            except Exception as exc:
                logger.error('{func_name} error: {error}'.format(
                    func_name=func.__name__, error=exc
                ))

    return wrapper
