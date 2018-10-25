import random
from queue import Queue
from typing import Dict, Callable
from typing import Tuple

import requests
from pymongo.collection import Collection
from requests.exceptions import ProxyError

from settings import USER_AGENTS
from settings import URLS
from settings import date
from select_proxy import create_logger

logger = create_logger(__name__)

user_agent = random.choice(USER_AGENTS)
headers = {
    'Accept': 'text/html,application/xhtml+xml,'
              'application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Encoding': 'gzip, deflate, sdch, br',
    'Accept-Language': 'en-US, en; q=0.8',
    'User-Agent': user_agent,
}


def get_proxy_from_ip(ip: str) -> Dict:
    return {
        'http': 'http://{user}:{pwd}@{ip}:{port}'.format(
            user='socialbirddrg', pwd='kR0gt9UWQCP53qBV',
            ip=ip, port=31128
        ),
        'https': 'https://{user}:{pwd}@{ip}:{port}'.format(
            user='socialbirddrg', pwd='kR0gt9UWQCP53qBV',
            ip=ip, port=31128
        )
    }


def get_pub_proxy(ip: str) -> Dict:
    return {'http': 'http://{}'.format(ip), 'https': 'https://{}'.format(ip)}


def use_proxy(
        scheme: str,
        proxy: Dict,
        timeout: int,
        url: str = '{scheme}://httpbin.org',
        header: Dict = headers
) -> Tuple:
    """
    :param scheme:
    :param proxy:
    :param timeout:
    :param url:
    :param header:
    :return:
    """
    logger.debug('check proxy: {}'.format(proxy))
    try:
        response = requests.get(
            url.format(scheme=scheme),
            proxies=proxy,
            timeout=timeout,
            allow_redirects=False,
            headers=header
        )
    except ProxyError as exc:
        logger.debug(exc)
        # raise exc
        return 'invalid', 777
    except Exception as exc:
        logger.debug(exc)
        return 'timeout', 999
    else:
        if response.status_code != 200:
            # print('status_code: {}, proxy: {}'.format(
            #     response.status_code,
            #     proxy
            # ))
            # print(response.content.decode())
            return 'unexpected code', response.status_code
        logger.debug('valid {}: {}'.format(proxy, url))
        return 'valid', response.status_code


def callback_hoovers(coll: Collection, ip: str, status: str):
    coll.update_one(
        {'ipv4': ip},
        {'$set': {'hoovers_ip.{}'.format(ip.replace('.', '-')): status}}
    )


def callback_privoxy(coll: Collection, ip: str, status: str):
    coll.update_one(
        {'local_port': int(ip.split(':')[1])},
        {'$set': {'status': {date: status}}}
    )


def thread_task_hoovers(queue: Queue, coll: Collection,
                        proxy_func: Callable = get_proxy_from_ip,
                        callback: Callable = callback_hoovers):
    """
    :param queue: ip queue
    :param coll: source vps coll
    :param proxy_func: get proxy function
    :param callback:
    :return:
    """
    url = random.choice(URLS)
    # url = 'http://httpbin.org/ip'
    while True:
        ip = queue.get()
        scheme = 'http'
        proxy = proxy_func(ip)
        status, code = use_proxy(scheme, proxy, 10,
                                 url,
                                 headers)
        callback(coll, ip, status)
        queue.task_done()


def thread_task(queue: Queue, coll: Collection):
    while True:
        ip = queue.get()
        scheme = 'https'
        proxy = get_proxy_from_ip(ip)
        status, code = use_proxy(scheme, proxy, 4)
        coll.update_one({'ipv4': ip},

                        {'$set': {
                            'https_ip.{}'.format(ip.replace('.', '-')): status
                        }})
        queue.task_done()


if __name__ == '__main__':
    pass
