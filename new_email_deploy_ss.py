from select_proxy.ss_privoxy_settings import coll
from select_proxy.ss_privoxy_settings import client
from select_proxy.ss_privoxy import directly_distribute_ports


def create_tencent_vps():
    coll_src = client['vps_management']['tencent_shadowsocks_service']
    ips = coll_src.distinct('ip')
    coll_dst = client['vps_management']['tencent_vps']
    for ip in ips:
        coll_dst.insert_one({'ipv4': [ip], 'main_ipv4': ip})


if __name__ == '__main__':
    # create_tencent_vps()
    directly_distribute_ports(coll)
