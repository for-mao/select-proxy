from select_proxy.vultr_apollo import vps_process
from select_proxy.settings import PROXY
from select_proxy.vultr_apollo import ip_process
from select_proxy.vultr_apollo import logger
from select_proxy.settings import client
from select_proxy.settings_tokens import VULTR_API_TOKEN
from select_proxy.utils.VPSClient import VultrClient
from select_proxy import formatter

import logging
import time


def main():
    fh = logging.FileHandler('vultr_sun_log.out')
    fh.setFormatter(formatter)
    fh.setLevel(logging.INFO)
    logger.addHandler(fh)
    sun = VultrClient('sun', VULTR_API_TOKEN['sun'], PROXY)
    coll_sun = client['vps_management']['apollo']
    # vps_process(coll_sun, sun, 'apollo_vultr_sun')
    ip_process(coll_sun, sun, 'apollo_vultr_sun')
    logger.info('================await================')
    time.sleep(60*40)


if __name__ == '__main__':
    main()
