import logging
import subprocess
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

from luminoso_api import LuminosoClient, LuminosoAuthError

ROOT_CLIENT = None
PROJECT = None
USERNAME = None

def not_error(obj):
    return obj.get('result')

def error(obj):
    return obj.get('error')

def setup():
    global ROOT_CLIENT, PROJECT, USERNAME
    user_info_str = subprocess.check_output('tellme lumi-test', shell=True)
    user_info = eval(user_info_str)
    USERNAME = user_info['username']

    ROOT_CLIENT = LuminosoClient.connect('/',
        username=USERNAME,
        password=user_info['password'])

    # ensure that the project is deleted
    PROJECT = ROOT_CLIENT.change_path(USERNAME + '/projects/test3')
    #PROJECT.delete()

    # create the project
    ROOT_CLIENT.post(USERNAME + '/projects', project='test3')
    assert not_error(PROJECT.get())

def test_list_dbs():
    assert not_error(ROOT_CLIENT.get(USERNAME + '/projects'))

def test_paths():
    client1 = ROOT_CLIENT.change_path('snoop')
    assert client1.url == ROOT_CLIENT.url + 'snoop/'
    client2 = client1.change_path('dogg')
    assert client2.url == ROOT_CLIENT.url + 'snoop/dogg/'
    client3 = client2.change_path('/snoop/lion')
    assert client3.url == ROOT_CLIENT.url + 'snoop/lion/'

def test_relevance():
    assert not_error(PROJECT.get('terms'))

def teardown():
    ROOT_CLIENT.delete(USERNAME + '/projects/test3')
    PROJECT = ROOT_CLIENT.change_path(USERNAME + '/projects/test3')
    try:
        PROJECT.get()
        raise ValueError("Getting a deleted database should have failed")
    except LuminosoAuthError:
        pass

#def upload():
#    s = get_session()
#    acct = Account('admin', s)
#    resp = acct.create_project('api-create-test-2')
#    if resp is not None:
#        print 'error: %s' % resp
#        return
#    db = Database('admin/api-create-test-2', 'api-create-test-2', s)
#    docs = [{'text': 'Examples are a great source of inspiration',
#             'title': 'example-1'},
#            {'text': 'W3C specifications are habitually in BNF',
#             'title': 'example-2'},
#            {'text': 'W3C specifications are inscrutible',
#             'title': 'example-3'},
#           ]
#    resp = db.upload_documents(docs)
#    print repr(resp)
