
import logging; logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

from luminoso_api import Account, Database
from luminoso_api.utils import get_session

def main():
    s = get_session()
    logger.info('getting database list')
    acct = Account.accessible(s)[0]
    dbs = acct.databases()
    return dbs

def create():
    s = get_session()
    logger.info('creating database create-test')
    result = s.post('https://api.lumino.so/v2/admin/create-test/create_project/',
                    data={}).json
    print repr(result)

def relevance():
    s = get_session()
    db = Database('admin/Arisia', 'Arisia', s)
    relevance = db.get_relevance()
    print repr(relevance)

if __name__ == '__main__':
    dbs = main()
    print repr(dbs)
    for db in dbs:
        print db
