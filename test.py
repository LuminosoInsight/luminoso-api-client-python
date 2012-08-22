import logging
import subprocess
import time
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

from luminoso_api import LuminosoClient, LuminosoAuthError

ROOT_CLIENT = None
PROJECT = None
USERNAME = None

PROJECT_NAME = 'test5'
ROOT_URL = 'http://localhost:5000/v3'

def error(obj):
    return obj.get('error')

def setup():
    global ROOT_CLIENT, PROJECT, USERNAME
    user_info_str = subprocess.check_output('tellme lumi-test', shell=True)
    user_info = eval(user_info_str)
    USERNAME = user_info['username']

    ROOT_CLIENT = LuminosoClient.connect(ROOT_URL,
        username=USERNAME,
        password=user_info['password'])

    # ensure that the project is deleted
    PROJECT = ROOT_CLIENT.change_path(USERNAME + '/projects/' + PROJECT_NAME)
    #PROJECT.delete()

    # create the project
    ROOT_CLIENT.post(USERNAME + '/projects', project=PROJECT_NAME)
    result = PROJECT.get()
    assert not error(result), result

def test_list_dbs():
    assert not error(ROOT_CLIENT.get(USERNAME + '/projects'))

def test_paths():
    client1 = ROOT_CLIENT.change_path('foo')
    assert client1.url == ROOT_CLIENT.url + 'foo/'
    client2 = client1.change_path('bar')
    assert client2.url == ROOT_CLIENT.url + 'foo/bar/'
    client3 = client2.change_path('/baz')
    assert client3.url == ROOT_CLIENT.url + 'baz/'

def test_empty_relevance():
    result = PROJECT.get('terms')
    assert error(result), result

def test_upload():
    docs = [
        {'text': 'This is an example',
         'title': 'example-1'},
        {'text': 'Examples are a great source of inspiration',
         'title': 'example-2'},
    ]
    assert not error(PROJECT.upload('docs', docs))
    assert not error(PROJECT.post('docs/calculate'))
    assert not error(PROJECT.get('docs/calculate'))
    PROJECT.wait_for_assoc()
    assert not error(PROJECT.get('terms'))

def teardown():
    ROOT_CLIENT.delete(USERNAME + '/projects/' + PROJECT_NAME)
    PROJECT = ROOT_CLIENT.change_path(USERNAME + '/projects/' + PROJECT_NAME)
    assert error(PROJECT.get())
