from select_proxy.ss_privoxy import process_test_hoovers
from select_proxy.ss_privoxy_settings import coll
from select_proxy.ss_privoxy_settings import sleep_second


def main():
    process_test_hoovers(coll, sleep_second)


if __name__ == '__main__':
    main()
