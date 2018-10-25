import time
import random
import pprint

from itertools import cycle
from queue import Queue
from threading import Thread
from typing import List
from typing import Dict
from os import path

from pymongo.collection import Collection

from testinfra import get_host
from testinfra.host import Host
from select_proxy import create_logger
from select_proxy.utils.thread_task import thread_task_hoovers
from select_proxy.utils.thread_task import get_pub_proxy
from select_proxy.utils.thread_task import callback_privoxy
from select_proxy.utils.thread_task import use_proxy
from select_proxy.settings import client
from select_proxy.settings import date
from select_proxy.settings import local_time
from select_proxy.utils.handle_error import ignore_all_error

from jinja2 import Template

from select_proxy.settings import USER_AGENTS
from select_proxy.settings import URLS
from select_proxy.ss_privoxy_settings import local_ip

from utils.VPSClient import DigitalOceanClient

pp = pprint.PrettyPrinter(indent=4)
logger = create_logger(__name__)
coll_msg = client['vps_management']['ss_privoxy_msg']
coll_ocean_jiang = client['vps_management']['apollo_ocean_jiang']
coll_ocean_sun = client['vps_management']['apollo_ocean_sun']
headers = {
    'Accept': 'text/html,application/xhtml+xml,'
              'application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Encoding': 'gzip, deflate, sdch, br',
    'Accept-Language': 'en-US, en; q=0.8',
}


def create_ss_privoxy_msg(src: Collection, dst: Collection):
    count = 12346
    for i in src.find():
        ip = i['main_ipv4']
        while True:
            msg = dst.find_one({'local_port': count})
            if not msg or msg.get('status', {}).get(date) != 'valid':
                logger.debug('update port: {} ---> {}'.format(count, ip))
                dst.update_one({'local_port': count}, {'$set': {
                    'ip': ip,
                    'coll_name': 'apollo_ocean_jiang',
                    'local_port': count,
                    'service_provider': i.get('service_provider'),
                    'account': i.get('account')
                }}, upsert=True)
                count += 1
                break
            else:
                count += 1
    logger.info('end port: {}'.format(count - 1))


def create_docker_task():
    coll = client['vps_management']['ss_privoxy_msg']
    for i in coll.find():
        port = i['local_port']
        with open('ss_privoxy/docker_compose_template') as f:
            template = Template(f.read())
            with open(
                    'ss_privoxy/docker_tasks/'
                    'docker_compose_{}.yml'.format(port),
                    'w'
            ) as fe:
                fe.write(template.render(port=port))

        with open('ss_privoxy/ss_config_template') as f:
            template = Template(f.read())
            with open(
                    'ss_privoxy/docker_tasks/ss_config_{}.json'.format(port),
                    'w'
            ) as fe:
                fe.write(template.render(ipv4=i.get('ip')))


def test_hoovers_multiple_thread(coll: Collection):
    queue = Queue()
    # start to thread
    for i in range(20):
        t = Thread(target=thread_task_hoovers,
                   args=(queue, coll, get_pub_proxy, callback_privoxy))
        t.setDaemon(True)
        t.start()
    for doc in coll.find({'status.2018-03-09': {'$ne': 'valid'}}):
        queue.put('10.255.0.4:{}'.format(doc['local_port']))
    # await task done
    queue.join()


def update_history(coll: Collection):
    dst_coll = client['vps_management']['ipv4_history']
    for doc in coll.find():
        logger.debug(doc)
        dst_coll.update_one({'ip': doc['ip']}, {'$set': {
            'ip': doc.get('ip'),
            'status.{}'.format(date): doc['status'][date]
        }})
        logger.info('update ip: {}'.format(doc['ip']))


def update_vps_status(src: Collection, dst: Collection):
    """
    :param src:
    :param dst:
    :return:
    """
    for i in src.find():
        status = i['status'][date]
        dst.update_one({'ipv4': i['ip']},
                       {'$set':
                            {'hoovers_ip.{}'.format(i['ip'].replace('.', '-')):
                                 status,
                             'local_port': i['local_port'],
                             }}
                       )


def test_start_docker():
    coll = client['vps_management']['ss_privoxy_msg']
    host = get_host('ssh://fumao-zhou@10.255.0.4')
    cmd = host.run("docker ps | awk '{print $12}'")
    ports = coll.distinct('local_port')
    # logger.debug(cmd.stdout)
    use_ports = list(map(
        lambda x: int(x.split(':')[1].split('->')[0]),
        filter(bool, cmd.stdout.split('\n'))))
    # mark_started_port(use_ports, coll)
    # stop_docker(use_ports, coll, host)
    pp.pprint(len(use_ports))


def mark_started_port(start_ports: List, coll: Collection):
    for i in start_ports:
        logger.debug('mark port: {}'.format(i))
        coll.update_one({'local_port': i}, {'$set': {'handle': 'started'}})


def stop_docker(start_ports: List, coll: Collection, host: Host):
    for i in start_ports:
        msg = coll.find_one({'local_port': i})
        if msg and msg.get('status', {}).get(date) != 'valid':
            logger.debug('stop container that port is {}'.format(i))
            cmd = host.run('docker-compose -f /home/fumao-zhou/docker-compose/'
                           'ss-privoxy/docker_compose_{}.yml down'.format(i))
            logger.debug('output: {}\nerror: {}'.format(cmd.stdout, cmd.stderr))
        else:
            logger.debug('>>>>{}<<<<< is valid'.format(i))


def get_cycle_regions(vps_client: DigitalOceanClient):
    return cycle((i['slug'] for i in vps_client.list_regions().get('regions')))


def get_next_letter(coll: Collection, letter: str = 'r') -> int:
    """
    from coll total apollo-() return next letter
    :param coll: vps coll
    :param letter: start letter
    :return: letter 'a', 'b', 'c'....
    """
    s = list(map(lambda x: int(x[8:]), coll.distinct('label')))
    s.sort()
    return s[-1] + 1 if s else letter


@ignore_all_error
def process_buy_vps(vps_client: DigitalOceanClient,
                    coll: Collection,
                    sleep_second: int):
    ssh_keys = {'jiang': [5535474, 8681866, 18002369],
                'sun': [18002374, 14188476, 11726484, ]}
    images = {'sun': 32245595,
              'jiang': 32245594}
    regions = get_cycle_regions(vps_client)
    while True:
        number = get_next_letter(coll, 'x00')
        kwargs = {
            'region': next(regions),
            'plan': 's-1vcpu-1gb',
            'image': images[vps_client.account],
            'label': 'apollo-z{:02}'.format(number + 1),
            'tag': 'apollo',
            'ssh_keys': ssh_keys[vps_client.account],
        }
        logger.debug('create digital ocean vps: {}'.format(kwargs.get('label')))
        res = vps_client.create_vps(**kwargs)
        if res:
            logger.debug('create success vps')
        else:
            logger.debug('create failed')
        time.sleep(sleep_second)


def distribution_of_port(coll: Collection, vps: Dict, port: int=12346) -> Dict:
    ports = coll.distinct('local_port')
    while True:
        if port in ports:
            port += 1
            continue
        vps.update({'local_port': port, 'local_ip': local_ip})
        return vps


def update_vps_history_action(vps: Dict, action: str):
    coll = client['vps_management']['ipv4_history']
    for ip in vps['ipv4']:
        logger.debug('update action msg:{}>>>{}<<<'.format(action, ip))
        coll.update_one({'ip': ip},
                        {'$set': {
                            'ip': ip,
                            'service_provider': vps['service_provider'],
                            'region': vps['region'],
                            'action.{}'.format(local_time): action
                        }}, upsert=True)


def update_vps_history_status(vps: Dict):
    coll = client['vps_management']['ipv4_history']
    for ip in vps['ipv4']:
        logger.debug('update status msg >>>{}<<<'.format(ip))
        coll.update_one(
            {'ip': ip},
            {'$set':
                 {'ip': ip,
                  'service_provider': vps['service_provider'],
                  'region': vps['region'],
                  'status.hoovers.{}'.format(date):
                      vps.get('hoovers') or
                      vps.get('hoovers_ip', {}).get(ip.replace('.', '-'))
                  }
             }, upsert=True)


@ignore_all_error
def process_collection_vps(vps_client: DigitalOceanClient,
                           coll: Collection, sleep_second: int):
    while True:
        logger.debug('=========start to process_collection_vps=========')
        for vps in vps_client.get_all_vps():
            if coll.find_one({'main_ipv4': vps['main_ipv4']}):
                continue
            if not vps['label'].startswith('apollo'):
                continue
            logger.debug('collection vps>>>{}<<<'.format(vps['main_ipv4']))
            vps.update({'handle': 'await deploy'})
            vps = distribution_of_port(coll, vps)
            coll.insert_one(vps)
            update_vps_history_action(vps, 'created')
        logger.debug('=========process_collection_vps end=========')
        time.sleep(sleep_second * 10)


def directly_distribute_ports(coll: Collection):
    for i in coll.find({'handle': {'$exists': 0}}):
        vps = distribution_of_port(coll, i, 15346)
        vps.update({'handle': 'await deploy'})
        logger.debug('distribute port >>>{}<<<'.format(vps['main_ipv4']))
        coll.update_one({'main_ipv4': vps['main_ipv4']}, {'$set': vps})


@ignore_all_error
def process_delete_vps(vps_client: DigitalOceanClient,
                       coll: Collection,
                       sleep_second: int):
    while True:
        logger.debug('==========start to process_delete_vps===========')
        for vps in coll.find({'handle': 'await delete'},
                             no_cursor_timeout=True):
            res = vps_client.delete_vps(vps.get('vps_id'))
            if res:
                logger.debug(
                    'delete vps  successful>>>{}<<<'.format(vps['main_ipv4'])
                )
                coll.delete_one({'main_ipv4': vps.get('main_ipv4')})
                update_vps_history_action(vps, 'deleted')
            else:
                logger.debug(
                    'delete vps fail>>>{}<<<'.format(vps['main_ipv4'])
                )
                coll.update_one({'main_ipv4': vps.get('main_ipv4')},
                                {'$set': {'delete_failed': True}})
        logger.debug('==========process_delete_vps end===========')
        time.sleep(sleep_second * 10)


@ignore_all_error
def process_create_compose(coll: Collection, sleep_second: int):
    while True:
        logger.debug('==========start to process_create_compose===========')
        for vps in coll.find({'handle': 'await deploy'},
                             no_cursor_timeout=True):
            port = vps['local_port']
            logger.debug('create compose of port: {}'.format(port))
            with open('ss_privoxy/docker_compose_template') as f:
                template = Template(f.read())
                with open(
                        'ss_privoxy/{}/'
                        'docker_compose_{}.yml'.format(local_ip, port),
                        'w'
                ) as fe:
                    fe.write(template.render(port=port))

            with open('ss_privoxy/ss_config_template') as f:
                template = Template(f.read())
                with open(
                        'ss_privoxy/{}/ss_config_{}.json'.format(
                            local_ip, port),
                        'w') as fe:
                    fe.write(template.render(ipv4=vps.get('main_ipv4')))
            coll.update_one({'main_ipv4': vps.get('main_ipv4')},
                            {'$set': {'handle': 'await start'}})
        logger.debug('==========process_create_compose end===========')
        time.sleep(sleep_second * 10)


project_path = path.abspath(
    path.join(__file__, path.pardir, path.pardir)
)


def allocated_port(coll: Collection, port: int):
    coll.update_one({'local_port': port, 'description': 'allocated'},
                    {'local_port': port, 'description': 'allocated'},
                    upsert=True)


@ignore_all_error
def process_start_container(
        coll: Collection, host: Host, sleep_second: int, limit: int):
    while True:
        logger.debug('==========start to process_start_container===========')
        cmd = host.run('docker ps | wc -l')
        number = int(cmd.stdout.strip())
        for vps in coll.find({'handle': 'await start'},
                             no_cursor_timeout=True):
            if number > limit:
                continue
            cmd = host.run(
                'docker-compose -f {path}/ss_privoxy/'
                '{ip}/docker_compose_{port}.yml up -d'.format(
                    path=project_path, ip=local_ip, port=vps['local_port']))
            if 'done' in cmd.stdout + cmd.stderr:
                logger.debug(
                    'successful start container '
                    'in port {}'.format(vps['local_port'])
                )
                coll.update_one({'main_ipv4': vps['main_ipv4']},
                                {'$set': {'handle': 'await test'}})
                number += 1
            elif 'port is already allocated' in cmd.stdout + cmd.stderr:
                logger.debug(
                    'failed start container: {}'.format(
                        'port is already allocated')
                )
                allocated_port(coll, vps.get('local_port'))
                coll.update_one({'main_ipv4': vps['main_ipv4']},
                                {'$set': {'handle': 'await test'}})
            elif 'up-to-date' in cmd.stdout + cmd.stderr:
                logger.debug(
                    'failed start container: {}'.format('already started')
                )
                coll.update_one({'main_ipv4': vps['main_ipv4']},
                                {'$set': {'handle': 'await test'}})
            else:
                logger.debug('failed start container: {}'.format(
                    cmd.stdout + cmd.stderr
                ))
        logger.debug('==========process_start_container end===========')
        time.sleep(sleep_second * 10)


def save_test_result(coll: Collection, vps: Dict, status: str):
    if status == 'valid':
        vps.update({'handle': 'ok', 'hoovers': status})
    else:
        vps.update({'handle': 'await stop', 'hoovers': status})
    coll.update_one({'main_ipv4': vps['main_ipv4']}, {'$set': vps})
    update_vps_history_status(vps)


@ignore_all_error
def process_test_hoovers(coll: Collection, sleep_second: int):
    while True:
        logger.debug('===========start to process_test_hoovers================')
        user_agent = random.choice(USER_AGENTS)
        headers.update({'User-Agent': user_agent})
        for vps in coll.find({'handle': 'await test'}, no_cursor_timeout=True):
            url = random.choice(URLS)
            ip = '{}:{}'.format(vps.get('local_ip', '10.255.0.4'),
                                vps.get('local_port'))
            scheme = 'http'
            proxy = get_pub_proxy(ip)
            status, code = use_proxy(scheme, proxy, 10,
                                     url,
                                     headers)
            save_test_result(coll, vps, status)
        logger.debug('===========process_test_hoovers end================')
        time.sleep(sleep_second)


@ignore_all_error
def process_stop_container(coll: Collection, host: Host, sleep_second: int):
    while True:
        logger.debug('==========start to process_stop_container===============')
        for vps in coll.find({'handle': 'await stop'}, no_cursor_timeout=True):
            cmd = host.run(
                'docker-compose -f {path}/'
                'ss_privoxy/{ip}/docker_compose_{port}.yml down'.format(
                    path=project_path, ip=local_ip, port=vps['local_port']
                ))
            if 'done' in cmd.stderr:
                logger.debug(
                    'successful stop container '
                    'in port {}'.format(vps['local_port'])
                )
                coll.update_one({'main_ipv4': vps['main_ipv4']},
                                {'$set': {'handle': 'await delete'}})
            else:
                logger.debug('failed stop container {}: {}'.format(
                    vps['local_port'],
                    cmd.stdout + cmd.stderr))
        logger.debug('==========process_stop_container end===============')
        time.sleep(sleep_second * 5)


# def test_loop_delete_mongo():
#     coll = client['test']['test_delete']
#     data = ['hello', 'world', 'python', 'mongo', 'squid', 'ansible']
#     for i in data:
#         logger.debug('insert msg: {}'.format(i))
#         coll.insert({'msg': i})
#
#     for i in coll.find():
#         logger.debug('delete msg: {}'.format(i['msg']))
#         coll.delete_one({'msg': i['msg']})
#
#
# def test_start_compose():
#     host = get_host('ssh://fumao-zhou@10.255.0.4')
#     coll = client['vps_management']['ss_privoxy_msg']
#     for i in coll.find({'handle': {'$exists': 0}}):
#         logger.debug(
#             'start container that port is {}'.format(i.get('local_port')))
#         cmd = host.run('docker-compose -f /home/fumao-zhou/docker-compose/'
#                        'ss-privoxy/docker_'
#                        'compose_{}.yml up -d'.format(i['local_port']))
#         # time.sleep(4)
#         logger.debug('output: {}\nerror: {}'.format(cmd.stdout, cmd.stderr))


def repair_stop():
    ports = []
    coll = client['vps_management']['apollo_ocean_sun']
    ps = coll.distinct('local_port')
    host = get_host('ssh://fumao-zhou@10.255.0.4')
    for p in ports:
        if p not in ps:
            logger.debug('stop container {}'.format(p))
            cmd = host.run('docker-compose -f /home/fumao-zhou/select-proxy/'
                           'ss_privoxy/docker_tasks/docker_compose_{}.yml down'.format(p))
            logger.debug(cmd.stderr)


if __name__ == '__main__':
    # create_ss_privoxy_msg(coll_ocean_sun, coll_msg)
    # create_docker_task()
    # test_hoovers_multiple_thread(coll_msg)
    # update_history(coll_msg)
    # update_vps_status(coll_msg, coll_ocean_sun)
    # test_start_docker()
    # repair_stop()
    # test_loop_delete_mongo()
    # test_start_compose()
    coll = client['vps_management']['azure_vps']
    directly_distribute_ports(coll)
    pass
