from select_proxy.ss_privoxy_settings import vps_client
from select_proxy.ss_privoxy_settings import coll
from select_proxy.ss_privoxy_settings import sleep_second
from select_proxy.ss_privoxy import process_buy_vps


def main():
    process_buy_vps(vps_client, coll, sleep_second)


if __name__ == '__main__':
    main()
