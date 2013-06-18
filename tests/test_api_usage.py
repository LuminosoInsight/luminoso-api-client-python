import logging
import subprocess
import sys
import os

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

from luminoso_api import LuminosoClient
from luminoso_api.errors import LuminosoError
from luminoso_api.json_stream import open_json_or_csv_somehow

ROOT_CLIENT = None
RELOGIN_CLIENT = None
PROJECT = None
USERNAME = None

PROJECT_NAME = os.environ.get('USER', 'jenkins') + '-test'
PROJECT_ID = None
EXAMPLE_DIR = os.path.dirname(__file__) + '/examples'

ROOT_URL = 'http://localhost:5021/v4'

def fileno_monkeypatch(self):
    return sys.__stdout__.fileno()

import StringIO
StringIO.StringIO.fileno = fileno_monkeypatch


def setup():
    """
    Make sure we're working with a fresh database. Build a client for
    interacting with that database and save it as a global.
    """
    global ROOT_CLIENT, PROJECT, USERNAME, RELOGIN_CLIENT, PROJECT_ID
    user_info_str = subprocess.check_output('tellme lumi-test', shell=True)
    user_info = eval(user_info_str)
    USERNAME = user_info['username']

    ROOT_CLIENT = LuminosoClient.connect(ROOT_URL,
                                         username=USERNAME,
                                         password=user_info['password'])
    RELOGIN_CLIENT = LuminosoClient.connect(ROOT_URL,
                                            username=USERNAME,
                                            password=user_info['password'],
                                            auto_login=True)

    # check to see if the project exists
    projects = ROOT_CLIENT.get('projects/' + USERNAME)
    projdict = dict((proj['name'], proj['project_id']) for proj in projects)

    if PROJECT_NAME in projdict:
        logger.warn('The test database existed already. '
                    'We have to clean it up.')
        ROOT_CLIENT.delete('projects/' + USERNAME + '/' + projdict[PROJECT_NAME])

    # create the project and client
    logger.info("Creating project: " + PROJECT_NAME)
    logger.info("Existing projects: %r" % projdict.keys())
    creation = ROOT_CLIENT.post('projects/' + USERNAME, name=PROJECT_NAME)
    PROJECT_ID = creation['project_id']
    PROJECT = ROOT_CLIENT.change_path('projects/' + USERNAME + '/' + PROJECT_ID)
    PROJECT.get()


def test_noop():
    """
    Sometimes you just need to do nothing.
    """
    assert ROOT_CLIENT.get('ping') == 'pong'
    assert ROOT_CLIENT.post('ping') == 'pong'
    assert ROOT_CLIENT.put('ping') == 'pong'
    assert ROOT_CLIENT.delete('ping') == 'pong'


def test_paths():
    """
    Without interacting with the network, make sure our path logic works.
    """
    client1 = ROOT_CLIENT.change_path('foo')
    assert client1.url == ROOT_CLIENT.url + 'foo/'
    client2 = client1.change_path('bar')
    assert client2.url == ROOT_CLIENT.url + 'foo/bar/'
    client3 = client2.change_path('/baz')
    assert client3.url == ROOT_CLIENT.url + 'baz/'


def test_no_terms():
    """
    The project was just created, so it shouldn't have any terms in it.
    """
    assert PROJECT.get('terms') == []


def test_upload_and_wait_for():
    """
    Upload three documents and wait for the result.
    """
    docs = open_json_or_csv_somehow(EXAMPLE_DIR + '/example1.stream.json')
    job_id = PROJECT.upload('docs', docs, stage=False)
    assert isinstance(job_id, int), job_id
    job_result = PROJECT.wait_for(job_id)
    assert job_result['success'] is True


def test_post_with_parameters():
    """
    Test post with parameters via topics.
    """
    topics = PROJECT.get('topics')
    assert topics == []

    PROJECT.post('topics',
                 name='Example topic',
                 role='topic',
                 color='#aabbcc',
                 surface_texts=['Examples']
                 )

    result = PROJECT.get('topics')
    assert len(result) == 1
    topic = result[0]
    assert topic['name'] == 'Example topic'
    assert topic['surface_texts'] == ['Examples']
    assert topic['color'] == '#aabbcc'
    topic_id = topic['_id']

    topic2 = PROJECT.get('topics/id/%s' % topic_id)
    assert topic2 == topic, '%s != %s' % (topic2, topic)


def test_auto_login():
    """Test auto-login after 401 responses."""
    RELOGIN_CLIENT._session.auth._key_id = ''
    assert RELOGIN_CLIENT.get('ping') == 'pong'


def teardown():
    """
    Pack everything up, we're done.
    """
    if ROOT_CLIENT is not None:
        ROOT_CLIENT.delete('projects/' + USERNAME + '/' + PROJECT_ID)
        PROJECT = ROOT_CLIENT.change_path('projects/' + USERNAME + '/' + PROJECT_ID)
        try:
            got = PROJECT.get()
        except LuminosoError:
            # it should be an error, we just deleted the project
            return
        else:
            assert False, got
