from select_proxy.ss_privoxy import process_start_container
from select_proxy.ss_privoxy_settings import coll
from select_proxy.ss_privoxy_settings import host
from select_proxy.ss_privoxy_settings import sleep_second
from select_proxy.ss_privoxy_settings import limit


def main():
    process_start_container(coll, host, sleep_second, limit)


if __name__ == '__main__':
    main()
