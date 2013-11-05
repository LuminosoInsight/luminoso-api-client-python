import logging
import subprocess
import sys
import os
import json
import uuid

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

from luminoso_api import LuminosoClient
from luminoso_api.errors import LuminosoError, LuminosoClientError
from luminoso_api.json_stream import open_json_or_csv_somehow
from nose.tools import eq_

ROOT_CLIENT = None
OAUTH_CLIENT = None
PROJECT = None
OAUTH_PROJECT = None
USERNAME = None
PASSWORD = None

PROJECT_NAME = os.environ.get('USER', 'jenkins') + '-test-' + str(uuid.uuid4())
PROJECT_ID = None
EXAMPLE_DIR = os.path.dirname(__file__) + '/examples'

#ROOT_URL = 'http://localhost:5021/v4'
ROOT_URL = 'http://erie.lumi:5022/v4'

def fileno_monkeypatch(self):
    return sys.__stdout__.fileno()

import StringIO
StringIO.StringIO.fileno = fileno_monkeypatch


def setup():
    """
    Make sure we're working with a fresh database. Build a client for
    interacting with that database and save it as a global.
    """
    global ROOT_CLIENT, OAUTH_CLIENT, PROJECT, OAUTH_PROJECT, \
        USERNAME, PASSWORD, PROJECT_ID
    user_info_str = subprocess.check_output('tellme -f json lumi-test',
                                            shell=True)
    user_info = json.loads(user_info_str)
    USERNAME = user_info['username']
    PASSWORD = user_info['password']

    ROOT_CLIENT = LuminosoClient.connect(ROOT_URL,
                                         username=USERNAME,
                                         password=user_info['password'])
    OAUTH_CLIENT = LuminosoClient.connect(ROOT_URL,
                                          username=USERNAME,
                                          password=user_info['password'],
                                          auth_method='oauth')

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
    OAUTH_PROJECT = OAUTH_CLIENT.change_path('projects/' + USERNAME + '/'
                                             + PROJECT_ID)


def test_noop():
    """
    Sometimes you just need to do nothing.
    """
    for client in [ROOT_CLIENT, OAUTH_CLIENT]:
        eq_(client.get('ping'), 'pong')
        eq_(client.post('ping'), 'pong')
        eq_(client.put('ping'), 'pong')
        eq_(client.delete('ping'), 'pong')


def test_documentation():
    """
    Test the get_raw method, and also the documentation endpoint, which is
    different because it doesn't require you to be logged in and therefore
    doesn't return a replacement session cookie.
    """
    for client in [ROOT_CLIENT, OAUTH_CLIENT]:
        assert client.get_raw('/').strip().startswith(
            'This API supports the following methods.')


def test_paths():
    """
    Without interacting with the network, make sure our path logic works.
    """
    client1 = ROOT_CLIENT.change_path('foo')
    eq_(client1.url, ROOT_CLIENT.url + 'foo/')
    client2 = client1.change_path('bar')
    eq_(client2.url, ROOT_CLIENT.url + 'foo/bar/')
    client3 = client2.change_path('/baz')
    eq_(client3.url, ROOT_CLIENT.url + 'baz/')


def test_no_assoc():
    """
    The project was just created, so it shouldn't let you get terms.
    """
    for proj_client in [PROJECT, OAUTH_PROJECT]:
        try:
            proj_client.get('terms')
            assert False, 'Should have failed with NO_ASSOC.'
        except LuminosoClientError as e:
            eq_(e.message['code'], 'NO_ASSOC')


def test_empty_string():
    """
    GET and PUT with parameters whose value is empty string.
    """
    for (proj_client, root_client) in [(PROJECT, ROOT_CLIENT),
                                       (OAUTH_PROJECT, OAUTH_CLIENT)]:
        # Change the project name
        name = proj_client.get()['name']
        eq_(name, PROJECT_NAME)
        proj_client.put(name='')
        name2 = proj_client.get()['name']
        eq_(name2, '')

        # Get project by name
        matches = root_client.get('projects', name='')
        assert any(p['project_id'] == PROJECT_ID and p['owner'] == USERNAME
                   for p in matches), matches

        # Change it back
        proj_client.put(name=PROJECT_NAME)


def test_upload_and_wait_for():
    """
    Upload three documents, recalculate, and wait for the result.
    """
    for proj_client in [PROJECT, OAUTH_PROJECT]:
        docs = list(open_json_or_csv_somehow(
                EXAMPLE_DIR + '/example1.stream.json'))
        doc_ids = proj_client.upload('docs', docs)
        assert isinstance(doc_ids, list), doc_ids
        assert len(doc_ids) == len(docs), doc_ids
        job_id = proj_client.post('docs/recalculate')
        job_result = proj_client.wait_for(job_id)
        assert job_result['success'] is True, job_result


def test_post_with_parameters():
    """
    Test post with parameters via topics.
    """
    for proj_client in [PROJECT, OAUTH_PROJECT]:
        topics = proj_client.get('topics')
        eq_(topics, [])

        proj_client.post('topics',
                         name='Example topic',
                         color='#aabbcc',
                         surface_texts=['Examples']
                         )

        result = proj_client.get('topics')
        assert len(result) == 1, result
        topic = result[0]
        eq_(topic['name'], 'Example topic')
        eq_(topic['surface_texts'], ['Examples'])
        eq_(topic['color'], '#aabbcc')
        topic_id = topic['_id']

        topic2 = proj_client.get('topics/id/%s' % topic_id)
        eq_(topic2, topic)

        proj_client.delete('topics/id/%s' % topic_id)
        no_topics = proj_client.get('topics')
        eq_(no_topics, [])


def test_auto_login():
    """Test auto-login after 401 responses."""
    relogin_client = LuminosoClient.connect(
        ROOT_URL, username=USERNAME, password=PASSWORD, auto_login=True)
    relogin_client._session.auth._key_id = ''
    assert relogin_client.get('ping') == 'pong'

    # TODO: set timeouts so this can be tested
    # oauth_relogin_client = LuminosoClient.connect(
    #     ROOT_URL, username=USERNAME, password=PASSWORD, auto_login=True,
    #     auth_method='oauth')
    # oauth_relogin_client._session.auth._token = oauth2.Token('', '')
    # assert oauth_relogin_client.get('ping') == 'pong'


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
