from select_proxy.vultr_apollo import vps_process
from select_proxy.settings import PROXY
from select_proxy.vultr_apollo import ip_process
from select_proxy.settings import client
from select_proxy.settings_tokens import VULTR_API_TOKEN
from select_proxy.utils.VPSClient import VultrClient
from select_proxy.vultr_apollo import logger
from select_proxy import formatter

import logging
import time


def main():
    fh = logging.FileHandler('vultr_jiang_log.out')
    fh.setLevel(logging.INFO)
    fh.setFormatter(formatter)
    logger.addHandler(fh)
    jiang = VultrClient('jiang', VULTR_API_TOKEN['jiang'], PROXY)
    coll_jiang = client['vps_management']['apollo_jiang']
    # vps_process(coll_jiang, jiang, 'apollo_vultr_jiang')
    ip_process(coll_jiang, jiang, 'apollo_vultr_jiang')
    logger.info('================await================')
    time.sleep(60*40)


if __name__ == '__main__':
    main()
