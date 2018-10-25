from os import path
from pprint import PrettyPrinter
from queue import Queue
from threading import Thread
from typing import Dict

from jinja2 import Template
from pymongo.collection import Collection
from testinfra import get_host

from create_ansible_task import create_ansible_task
from settings_tokens import VULTR_API_TOKEN
from utils.thread_task import thread_task
from utils.thread_task import thread_task_hoovers
from utils.VPSClient import VultrClient
from select_proxy import create_logger

logger = create_logger(__name__)
pp = PrettyPrinter(indent=4)
vultr = VultrClient('sun', VULTR_API_TOKEN['sun'])


def get_regions(coll: Collection, vps_client: VultrClient) -> Dict:
    # if not coll.find_one():
    return {i: 0 for i in vps_client.list_regions()}
    #
    # regions = {}
    # print(coll.full_name)
    # for vps in coll.find():
    #     dcid = vps['meta']['DCID']
    #     if dcid not in regions:
    #         regions[dcid] = 0
    #     regions[dcid] += 1
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
    if not coll.find_one():
        return 0
    s = list(map(lambda x: int(x[8:]), coll.distinct('label')))
    s.sort()
    return s[-1] + 1 if s else letter


def fill_vps(coll: Collection, vps_client: VultrClient, letter: str = 'r'):
    # images id: 21669205
    # plan id: s-1vcpu-1gb
    ssh_keys = {'jiang': '5a72df77c05a0,5867453fdc747,58ddb309dfd6e',
                'sun': '5a72df4d9c615,59c2227b038c8,5975ad13beead'}
    regions = get_regions(coll, vps_client)
    number = get_next_letter(coll, letter)
    for i in range(number + 1, number + 1000):
        min_region = get_min_key(regions)
        kwargs = {
            'region': min_region,
            'plan': 201,
            'image': 215,
            'label': 'apollo-z{:02}'.format(i),
            'tag': 'apollo',
            'ssh_keys': ssh_keys[vps_client.account],
        }
        logger.debug('create vultr vps: {}'.format(kwargs.get('label')))
        res = vps_client.create_vps(**kwargs)
        if res:
            regions[min_region] += 1
            logger.debug('create success')
        else:
            logger.debug('create failed')
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


def inspect_https_multiple_thread(coll: Collection):
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


def inspect_hoovers_multiple_thread(coll: Collection):
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
        for ip in filter(
                # bool,
                lambda x: doc.get(
                    'hoovers_ip', {}).get(x.replace('.', '-')) != 'valid',
                doc.get('ipv4')
        ):
            queue.put(ip)
    # await task done
    queue.join()


def view_invalid_vps(coll: Collection):
    invalid_ips = set()
    valid_ips = set()

    for vps in coll.find():
        ip = vps.get('main_ipv4')
        if vps.get('https_ip').get(ip.replace('.', '-')) != 'valid' and \
                vps.get('hoovers_ip').get(ip.replace('.', '-')) != 'valid':
            # if vps.get('hoovers_ip').get(ip.replace('.', '-')) != 'valid':
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
                       vps_client: VultrClient):
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
                    logger.debug(
                        'delete vps success: {}'.format(vps.get('main_ipv4'))
                    )
                    delete_ips.append(vps.get('main_ipv4'))
    except Exception:
        pass
    finally:
        for i in delete_ips:
            logger.debug('delete vps from collection :', i)
            coll.delete_one({'main_ipv4': i})


def vps_process(coll: Collection, vps_client: VultrClient,
                task_name: str, letter: str = 'h'):
    # test proxy
    inspect_https_multiple_thread(coll)
    inspect_hoovers_multiple_thread(coll)
    inspect_https_multiple_thread(coll)
    inspect_hoovers_multiple_thread(coll)

    # view invalid vps
    while view_invalid_vps(coll):
        # break
        # delete invalid vps
        delete_invalid_vps(coll, vps_client)

    # buy vps
    try:
        fill_vps(coll, vps_client, letter)
    except IndexError:
        pass
    logger.info('update collection message')
    fill_collection(coll, vps_client)
    # create task
    create_task_with_vps(coll, task_name)


def fill_collection(coll: Collection,
                    vps_client: VultrClient):
    for vps in vps_client.get_all_vps():
        if vps.get('label').startswith('apollo'):
            coll.update_one({'main_ipv4': vps.get('main_ipv4')},
                            {'$set': vps}, upsert=True)


# ==============================================================================
def view_invalid_ip_number(coll: Collection) -> int:
    # coll = client['vps_management']['apollo']
    invalid_ips = set()
    valid_ips = set()

    for vps in coll.find():
        for ip in filter(lambda x: x != vps.get('main_ipv4'), vps.get('ipv4')):
            if vps.get('hoovers_ip').get(ip.replace('.', '-')) != 'valid':
                invalid_ips.add(vps.get('main_ipv4'))
                break
        else:
            valid_ips.add(vps.get('main_ipv4'))
            logger.debug('all valid main ipv4: {}'.format(vps.get('main_ipv4')))

    logger.info('invalid: {}'.format(len(invalid_ips)))
    logger.info('valid: {}'.format(len(valid_ips)))
    return len(invalid_ips)


def delete_invalid_ip(coll: Collection, vps_client: VultrClient):
    for vps in coll.find(no_cursor_timeout=True):
        ipv4 = vps.get('ipv4')
        for ip in list(filter(lambda x: x != vps.get('main_ipv4'),
                              vps.get('ipv4'))):
            # exclude valid ip and handle invalid ip
            if vps.get('hoovers_ip').get(ip.replace('.', '-')) == 'valid':
                continue

            logger.debug('delete ip: {}'.format(ip))
            res = vps_client.delete_ipv4(vps.get('vps_id'), ip)
            # success delete ip
            if res:
                logger.debug('success delete ip: {}'.format(ip))
                ipv4.remove(ip)
        # finally update ipv4
        else:
            coll.update_one({'_id': vps['_id']}, {'$set': {'ipv4': ipv4}})


def append_ipv4(coll: Collection, vps_client: VultrClient) -> int:
    count = 0
    # ipv4_number: 3
    for vps in coll.find(no_cursor_timeout=True):
        for i in range(3 - len(vps.get('ipv4'))):
            logger.debug('main ip: {} create ipv4'.format(vps.get('main_ipv4')))
            try:
                res = vps_client.create_ipv4(vps.get('vps_id'))
            except Exception as exc:
                logger.debug(exc)
                pass
            else:
                count += 1
                logger.debug(res)
                if res:
                    coll.update_one({'_id': vps.get('_id')},
                                    {'$set': {'reboot': True,
                                              'change_interfaces': False}})
                else:
                    break
    return count


def update_ipv4(coll: Collection, vps_client: VultrClient):
    for vps in coll.find(
            {'reboot': True},
            no_cursor_timeout=True):
        logger.debug('[ipv4 update] main ip: {}'.format(vps.get('main_ipv4')))
        ips = vps_client.query_ipv4(vps.get('vps_id'))
        if ips:
            ipv4 = [i.get('ip') for i in filter(
                lambda x: x.get('type') != 'private', ips
            )]
            logger.debug(
                'update success {} --> {}'.format(vps.get('ipv4'), ipv4))
            coll.update_one({'_id': vps.get('_id')},
                            {'$set': {'ipv4': ipv4}})
        else:
            logger.debug('update fail >>>>>>>>>>>>>>>')


def change_interfaces_task(queue: Queue, coll: Collection, template: Template):
    while True:
        doc = queue.get()
        ip = doc.get('main_ipv4')
        logger.debug('check status: {}'.format(ip))
        host = get_host('ssh://root@{ip}:33301'.format(ip=ip),
                        ssh_identity_file='~/.ssh/id_rsa_grammy_jiang_old')
        logger.debug('config interfaces: {}'.format(ip))
        ips = doc.get('ipv4')
        ips.remove(doc.get('main_ipv4'))
        content = template.render(ips=ips)
        cmd = host.run(
            "echo -e '{}' > /etc/network/interfaces".format(content))
        if cmd.rc == 0:
            coll.update_one({'_id': doc.get('_id')},
                            {'$set': {'change_interfaces': True}})
            for i in range(len(ips)):
                cmd = host.run(
                    'ifdown ens3:{} && ifup ens3:{}'.format(i, i))
            if cmd.rc == 0:
                logger.debug('output: {}'.format(cmd.stdout))
                logger.debug('{} interfaces: ok'.format(doc.get('main_ipv4')))
            else:
                logger.debug('{} {}'.format(cmd.stdout, cmd.stderr))

        else:
            logger.debug('{} {}'.format(cmd.stdout, cmd.stderr))
        queue.task_done()


def change_interfaces(coll: Collection) -> int:
    count = 0
    # ../docs/template_interfaces
    file_path = path.abspath(path.join(__file__, path.pardir,
                                       path.pardir, 'docs',
                                       'template_interfaces'))
    f = open(file_path)
    template = Template(f.read())
    queue = Queue()
    f.close()
    for i in range(20):
        t = Thread(target=change_interfaces_task, args=(queue, coll, template))
        t.setDaemon(True)
        t.start()

    for doc in coll.find({'reboot': True, 'change_interfaces': False},
                         no_cursor_timeout=True):
        queue.put(doc)
        count += 1

    queue.join()

    return count


def reboot(coll: Collection, vps_client: VultrClient) -> int:
    # reboot
    count = 0
    for vps in coll.find(no_cursor_timeout=True):
        if vps.get('reboot') and vps.get('change_interfaces'):
            count += 1
            logger.debug('main ip: {} reboot'.format(vps.get('main_ipv4')))
            try:
                res = vps_client.reboot(vps.get('vps_id'))
            except Exception as exc:
                logger.debug(exc)
                continue
            else:
                logger.debug(res)
                if not res:
                    continue
                coll.update_one({'_id': vps.get('_id')},
                                {'$set': {'reboot': False}})
    return count


def apollo_with_ip(coll: Collection, task_name: str):
    ips = []
    for vps in coll.find({'change_interfaces': True}):
        ips.append(vps.get('main_ipv4'))
    create_ansible_task(task_name, ips, [])
    coll.update_many({}, {'$set': {'change_interfaces': False}})


def ip_process(coll: Collection, vps_client: VultrClient, task_name: str):
    logger.info('=================test ip==================')
    # inspect_https_multiple_thread()
    # inspect_https_multiple_thread()
    # inspect_hoovers_multiple_thread(coll)
    # inspect_hoovers_multiple_thread(coll)
    logger.info('=================start delete all invalid ip================')
    # delete all invalid
    # while view_invalid_ip_number(coll):
    #     try:
    #         delete_invalid_ip(coll, vps_client)
    #     except Exception as exc:
    #         logger.debug(exc)
    logger.info('=================start fill ip=======================')

    # fill_ipv4 and update ipv4
    while append_ipv4(coll, vps_client):
        try:
            update_ipv4(coll, vps_client)
        except Exception as exc:
            logger.debug(exc)

    logger.info('=================config network======================')
    for i in range(4):
        change_interfaces(coll)

    logger.info('====================reboot=======================')
    while reboot(coll, vps_client):
        pass
    logger.info('===================create ansible task======================')
    # apollo_with_ip(coll, task_name)  # create ansible task


if __name__ == '__main__':
    f_path = path.abspath(path.join(__file__, path.pardir,
                                    path.pardir, 'docs',
                                    'template_interfaces'))
    logger.debug(path.exists(f_path))
    pass
