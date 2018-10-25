from pprint import PrettyPrinter
from typing import Dict
from threading import Thread
from queue import Queue

from pymongo.collection import Collection

from utils.VPSClient import DigitalOceanClient
from settings import client
from create_ansible_task import create_ansible_task
from settings_tokens import DIGITALOCEAN_API_TOKEN
from utils.thread_task import thread_task_hoovers
from utils.thread_task import thread_task
from select_proxy import create_logger


logger = create_logger(__name__)

pp = PrettyPrinter(indent=4)

jiang = DigitalOceanClient('jiang', DIGITALOCEAN_API_TOKEN['jiang'])
coll_jiang = client['vps_management']['apollo_ocean_jiang']
sun = DigitalOceanClient('sun', DIGITALOCEAN_API_TOKEN['sun'])
coll_sun = client['vps_management']['apollo_ocean_sun']


def view_msg():
    pp.pprint(jiang.list_os())
    pp.pprint(jiang.list_plans())
    pp.pprint(jiang.list_regions())
    pp.pprint(jiang.list_ssh_keys())


def get_regions(coll: Collection, vps_client: DigitalOceanClient) -> Dict:
    # if not coll.find_one():
    #     return { i['slug']:
    #                  0 for i in vps_client.list_regions().get('regions')}
    return {i['slug']: 0 for i in vps_client.list_regions().get('regions')}
    #
    # regions = {}
    # for vps in coll.find():
    #     if vps.get('meta').get('region').get('slug') not in regions:
    #         regions.update({vps.get('region'): 0})
    #     regions[vps.get('region')] += 1
    #
    # return regions


def get_min_key(data: Dict, skip: int = 0) -> str:
    return sorted(data, key=lambda x: data[x])[skip]


def get_next_letter(coll: Collection, letter: str='r') -> int:
    """
    from coll total apollo-() return next letter
    :param coll: vps coll
    :param letter: start letter
    :return: letter 'a', 'b', 'c'....
    """
    s = list(map(lambda x: int(x[8:]), coll.distinct('label')))
    s.sort()
    return s[-1] + 1 if s else letter


def fill_vps(coll: Collection, vps_client: DigitalOceanClient, letter: str= 'r'):
    # images id: 21669205
    # plan id: s-1vcpu-1gb
    ssh_keys = {'jiang': [5535474, 8681866, 18002369],
                'sun': [18002374, 14188476, 11726484, ]}
    images = {'sun': 32245595,
              'jiang': 32245594}
    regions = get_regions(coll, vps_client)
    number = get_next_letter(coll, letter)
    for i in range(number+1, number+1000):
        min_region = get_min_key(regions)
        kwargs = {
            'region': min_region,
            'plan': 's-1vcpu-1gb',
            'image': images[vps_client.account],
            'label': 'apollo-z{:02}'.format(i),
            'tag': 'apollo',
            'ssh_keys': ssh_keys[vps_client.account],
        }
        logger.debug('create digital ocean vps: {}'.format(kwargs.get('label')))
        res = vps_client.create_vps(**kwargs)
        if res:
            regions[min_region] += 1
            logger.debug('create success')
        else:
            logger.debug('create failed')
            del regions[min_region]

    # for i in vps_ids:
    #     res = vps_client.query_one(i)
    #     vps = vps_client.get_standard_msg(res)
    #     coll.update_one({'main_ipv4': vps.get('main_ipv4')},
    #                     {'$set': vps}, upsert=True)


def create_task_with_vps(coll: Collection, task_name: str):
    ips = []
    for vps in coll.find():
        if vps.get('https_ip', {}).get(
                vps.get('main_ipv4').replace('.', '-')) != 'valid' and \
                vps.get('hoovers_ip', {}).get(
                    vps.get('main_ipv4').replace('.', '-')) != 'valid':
            ips.append(vps.get('main_ipv4'))

    create_ansible_task(task_name, ips, [])


def test_https_multiple_thread(coll: Collection=coll_jiang):
    queue = Queue()
    # start to thread
    for i in range(20):
        t = Thread(target=thread_task, args=(queue, coll))
        t.setDaemon(True)
        t.start()
    for doc in coll.find(
            # {'https': {'$ne': 'valid'}}
    ):
        # queue.put(doc.get('main_ipv4'))
        for ip in filter(
                lambda x: doc.get(
                    'https_ip', {}).get(x.replace('.', '-')) != 'valid',
                doc.get('ipv4')):
            queue.put(ip)
    # await task done
    queue.join()


def test_hoovers_multiple_thread(coll: Collection=coll_jiang,
                                 repeat: bool=False):
    queue = Queue()
    # start to thread
    for i in range(20):
        t = Thread(target=thread_task_hoovers, args=(queue, coll))
        t.setDaemon(True)
        t.start()
    for doc in coll.find({
        # 'hoovers': {'$ne': 'valid'}
    }):
        # queue.put(doc.get('main_ipv4'))
        if repeat:
            for ip in filter(
                    bool,
                    doc.get('ipv4')
            ):
                queue.put(ip)
        else:
            for ip in filter(
                    lambda x: doc.get(
                        'hoovers_ip', {}).get(x.replace('.', '-')) != 'valid',
                    doc.get('ipv4')
            ):
                queue.put(ip)
    # await task done
    queue.join()


def view_invalid_vps(coll: Collection=coll_jiang):
    invalid_ips = set()
    valid_ips = set()

    for vps in coll.find():
        ip = vps.get('main_ipv4')
        # if vps.get('https_ip').get(ip.replace('.', '-')) != 'valid' and \
        #         vps.get('hoovers_ip').get(ip.replace('.', '-')) != 'valid':
        if vps.get('hoovers_ip', {}).get(ip.replace('.', '-')) != 'valid':
            invalid_ips.add(vps.get('main_ipv4'))
        else:
            valid_ips.add(vps.get('main_ipv4'))
            logger.debug('all valid main ipv4: {}'.format(vps.get('main_ipv4')))

    # for i in invalid_ips:
    #     coll.delete_one({'main_ipv4': i})

    logger.info('invalid: {}'.format(len(invalid_ips)))
    logger.info('valid: {}'.format(len(valid_ips)))
    return len(invalid_ips)


def delete_invalid_vps(coll: Collection=coll_jiang,
                       vps_client: DigitalOceanClient=jiang):
    delete_ips = []
    try:
        for vps in coll.find():
            if vps.get('hoovers_ip', {}).get(
                    vps.get('main_ipv4').replace('.', '-')
            ) != 'valid':
                logger.debug('delete vps : {}'.format(vps.get('main_ipv4')))
                res = vps_client.delete_vps(vps.get('vps_id'))
                if res:
                    logger.debug(
                        'delete vps success: {}'.format(vps.get('main_ipv4')))
                    delete_ips.append(vps.get('main_ipv4'))
    except Exception as exc:
        logger.error(exc)
    finally:
        for i in delete_ips:
            logger.debug('delete vps from collection : {}'.format(i))
            coll.delete_one({'main_ipv4': i})


def delete_vps_from_coll(coll: Collection):
    delete_vps = []
    for vps in coll.find():
        if vps.get('hoovers_ip', {}).get(
                vps.get('main_ipv4').replace('.', '-')) != 'valid':
            delete_vps.append(vps)

    for i in delete_vps:
        print(i.get('main_ipv4'))
        coll.delete_one({'_id': i.get('_id')})


def vps_process(coll: Collection, vps_client: DigitalOceanClient,
                task_name: str, letter: str='h'):
    # test proxy
    logger.info('start to test proxy of hoovers')
    # test_https_multiple_thread(coll)
    # test_hoovers_multiple_thread(coll, True)
    # test_https_multiple_thread(coll)
    # test_hoovers_multiple_thread(coll)

    # view invalid vps
    # view_invalid_vps(coll)
    view_invalid_vps(coll)
    for i in range(3):
        # break
        # delete invalid vps
        logger.info('start to delete vps')
        delete_invalid_vps(coll, vps_client)
    delete_vps_from_coll(coll)

    # buy vps
    # logger.info('start to buy vps')
    # try:
    #     fill_vps(coll, vps_client, letter)
    # except IndexError:
    #     pass
    # except Exception as exc:
    #     logger.debug(exc)
    # logger.info('update collection message')
    # fill_collection(coll, vps_client)
    # create task
    # create_task_with_vps(coll, task_name)


def fill_collection(coll: Collection=coll_jiang,
                    vps_client: DigitalOceanClient=jiang):
    for vps in vps_client.get_all_vps():
        if vps.get('label').startswith('apollo'):
            coll.update_one({'main_ipv4': vps.get('main_ipv4')},
                            {'$set': vps}, upsert=True)


if __name__ == '__main__':
    vps_process(coll_jiang, jiang, 'apollo_ocean_jiang')
    pass
