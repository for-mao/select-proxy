from select_proxy.settings import client
from select_proxy.settings_tokens import DIGITALOCEAN_API_TOKEN
from select_proxy.utils.VPSClient import DigitalOceanClient
from testinfra import get_host

# coll = client['vps_management']['apollo_ocean_sun_new_email']
coll = client['vps_management']['azure_vps']
vps_client = DigitalOceanClient('sun', DIGITALOCEAN_API_TOKEN['sun'])
host = get_host('local://')
local_ip = ''
sleep_second = 30
limit = 50
