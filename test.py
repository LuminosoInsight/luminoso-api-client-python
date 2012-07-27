
import requests
from luminoso_api.auth import LuminosoAuth
import logging; logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

from getpass import getpass
import os

def main():
    logger.info('creating LuminosoAuth object')
    username = os.environ['USER']
    password = getpass('Password for %s: ' % username)
    auth = LuminosoAuth(username, password)

    logger.info('creating requests session')
    s = requests.session(auth=auth, verify=False)

    logger.info('getting database list')
    dbs = s.get('https://api.lumino.so/v2/default/.list_dbs/').json
    return dbs

if __name__ == '__main__':
    dbs = main()
    print repr(dbs)
    for db in dbs:
        print db
