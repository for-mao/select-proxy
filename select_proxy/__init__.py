import sys
from os import path
import logging
from logging import Logger

pkg_path = path.abspath(path.join(__file__, path.pardir))

sys.path.insert(0, pkg_path)


formatter = logging.Formatter(
    '%(asctime)s [%(name)s] %(levelname)s: %(message)s', '%Y-%m-%d %H:%M:%S'
)


def create_logger(name: str) -> Logger:
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    console = logging.StreamHandler()
    console.setLevel(logging.DEBUG)
    console.setFormatter(formatter)

    logger.addHandler(console)
    # fs = logging.FileHandler('./log.out'.format(name))
    # fs.setLevel(logging.INFO)
    return logger


if __name__ == '__main__':
    # print(path.exists(docs_path))
    pass
