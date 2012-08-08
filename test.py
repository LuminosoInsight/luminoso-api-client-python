
import logging; logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

from luminoso_api import Account, Database
from luminoso_api.utils import get_session

def main():
    s = get_session()
    logger.info('getting database list')
    acct = Account('admin', s)
    dbs = acct.databases()
    for db in dbs:
        print "%s: %r" % (db, dbs[db]._meta)

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

def upload():
    s = get_session()
    acct = Account('admin', s)
    resp = acct.create_project('api-create-test-2')
    if resp is not None:
        print 'error: %s' % resp
        return
    db = Database('admin/api-create-test-2', 'api-create-test-2', s)
    docs = [{'text': 'Examples are a great source of inspiration',
             'title': 'example-1'},
            {'text': 'W3C specifications are habitually in BNF',
             'title': 'example-2'},
            {'text': 'W3C specifications are inscrutible',
             'title': 'example-3'},
           ]
    resp = db.upload_documents(docs)
    print repr(resp)

if __name__ == '__main__':
    #main()
    #relevance()
    upload()
