from pprint import PrettyPrinter
from typing import Dict
from threading import Thread
from queue import Queue

from pymongo.collection import Collection

from utils.VPSClient import LinodeClient
from settings import client
from create_ansible_task import create_ansible_task
from settings_tokens import LINODE_API_TOKEN
from utils.thread_task import thread_task_hoovers
from utils.thread_task import thread_task
from select_proxy import create_logger

pp = PrettyPrinter(indent=4)

sun = LinodeClient('sun', LINODE_API_TOKEN['sun'])
jiang = LinodeClient('jiang', LINODE_API_TOKEN['jiang'])
coll_jiang = client['vps_management']['apollo_linode_jiang']
coll_sun = client['vps_management']['apollo_linode_sun']
logger = create_logger(__name__)

authorized_keys = [
    # jianen
    'ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQC+f8/rxsYKL+N66lYlJuysdLbEUtqvGP3xLTJp1AWcZSMA+SuO9I6XQy6ZbmOk9laNW3uaUyVWBd2Y9wucTssX/9qyr3sn+Kxq/zTbne0RBbKhA3qdjnJiOqvlbks30JKl+8rf1i+nnuyxaTWYal2yhg+2SZS1Wkz6O1nhrTQmI27Eoat9e/D2A5KyEmvaMHTuM3pZVoG1pRiTtetIDLsUzAoh7BpJRZJzT+2dZvtyeey5EnzRyXWRjLY8Z9spkd2aylsUnGsEfLnifKjE8ZGzFFRuN7z94jK9/t+pNYa0CbyHu4BdcTwvp7os+wQMPY0caEoEywFQg+G3TYn0py2H alex-wang@SocialbirdDRG002',
    # grammy
    'ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQDW8WnH/jXO48vF6bJVSBuwkQYHDkXp+sTRZz1kJ4z4YsE5nsRgLjuSYcXIfskGwX/nGUwnBEVPN04beNaGZ83h3oKyVvr3KvQWPhNgkrNYj1zc7TbPUb6wA1OhI5NwcX2RclePVxJWqfaQGGbVILO0vLxROhx/e7IGmUHFGRhHj1Rj1/FqUDYelVmaRVp1WWzdVwFzg8YhSMSA5P3GJZTScU4ZnEXmYofUygXdcH5g7VsOe6ea4mG4wdqO0KZQZu0Mg3qe6eOPcBHK0PipCUN4BmlZ3uF2Wsmy2/Cmrv1Q1hcuNPbbKaCHWZZBHZOGxnDCwC4lfa6tjDKDxpzHv2x3 grammy-jiang@SocialbirdDRG000',
    # frank
    'ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQC5SjJZc3z7SrOF5Rrf2XHzjNz152JavK+6BvVKOb6jQ5waWVxYrDtdzBhGiJSn2aM4vFZDFAtxA6gVaBqVYanbInqsTLn778rnWRek1EDG3hwKYGDqdgoglkVCMadW6pyHLaoElttjFTC1w8ZZ+tPH24t4qRI/EMZQnYbiqVjmlGLBCyHK810LvXCGOHjom+sTdd4+c+Lozo3tH4JHIeSgiBHPJp+wH57BCkI9a8qsVJeDGlNV8tlIh1ZOmGfPeKDOwksaD8BRDo3v98FPkSO5J99f8B0VSXKjCSPk3xtCkzpbtXm88HPiD6F2175NbnoRyxHKkjBDmlLNk0bL4yVj frank-wang@SocialbirdDRG001',
    # vps-management
    'ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQDAJGElVlXn514nBLDTobVnssBWBV1w62F5XbT5xxvDzSSROx0/AEIDxR6KT/sIMkaiX+k9z/MOtw4h3tIJdaxwhpspd95Im0iKAAXyXFrV/lGWQbVUsK7azF80LCY9H2wDvh7B/pwGPrqdDVhQNwT/+9n3/iUuW1ELmQxlOPx8raS8X0gKIrK2vFsJP5WIbGDhuCfvxrqM4spkvyJ+7UhDDAczTo2xj8N/Nuw1E9jUE2lC4MM02dYrj5+6+RKNSLAEOBgrpdN+7dTeM9f6PLr3U1wzGrOGckievVJ4pU3BGMNzg6VLuPyci2WF8x74bqUSHQvIvHpGamW8PEZ7Ip09 vps-management@SocialbirdDRG006'
]
images = {
    'jiang': 'private/3339696',
}


def delete_guess_email():
    ids = []
    delete = ['172.104.34.104',
              '172.104.53.65',
              '172.105.221.227',
              '172.105.199.26',
              "45.79.163.55"]
    for vps in sun.get_all_vps():
        if vps.get('main_ipv4') in delete:
            logger.debug('{}-{}:{}'.format(vps.get('region'), vps.get('label'),
                                           vps.get('main_ipv4')))
            ids.append(vps.get('vps_id'))

    for i in ids:
        logger.debug('delete id: {}'.format(i))
        res = sun.delete_vps(i)
        if res:
            logger.debug(res)


def view_msg():
    pp.pprint(sun.list_os())
    pp.pprint(sun.list_plans())
    pp.pprint(sun.list_regions())


def get_regions(coll: Collection, vps_client: LinodeClient) -> Dict:
    # if not coll.find_one():
    return {i['id']: 0 for i in vps_client.list_regions().get('data')}

    #     regions = {}
    # for vps in coll.find():
    #     if vps.get('region') not in regions:
    #         regions.update({vps.get('region'): 0})
    #     regions[vps.get('region')] += 1
    #
    # return regions


def get_min_key(data: Dict, skip: int = 0) -> str:
    return sorted(data, key=lambda x: data[x])[skip]


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


def fill_vps(coll: Collection, vps_client: LinodeClient,
             letter: str = 'r', region: str = ''):
    # images id: linode/ubuntu16.04lts
    # plan id: g5-nanode-1
    if region:
        regions = {region: 0}
    else:
        regions = get_regions(coll, vps_client)
    logger.debug('regions: {}'.format(regions))
    number = get_next_letter(coll, letter)
    for i in range(number + 1, number + 400):
        min_region = get_min_key(regions)
        kwargs = {
            'region': min_region,
            'plan': 'g5-nanode-1',
            'image': images[vps_client.account],
            'label': 'apollo-z{:02}'.format(i),
            'tag': 'apollo',
            'ssh_keys': authorized_keys,
        }
        logger.debug('create linode vps: {}'.format(kwargs.get('label')))
        res = vps_client.create_vps(**kwargs)
        if res.get('id'):
            vps = vps_client.get_standard_msg(res)
            coll.update_one({'main_ipv4': vps.get('main_ipv4')},
                            {'$set': vps}, upsert=True)
            regions[min_region] += 1
            logger.debug('create success')
        else:
            logger.debug('create failed: {}'.format(res))
            del regions[min_region]


def create_task_with_vps(coll: Collection, task_name: str):
    ips = []
    for vps in coll.find():
        if vps.get('https_ip', {}).get(
                vps.get('main_ipv4').replace('.', '-')) != 'valid' and \
                vps.get('hoovers_ip', {}).get(
                    vps.get('main_ipv4').replace('.', '-')) != 'valid':
            ips.append(vps.get('main_ipv4'))

    create_ansible_task(task_name, ips, [])


def test_https_multiple_thread(coll: Collection = coll_jiang):
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


def test_hoovers_multiple_thread(coll: Collection = coll_jiang,
                                 repeat: bool = False):
    queue = Queue()
    # start to thread
    for i in range(20):
        t = Thread(target=thread_task_hoovers, args=(queue, coll))
        t.setDaemon(True)
        t.start()
    for doc in coll.find({
        # 'hoovers': {'$ne': 'valid'}
    }):
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


def view_invalid_vps(coll: Collection = coll_jiang):
    invalid_ips = set()
    valid_ips = set()

    for vps in coll.find():
        ip = vps.get('main_ipv4')
        # if vps.get('hoovers_ip').get(ip.replace('.', '-')) != 'valid':
        if vps.get('https_ip').get(ip.replace('.', '-')) != 'valid' and \
                vps.get('hoovers_ip').get(ip.replace('.', '-')) != 'valid':
            invalid_ips.add(vps.get('main_ipv4'))
        else:
            valid_ips.add(vps.get('main_ipv4'))
            logger.debug('all valid main ipv4: {}'.format(vps.get('main_ipv4')))

    # for i in invalid_ips:
    #     coll.delete_one({'main_ipv4': i})

    logger.info('invalid: {}'.format(len(invalid_ips)))
    logger.info('valid: {}'.format(len(valid_ips)))
    return len(invalid_ips)


def delete_invalid_vps(coll: Collection,
                       vps_client: LinodeClient):
    delete_ips = []
    try:
        for vps in coll.find():
            if vps.get('hoovers_ip').get(
                    vps.get('main_ipv4').replace('.', '-')) != 'valid' and \
               vps.get('https_ip').get(
                   vps.get('main_ipv4').replace('.', '-')) != 'valid':

                logger.debug('delete vps : {}'.format(vps.get('main_ipv4')))
                res = vps_client.delete_vps(vps.get('vps_id'))
                if res:
                    logger.debug('delete vps success: {}'.format(
                        vps.get('main_ipv4')))
                    delete_ips.append(vps.get('main_ipv4'))
    finally:
        for i in delete_ips:
            logger.debug('delete vps from collection : '.format(i))
            coll.delete_one({'main_ipv4': i})


def delete_vps_from_coll():
    delete_vps = []
    for vps in coll_jiang.find():
        if vps.get('hoovers_ip').get(
                vps.get('main_ipv4').replace('.', '-')) != 'valid':
            delete_vps.append(vps)

    for i in delete_vps:
        logger.debug(i.get('main_ipv4'))
        coll_jiang.delete_one({'_id': i.get('_id')})


def vps_process(coll: Collection, vps_client: LinodeClient,
                task_name: str, letter: str = 'h'):
    # test proxy
    logger.info('start to test hoovers proxy')
    test_https_multiple_thread(coll)
    test_hoovers_multiple_thread(coll)
    test_https_multiple_thread(coll)
    test_hoovers_multiple_thread(coll)

    # view invalid vps
    while view_invalid_vps(coll):
        # break

        # delete invalid vps
        logger.info('start to delete invalid vps')
        delete_invalid_vps(coll, vps_client)

    # buy vps
    logger.info('start to buy vps')
    try:
        fill_vps(coll, vps_client, letter,
                 # region='eu-west-1a',
                 # number=150
                 )
    except IndexError:
        pass
    except Exception as exc:
        logger.debug(exc)
    logger.info('update collection message')
    fill_collection(coll, vps_client)
    # create task
    # create_task_with_vps(coll, task_name)


def fill_collection(coll: Collection = coll_jiang,
                    vps_client: LinodeClient = jiang):
    for vps in vps_client.get_all_vps():
        if vps.get('label').startswith('apollo'):
            coll.update_one({'main_ipv4': vps.get('main_ipv4')},
                            {'$set': vps}, upsert=True)


def total_zone(coll: Collection):
    zone = {}
    for vps in coll.find():
        region = vps.get('region')
        if region not in zone:
            zone[region] = {
                'valid': 0,
                'invalid': 0,
            }
        if vps.get('hoovers_ip', {}).get(
                vps.get('main_ipv4').replace('.', '-')) == 'valid':
            zone[region]['valid'] += 1
        else:
            zone[region]['invalid'] += 1
    pp.pprint(zone)
    # pp.plogger.debug(jiang.list_regions())


if __name__ == '__main__':
    pass
