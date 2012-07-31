
import requests
from luminoso_api.auth import LuminosoAuth
import logging; logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

from getpass import getpass
import os

def get_session():
    logger.info('creating LuminosoAuth object')
    username = os.environ['USER']
    password = getpass('Password for %s: ' % username)
    auth = LuminosoAuth(username, password)

    logger.info('creating requests session')
    return requests.session(auth=auth, verify=False)

def main():
    s = get_session()
    logger.info('getting database list')
    dbs = s.get('https://api.lumino.so/v2/default/.list_dbs/').json
    return dbs

def create():
    s = get_session()
    logger.info('creating database create-test')
    result = s.post('https://api.lumino.so/v2/admin/create-test/create_project/',
                    data={}).json
    print repr(result)

if __name__ == '__main__':
    dbs = main()
    print repr(dbs)
    for db in dbs:
        print db
