from pymongo import MongoClient
from datetime import datetime

date = str(datetime.today()).split()[0]
local_time = str(datetime.today()).split('.')[0]

client = MongoClient('mongodb://uri')
PROXY = {'https': 'https://ip:port', 'http': 'http://ip:port'}


URLS = [
    'http://www.hoovers.com/company-information/cs/company-'
    'profile.2yunion_development_ooo.79b2020b0b575a79.html',
    'http://www.hoovers.com/company-information/cs/revenue-'
    'financial.2you_sa.a63ecc1819605f99.html',
    'http://www.hoovers.com/company-information/company-search.html?'
    'nvcnt=76&nvloc=0&nvics=I812930L&sortDir=Descending&'
    'sort=CompanyName&maxitems=100&page=30',
    'http://www.hoovers.com/company-information/cs/'
    'marketing-lists.2you_sa.a63ecc1819605f99.html',
    'http://www.hoovers.com/company-information/company-search.html?'
    'nvcnt=76&nvloc=0&nvics=I812930L&sortDir=Descending&'
    'sort=CompanyName&maxitems=100&page=31',
    'http://www.hoovers.com/company-information/company-search.html'
]

USER_AGENTS = [
    'Mozilla/5.0 (X11; Linux x86_64) '
    'AppleWebKit/537.36 (KHTML, like Gecko) '
    'Chrome/57.0.2987.110 '
    'Safari/537.36',  # chrome
    'Mozilla/5.0 (X11; Linux x86_64) '
    'AppleWebKit/537.36 (KHTML, like Gecko) '
    'Chrome/61.0.3163.79 '
    'Safari/537.36',  # chrome
    # 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:55.0) '
    # 'Gecko/20100101 '
    # 'Firefox/55.0',  # firefox
    'Mozilla/5.0 (X11; Linux x86_64) '
    'AppleWebKit/537.36 (KHTML, like Gecko) '
    'Chrome/61.0.3163.91 '
    'Safari/537.36',  # chrome
    'Mozilla/5.0 (X11; Linux x86_64) '
    'AppleWebKit/537.36 (KHTML, like Gecko) '
    'Chrome/62.0.3202.89 '
    'Safari/537.36',  # chrome
    'Mozilla/5.0 (X11; Linux x86_64) '
    'AppleWebKit/537.36 (KHTML, like Gecko) '
    'Chrome/63.0.3239.108 '
    'Safari/537.36',  # chrome
]

LINODE_AUTH_KEYS = [
    # ssh public key
]
