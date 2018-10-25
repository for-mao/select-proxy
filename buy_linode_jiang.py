from select_proxy.linode_apollo import vps_process
from select_proxy.settings import client
from select_proxy.settings_tokens import LINODE_API_TOKEN
from select_proxy.utils.VPSClient import LinodeClient
from select_proxy.linode_apollo import logger
from select_proxy import formatter
import logging
import time

fs = logging.FileHandler('linode_jiang_log.out')
fs.setFormatter(formatter)
fs.setLevel(logging.INFO)
logger.addHandler(fs)


def main():
    jiang = LinodeClient('jiang', LINODE_API_TOKEN['jiang'])
    coll_jiang = client['vps_management']['apollo_linode_jiang']
    vps_process(coll_jiang, jiang, 'apollo_linode_jiang')
    logger.info('================await================')
    time.sleep(60 * 20)


if __name__ == '__main__':
    main()
