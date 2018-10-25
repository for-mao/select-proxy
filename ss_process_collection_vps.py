from select_proxy.ss_privoxy import process_collection_vps
from select_proxy.ss_privoxy_settings import coll
from select_proxy.ss_privoxy_settings import vps_client
from select_proxy.ss_privoxy_settings import sleep_second


def main():
    process_collection_vps(vps_client, coll, sleep_second)


if __name__ == '__main__':
    main()
