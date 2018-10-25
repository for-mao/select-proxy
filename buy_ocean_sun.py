from select_proxy.ocean_apollo import vps_process
from select_proxy.settings import client
from select_proxy.settings_tokens import DIGITALOCEAN_API_TOKEN
from select_proxy.utils.VPSClient import DigitalOceanClient
from select_proxy.ocean_apollo import logger
from select_proxy import formatter
import logging
import time

fs = logging.FileHandler('ocean_sun_log.out')
fs.setLevel(logging.INFO)
fs.setFormatter(formatter)
logger.addHandler(fs)


def main():
    sun = DigitalOceanClient('sun', DIGITALOCEAN_API_TOKEN['sun'])
    coll_sun = client['vps_management']['apollo_ocean_sun']
    vps_process(coll_sun, sun, 'apollo_ocean_sun')
    logger.info('================await================')
    time.sleep(60*30)


if __name__ == '__main__':
    main()
