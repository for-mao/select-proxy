from select_proxy.ss_privoxy import process_create_compose
from select_proxy.ss_privoxy_settings import coll
from select_proxy.ss_privoxy_settings import sleep_second


def main():
    process_create_compose(coll, sleep_second)


if __name__ == '__main__':
    main()
