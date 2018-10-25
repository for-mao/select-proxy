from select_proxy.ss_privoxy import process_stop_container
from select_proxy.ss_privoxy_settings import coll
from select_proxy.ss_privoxy_settings import host
from select_proxy.ss_privoxy_settings import sleep_second


def main():
    process_stop_container(coll, host, sleep_second)


if __name__ == '__main__':
    main()
