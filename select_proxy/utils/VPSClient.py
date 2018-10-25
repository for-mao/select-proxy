from typing import Generator
from typing import List
from typing import Dict
from typing import Union
from functools import partial
from __init__ import create_logger

import requests
from requests.models import Response
# import grequests
import json
import random
import re

from future.moves import sys
from pymongo.collection import Collection

from utils.cache import CacheUtil

logger = create_logger(__name__)


class VPSClientBase(object):

    def list_servers(self) -> List:
        pass

    def create_vps(self, region: str, plan: str, image: str,
                   label: str, tag: str, ssh_keys: List) -> bool:
        pass

    def create_multiple_vps(self):
        pass

    def delete_vps(self, vps_id: str) -> bool:
        pass

    def delete_multiple_vps(self):
        pass

    def get_standard_msg(self, vps: Dict) -> Dict:
        """
        :param vps:
        :return: { ip:[], service provider:'',account:'', meta:{}}
        """
        pass

    def get_all_vps(self) -> Generator:
        for vps in self.list_servers():
            yield self.get_standard_msg(vps)


class VultrClient(VPSClientBase):

    def __init__(self, account: str, token: str, proxy: Dict=None):
        self.account = account
        self.__token = token
        self.header = {
            'API-Key': '{}'.format(self.__token)
        }
        self.proxy = proxy
        self.url = 'https://api.vultr.com/v1/'
        self.get = partial(requests.get, headers=self.header, timeout=60,
                           proxies=self.proxy)
        self.post = partial(requests.post, headers=self.header, timeout=60,
                            proxies=self.proxy)

    def list_servers(self) -> List:
        response = self.get('https://api.vultr.com/v1/server/list')
        return list(json.loads(response.content.decode()).values())

    def query_one(self, vps_id: str) -> Dict:
        response = self.get('https://api.vultr.com/v1/server/list')
        return json.loads(response.content.decode()).get(vps_id)

    @staticmethod
    def requests_back(response: Response, *args, **kwargs):
        if response.status_code != 200:
            logger.warning(response.content)
        else:
            response.vps = kwargs.get('vps')
        return response

    @staticmethod
    def handle_except(request, exception):
        logger.warning(exception)

    def get_all_vps_async(self):
        servers = self.list_servers()
        import grequests

        urls = (grequests.get('https://api.vultr.com/v1/server/list_ipv4',
                              params={'SUBID': i.get('SUBID')},
                              headers=self.header,
                              callback=partial(self.requests_back,
                                               vps=i)) for i in servers[0:10])
        for vps in grequests.map(urls, size=2, gtimeout=1.3,
                                 exception_handler=self.handle_except):
            yield self.get_standard_msg_async(vps)

    def get_standard_msg_async(self, response: Response) -> Dict:
        ips = []
        main_ip = ''
        logger.warning(response.content)
        vps = response.vps
        for i in json.loads(response.content.decode()).get(vps.get('SUBID')):
            if i['type'] != 'private':
                ips.append(i['ip'])
            if i['type'] == 'main_ip':
                main_ip = i['ip']
        return {
            'ipv4': ips,
            'vps_id': vps.get('SUBID'),
            'main_ipv4': main_ip,
            'region': vps.get('location'),
            'service_provider': 'Vultr',
            'account': self.account,
            'label': vps.get('label'),
            'os': vps.get('os'),
            'meta': vps
        }

    def query_ipv4(self, vps_id: str) -> Dict:
        url = self.url + 'server/list_ipv4'
        response = self.get(url, params={'SUBID': vps_id})
        if response.status_code == 200:
            return json.loads(response.content.decode()).get(vps_id)
        else:
            logger.warning(response.content.decode())

    def get_standard_msg(self, vps: Dict) -> Dict:
        logger.info('query vps_id: {}'.format(vps.get('SUBID')))
        raw_ips = self.query_ipv4(vps.get('SUBID'))
        ips = []
        main_ip = ''
        for i in raw_ips:
            if i['type'] != 'private':
                ips.append(i['ip'])
            if i['type'] == 'main_ip':
                main_ip = i['ip']
        return {
            'ipv4': ips,
            'vps_id': vps.get('SUBID'),
            'main_ipv4': main_ip,
            'region': vps.get('location'),
            'service_provider': 'Vultr',
            'account': self.account,
            'label': vps.get('label'),
            'os': vps.get('os'),
            'meta': vps
        }

    def create_vps(self, region: int, plan: int, image: int,
                   label: str, tag: str,
                   ssh_keys: str, **kwargs) -> [Dict, False]:
        """
        DCID: regions  requested
        VPSPLANID: plan requested
        OSID: os requested
        enable_ipv6: default True
        enable_private_network: default True
        SSHKEYID: you need get id -> self.list_ssh_key
        label:
        hostname:
        tag:
        """
        kwargs.update({
            'DCID': region,
            'VPSPLANID': plan,
            'OSID': image,
            'hostname': label,
            'label': label,
            'tag': tag,
            'SSHKEYID': ssh_keys
        })

        url = self.url + 'server/create'
        kwargs.setdefault('enable_ipv6', 'yes')
        kwargs.setdefault('enable_private_network', 'yes')

        response = self.post(url, data=kwargs)
        if response.status_code == 200:
            return json.loads(response.content.decode())
        else:
            logger.warning(response.content)

    def create_vps_with_snapshot(self, region: int, plan: int,
                                 label: str, tag: str, snapshot_id: str,
                                 **kwargs) -> [Dict, False]:
        """
        DCID: regions  requested
        VPSPLANID: plan requested
        OSID: os requested
        enable_ipv6: default True
        enable_private_network: default True
        SSHKEYID: you need get id -> self.list_ssh_key
        snapshot_id: str
        label:
        hostname:
        tag:
        """
        kwargs.update({
            'DCID': region,
            'VPSPLANID': plan,
            'OSID': 164,  # must be 164
            'hostname': label,
            'label': label,
            'tag': tag,
            'SNAPSHOTID': snapshot_id
        })

        url = self.url + 'server/create'
        kwargs.setdefault('enable_ipv6', 'yes')
        kwargs.setdefault('enable_private_network', 'yes')

        response = self.post(url, data=kwargs)
        if response.status_code == 200:
            return json.loads(response.content.decode())
        else:
            logger.warning(response.content)

    def create_snapshot(self, vps_id: str, desc: str) -> Dict:
        url = self.url + 'snapshot/create'
        response = self.post(url, data={'SUBID': vps_id, 'description': desc})
        if response.status_code == 200:
            return json.loads(response.content.decode())
        else:
            logger.warning(response.content.decode())

    def delete_snapshot(self, snapshot: str) -> bool:
        url = self.url + 'snapshot/destroy'
        response = self.post(url, data={'SNAPSHOTID': snapshot})
        if response.status_code == 200:
            return True
        else:
            logger.warning(response.content.decode())

    def restore_snapshot(self, vps_id: str, snapshot_id: str) -> bool:
        url = self.url + 'server/restore_snapshot'
        response = self.post(url, data={'SUBID': vps_id,
                                        'SNAPSHOTID': snapshot_id})
        if response.status_code == 200:
            return True
        else:
            logger.warning(response.content.decode())

    def list_snapshots(self):
        url = self.url + 'snapshot/list'
        response = self.get(url)
        if response.status_code == 200:
            return json.loads(response.content.decode())
        else:
            logger.warning(response.content.decode())

    def create_ssh_key(self, name: str, pub_key: str) -> Dict:
        url = self.url + 'sshkey/create'
        response = self.post(url, data={
            'name': name, 'ssh_key': pub_key
        })
        return json.loads(response.content.decode())

    def create_ipv4(self, subid: str) -> bool:
        url = self.url + 'server/create_ipv4'
        response = self.post(url, data={'SUBID': subid})
        if response.status_code == 200:
            return True
        else:
            logger.warning(response.content.decode())

    def delete_ipv4(self, vps_id: str, ip: str) -> bool:
        url = self.url + 'server/destroy_ipv4'
        response = self.post(url, data={
            "SUBID": vps_id,
            'ip': ip
        })
        if response.status_code == 200:
            return True
        else:
            logger.warning(response.content.decode())

    @CacheUtil.query_cache
    def list_plans(self, _type='all') -> Dict:
        url = self.url + 'plans/list'
        response = self.get(url, params={'type': _type})
        return json.loads(response.content.decode())

    @CacheUtil.query_cache
    def list_regions(self) -> Dict:
        url = self.url + 'regions/list'
        response = self.get(url)
        return json.loads(response.content.decode())

    @CacheUtil.query_cache
    def list_os(self) -> Dict:
        url = self.url + 'os/list'
        response = self.get(url)
        logger.warning(response.status_code)
        return json.loads(response.content.decode())

    @CacheUtil.query_cache
    def list_ssh_keys(self) -> Dict:
        url = self.url + 'sshkey/list'
        response = self.get(url)
        return json.loads(response.content.decode())

    def reboot(self, subid: str) -> bool:
        url = self.url + 'server/reboot'
        response = self.post(url, data={'SUBID': subid})
        if response.status_code == 200:
            return True
        else:
            logger.warning(response.content.decode())

    def delete_vps(self, subid: str) -> bool:
        url = self.url + 'server/destroy'
        response = self.post(url, data={'SUBID': subid})
        if response.status_code == 200:
            return True
        else:
            logger.warning(response.content.decode())


class LinodeClient(VPSClientBase):

    def __init__(self, account: str, token: str):
        self.account = account
        self.__token = token
        self.header = {
            'Authorization': 'Bearer {}'.format(self.__token)
        }
        self.get = partial(requests.get, headers=self.header, timeout=60)
        self.post = partial(requests.post, headers=self.header, timeout=60)
        self.url = 'https://api.linode.com/v4/'
        self.private_ip_regex = re.compile(
            r'(^127\.)|(^10\.)|(^172\.1[6-9]\.)|(^172\.2\d\.)|'
            r'(^172.3[0-1]\.)|(^192\.168\.)')

    def list_servers(self) -> List:
        vps_list = []
        for i in range(1, 100):
            response = self.get('https://api.linode.com/v4/linode/instances',
                                params={'page': i})
            json_data = json.loads(response.content.decode())
            vps_list.extend(json_data.get('data'))
            if json_data.get('pages') == i:
                break
        return vps_list

    def query_one(self, vps_id: str) -> Dict:
        url = self.url + 'linode/instances/{vps_id}'.format(vps_id=vps_id)
        response = self.get(url)
        if response.status_code == 200:
            return json.loads(response.content.decode())
        else:
            logger.warning(response.content.decode())

    def get_standard_msg(self, vps: Dict) -> Dict:
        ips = vps.get('ipv4')
        ips_public = []
        for ip in ips:
            if not self.private_ip_regex.search(ip):
                ips_public.append(ip)

        return {
            'ipv4': ips_public,
            'vps_id': vps.get('id'),
            'main_ipv4': ips_public[0],
            'region': vps.get('region'),
            'service_provider': 'Linode',
            'account': self.account,
            'label': vps.get('label'),
            'meta': vps,
            'os': vps.get('image')
        }

    def create_vps(self, region: str, plan: str, image: str,
                   label: str, tag: str, ssh_keys: List, **kwargs):
        """
        region:      required
        type: plan   required
        image: os    required
        label:
        group:
        root_pass: required
        authorized_keys: array[id_rsa_pub]
        """
        kwargs.update({
            'region': region,
            'type': plan,
            'image': image,
            'label': label,
            'group': tag,
            'authorized_keys': ssh_keys
        })
        url = self.url + 'linode/instances'
        # set random password
        password = ''.join([chr(random.randint(50, 125)) for x in range(15)])
        kwargs.setdefault('root_pass', password)
        response = self.post(url, json=kwargs)
        if response.status_code == 200:
            return json.loads(response.content.decode())
        else:
            logger.warning(response.content.decode())

    @CacheUtil.query_cache
    def list_regions(self):
        url = self.url + 'regions'
        response = self.get(url)
        return json.loads(response.content.decode())

    @CacheUtil.query_cache
    def list_os(self) -> List:
        url = self.url + 'images'
        images = []
        for i in range(1, 100):
            response = self.get(url,
                                params={'page': i})
            json_data = json.loads(response.content.decode())
            images.extend(json_data.get('data'))
            if json_data.get('pages') == i:
                break
        return images

    @CacheUtil.query_cache
    def list_plans(self):
        url = self.url + 'linode/types'
        response = self.get(url)
        return json.loads(response.content.decode())

    def reboot(self, vps_id: str) -> bool:
        url = self.url + 'linode/instances/{}/reboot'.format(vps_id)
        response = self.post(url,
                             # json={'config_id': 5567}
                             )
        if response.status_code == 200:
            return True
        else:
            logger.warning(response.content.decode())

    def delete_vps(self, vps_id: [int, str]) -> bool:
        url = self.url + 'linode/instances/{}'.format(vps_id)
        response = requests.delete(url, headers=self.header)
        if response.status_code == 200:
            return True
        else:
            logger.warning(response.content.decode())

    def list_disks_of_vps(self, vps_id: [str, int]) -> Dict:
        url = self.url + 'linode/instances/{vps_id}/disks'.format(vps_id=vps_id)
        response = self.get(url)
        if response.status_code == 200:
            return json.loads(response.content.decode())
        else:
            logger.warning(response.content.decode())

    def create_image(self, disk_id: int,
                     label: str = None,
                     description: str = None):
        data = {'disk_id': disk_id}
        if label:
            data.update({'label': label})
        if description:
            data.update({'description': description})
        url = self.url + 'images'
        response = self.post(url, json=data)
        if response.status_code == 200:
            return json.loads(response.content.decode())
        else:
            logger.warning(response.content.decode())

    def change_image(self, image_id: str,
                     label: str,
                     description: str = None) -> bool:
        data = {'label': label}
        if description:
            data.update({'description': description})
        url = self.url + 'images/{}'.format(image_id)
        response = requests.put(url, headers=self.header, json=data)
        if response.status_code == 200:
            return True
        else:
            logger.warning(response.content.decode())

    def query_image(self, image_id: str) -> Dict:
        url = self.url + 'images/{}'.format(image_id)
        response = self.get(url)
        if response.status_code == 200:
            return json.loads(response.content.decode())
        else:
            logger.warning(response.content.decode())

    def delete_image(self, image_id: str) -> bool:
        url = self.url+'images/{}'.format(image_id)
        response = requests.delete(url, headers=self.header)
        if response.status_code == 200:
            return True
        else:
            logger.warning(response.content.decode())

    def rebuild(self, vps_id: str, image_id: str, **kwargs) -> Dict:
        """
        :param vps_id:
        :param image_id:
        :param kwargs: root_pass, authorized_keys
        :return:
        """
        url = self.url+'linode/instances/{}/rebuild'.format(vps_id)
        kwargs.update({'image': image_id})
        # set random password
        password = ''.join([chr(random.randint(50, 125)) for x in range(15)])
        kwargs.setdefault('root_pass', password)
        response = self.post(url, json=kwargs)
        if response.status_code == 200:
            return json.loads(response.content.decode())
        else:
            logger.warning(response.content.decode())


class DigitalOceanClient(VPSClientBase):

    def __init__(self, account: str, token: str):
        self.account = account
        self.__token = token
        self.url = 'https://api.digitalocean.com/v2/'
        self.header = {
            'Content-Type': 'application/json',
            'Authorization': 'Bearer {}'.format(self.__token)
        }
        self.get = partial(requests.get, headers=self.header, timeout=60)
        self.post = partial(requests.post, headers=self.header, timeout=60)

    def list_servers(self) -> List:
        page_size = 200
        vps_list = []
        for i in range(1, sys.maxsize):
            url = self.url + 'droplets'
            response = self.get(url, params={
                'page': i,
                'per_page': page_size
            })
            droplets = json.loads(response.content.decode()).get('droplets', [])
            vps_list.extend(droplets)
            if len(droplets) < page_size:
                break
        return vps_list

    def query_one(self, droplet_id: [str, int]) -> Dict:
        response = requests.get(
            'https://api.digitalocean.com/v2/droplets/{id}'.format(
                id=droplet_id), headers=self.header
        )
        if response.status_code == 200:
            return json.loads(response.content.decode()).get('droplet')
        else:
            logger.warning(response.content.decode())

    def get_standard_msg(self, vps: Dict) -> Dict:
        ips = []
        for i in vps.get('networks', {}).get('v4'):
            if i['type'] == 'public':
                ips.append(i['ip_address'])
        os = vps.get('image').get(
            'distribution') + ' ' + vps.get('image').get('name')
        return {
            'ipv4': ips, 'vps_id': vps.get('id'),
            'main_ipv4': ips[0],
            'region': vps.get('region').get('name'),
            'service_provider': 'DigitalOcean',
            'account': self.account,
            'label': vps.get('name'),
            'meta': vps,
            'os': os
        }

    def rebuild(self, vps_id: [int, str], image='ubuntu-16-04-x64') -> Dict:
        """
        use original image rebuild vps
        """
        url = self.url+'droplets/{}/actions'.format(vps_id)
        data = {
            'type': 'rebuild',
            'image': image
        }
        response = self.post(url, json=data)
        if response.status_code == 201:
            return json.loads(response.content.decode())
        else:
            logger.warning(response.content.decode())

    def restore(self, vps_id: [int, str], image_id: int) -> Dict:
        """
        use snapshots rebuild vps
        """
        url = self.url+'droplets/{}/actions'.format(vps_id)
        data = {
            'type': 'restore',
            'image': image_id
        }
        response = self.post(url, json=data)
        if response.status_code == 201:
            return json.loads(response.content.decode())
        else:
            logger.warning(response.content.decode())

    def resize(self, vps_id: str, plan: str) -> [Dict, bool]:
        url = self.url + 'droplets/{}/actions'.format(vps_id)
        response = self.post(url, json={
            'type': 'resize',
            'size': plan
        })
        if response.status_code == 200:
            return json.loads(response.content.decode())
        else:
            logger.warning(response.content.decode())

    def create_vps(self, region: str, plan: str, image: str,
                   label: str, tag: str, ssh_keys: List, **kwargs):
        """
        'region': string
        'size': string -> list_plans
        'image': string or integer -> list_os
        'ssh_keys': array
        'ipv6': True
        'private_networking': True
        'name': string  -> proxy-d00
        'tags': array
        """
        kwargs.update({
            'region': region,
            'size': plan,
            'image': image,
            'name': label,
            'tags': [tag],
            'ssh_keys': ssh_keys
        })
        url = self.url + 'droplets'
        kwargs.setdefault('ipv6', True)
        kwargs.setdefault('private_networking', True)
        response = self.post(url, json=kwargs)
        if response.status_code == 202:
            return json.loads(response.content.decode())
        else:
            logger.warning(response.content.decode())

    @CacheUtil.query_cache
    def list_regions(self) -> Dict:
        url = self.url + 'regions'
        response = self.get(url)
        return json.loads(response.content.decode())

    @CacheUtil.query_cache
    def list_os(self) -> List:
        url = self.url + 'images'
        size = 100
        images = []
        for i in range(1, 999):
            response = self.get(url, params={'page': i, 'per_page': size})
            images_raw = json.loads(response.content.decode()).get('images')
            images.extend(images_raw)
            if len(images_raw) < size:
                break
        return images

    @CacheUtil.query_cache
    def list_plans(self) -> List:
        url = self.url + 'sizes'
        page_size = 100
        result = []
        for i in range(1, 999):
            response = self.get(url, params={'page': i, 'per_page': page_size})
            sizes = json.loads(response.content.decode()).get('sizes')
            result.extend(sizes)
            if len(sizes) < page_size:
                break
        return result

    @CacheUtil.query_cache
    def list_ssh_keys(self) -> Dict:
        url = self.url + 'account/keys'
        response = self.get(url)
        return json.loads(response.content.decode())

    def create_ssh_key(self, name: str, pub_key: str) -> Dict:
        url = self.url + 'account/keys'
        response = self.post(url, json={
            'name': name,
            'public_key': pub_key
        })
        return json.loads(response.content.decode())

    def create_volume(self, size: int, name: str,
                      region: str, description: str = '') -> Dict:
        url = self.url + '/volumes'
        response = self.post(url, json={'size_gigabytes': size, 'name': name,
                                        'region': region,
                                        'description': description})
        return json.loads(response.content.decode())

    def attach_volume(self, volumes_id: str, vps_id: int) -> Dict:
        """attach a volume to a droplet"""
        url = self.url + 'volumes/{v_id}/actions'.format(v_id=volumes_id)
        response = self.post(url, json={
            'type': 'attach',
            'droplet_id': vps_id
        })
        return json.loads(response.content.decode())

    def list_volumes(self) -> Dict:
        url = self.url + 'volumes'
        response = self.get(url)
        if response.status_code == 200:
            return json.loads(response.content.decode())
        else:
            return response.content.decode()

    def delete_volume(self, volume_id: str) -> bool:
        url = self.url + 'volumes/{}'.format(volume_id)
        response = requests.delete(url, headers=self.header)
        if response.status_code == 204:
            return True
        else:
            logger.warning(response.content.decode())

    def query_action(self, action_id: str) -> Dict:
        """query action status"""
        url = self.url + 'actions/{}'.format(action_id)
        response = self.get(url)
        return json.loads(response.content.decode())

    def reboot(self, vps_id: str) -> Dict:
        url = self.url + 'droplets/{}/actions'.format(vps_id)
        response = self.post(url, json={'type': 'reboot'})
        return json.loads(response.content.decode())

    def delete_vps(self, droplet_id) -> bool:
        """success code 204"""
        url = self.url + 'droplets/{}'.format(droplet_id)
        response = requests.delete(url, headers=self.header)
        if response.status_code == 204:
            return True
        else:
            logger.warning(response.content.decode())

    def list_all_snapshots(self) -> Dict:
        url = self.url + 'snapshots'
        response = self.get(url)
        return json.loads(response.content.decode())

    def create_snapshots(self, vps_id: [str, int], name: str = None) -> Dict:
        # response_code 201
        url = self.url + 'droplets/{}/actions'.format(vps_id)
        if name:
            data = {
                'type': 'snapshot',
                'name': name
            }
        else:
            data = {'type': 'snapshot'}
        response = self.post(url, json=data)
        if response.status_code == 201:
            return json.loads(response.content.decode())
        else:
            logger.warning(response.content.decode())

    create_image = create_snapshots

    def delete_snapshot(self, snapshot_id: [str, int]) -> bool:
        url = self.url + '/snapshots/{}'.format(snapshot_id)
        response = requests.delete(url, headers=self.header)
        if response.status_code == 204:
            return True
        else:
            logger.warning(response.content.decode())

    def transfer_image(self, os_id: str, region: str) -> Dict:
        url = self.url + '/images/{}/actions'.format(os_id)
        response = self.post(url, json={'type': 'transfer', 'region': region})
        if response.status_code == 201:
            return json.loads(response.content.decode())
        else:
            logger.warning(response.content.decode())


CLIENT = {
    'Vultr': VultrClient,
    'Linode': LinodeClient,
    'DigitalOcean': DigitalOceanClient
}


class VPSClient(object):

    def __init__(self, provider, account, token):
        # create specific provider vps_clientk
        self.client = CLIENT.get(provider)(account, token)
        self.account = account
        self.provider = provider
        self.regions_cache = []

    def get_proxy_params(self, region: str) -> Dict:
        proxy_params = {
            'DigitalOcean': {
                'plan': '512mb',
                'image': 21669205,
                'region': self.get_region_id(region)
            },
            'Linode': {
                'plan': 'g5-nanode-1',
                'image': 'linode/ubuntu16.04lts',
                'region': self.get_region_id(region)
            },
            'Vultr': {
                'plan': 201,
                'image': 216,
                'region': self.get_region_id(region)
            }
        }
        return proxy_params.get(self.provider)

    def get_region_id(self, region: str) -> str:
        if self.provider == 'DigitalOcean':
            regions = self.client.list_regions().get('regions')
            for i in regions:
                if i.get('name') == region:
                    return i.get('slug')
        elif self.provider == 'Vultr':
            regions = self.client.list_regions().values()
            for i in regions:
                if i.get('name') == region:
                    return i.get('DCID')

        elif self.provider == 'Linode':
            return region

    @staticmethod
    def get_min_key(doc: Dict[str, int]):
        # from dict query key of minimum value
        return sorted(doc, key=lambda x: doc[x])[0]

    def auto_buy_proxy(self, number: int, coll: Collection,
                       label: str = None, tag: str = 'proxy'):
        # region distribution
        region_dist = {}
        for i in coll.distinct('region'):
            region_dist.update({
                i: coll.count({'region': i})
            })

        for i in range(number):
            region = self.get_min_key(region_dist)
            params = self.get_proxy_params(region)
            params.update({
                'label': self.get_proxy_label(label, i),
                'tag': tag,
                'ssh_keys': [self.get_vps_management_key()]
            })

    def get_vps_management_key(self) -> Union[int, str]:
        if self.provider == 'DigitalOcean':
            ssh_keys = self.client.list_ssh_keys().get('ssh_keys')
            for i in ssh_keys:
                if i.get('name') == 'vps-management':
                    return i.get(id)

        elif self.provider == 'Vultr':
            ssh_keys = self.client.list_ssh_keys().values()
            for i in ssh_keys:
                if i.get('name') == 'vps-namagement':
                    return i.get('SSHKEYID')

        elif self.provider == 'Linode':
            return 'ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQDAJGElVlXn514nBLDT' \
                   'obVnssBWBV1w62F5XbT5xxvDzSSROx0/AEIDxR6KT/sIMkaiX+k9z/MO' \
                   'tw4h3tIJdaxwhpspd95Im0iKAAXyXFrV/lGWQbVUsK7azF80LCY9H2wD' \
                   'vh7B/pwGPrqdDVhQNwT/+9n3/iUuW1ELmQxlOPx8raS8X0gKIrK2vFsJ' \
                   'P5WIbGDhuCfvxrqM4spkvyJ+7UhDDAczTo2xj8N/Nuw1E9jUE2lC4MM0' \
                   '2dYrj5+6+RKNSLAEOBgrpdN+7dTeM9f6PLr3U1wzGrOGckievVJ4pU3B' \
                   'GMNzg6VLuPyci2WF8x74bqUSHQvIvHpGamW8PEZ7Ip09 vps-managem' \
                   'ent@SocialbirdDRG006'


if __name__ == '__main__':
    pass
