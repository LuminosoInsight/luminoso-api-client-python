
import logging; logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)

from luminoso_api import LuminosoClient

def main():
    result = LuminosoClient.connect().get('.list_dbs')
    print result
    return result

def create():
    client = LuminosoClient.connect('/admin/api-create-test-3')
    result = client.post('create_project')
    print result

def relevance():
    client = LuminosoClient.connect('/admin/api-create-test-6')
    relevance = client.get('get_relevance')
    print relevance

def upload():
    client = LuminosoClient.connect('/admin/api-create-test-6')
    print client.post('create_project')
    docs = [{'text': 'This is an example document.',
             'title': 'example-1'},
            {'text': 'Examples are a great source of inspiration.',
             'title': 'example-2'},
           ]
    resp = client.upload_documents(docs)
    print resp

def smoke_test():
    #main()
    relevance()
    #create()
    #upload()

if __name__ == '__main__':
    smoke_test()

