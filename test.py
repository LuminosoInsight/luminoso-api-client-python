
import logging; logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)

from luminoso_api import LuminosoClient

def list_dbs():
    result = LuminosoClient.connect().get('.list_dbs')
    print result
    return result

def create():
    client = LuminosoClient.connect('/admin/api-create-test-4')
    result = client.post('create_project')
    print result

def relevance():
    client = LuminosoClient.connect('/admin/api-create-test-4')
    relevance = client.get('get_relevance')
    print relevance

def upload():
    client = LuminosoClient.connect('/admin/api-create-test-4')
    print client.post('create_project')
    docs = [{'text': 'This is an example document.',
             'title': 'example-1'},
            {'text': 'Examples are a great source of inspiration.',
             'title': 'example-2'},
           ]
    resp = client.upload_documents(docs)
    print resp

def delete():
    client = LuminosoClient.connect('/admin/api-create-test-4')
    print client.delete('.delete')


def smoke_test():
    delete()
    list_dbs()
    create()
    upload()
    relevance()

if __name__ == '__main__':
    smoke_test()

