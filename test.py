import logging
import subprocess
import sys
import os

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

from luminoso_api import LuminosoClient

ROOT_CLIENT = None
PROJECT = None
USERNAME = None

PROJECT_NAME = os.environ['USER'] + '-test'
ROOT_URL = 'http://localhost:5000/v3'

def fileno_monkeypatch(self):
    return sys.__stdout__.fileno()

import StringIO
StringIO.StringIO.fileno = fileno_monkeypatch

def error(obj):
    return obj.get('error')

def setup():
    """
    Make sure we're working with a fresh database. Build a client for
    interacting with that database and save it as a global.
    """
    global ROOT_CLIENT, PROJECT, USERNAME
    user_info_str = subprocess.check_output('tellme lumi-test', shell=True)
    user_info = eval(user_info_str)
    USERNAME = user_info['username']

    ROOT_CLIENT = LuminosoClient.connect(ROOT_URL,
        username=USERNAME,
        password=user_info['password'])

    # check to see if the project exists; also create the client we'll use
    projlist = ROOT_CLIENT.get(USERNAME + '/projects')
    PROJECT = ROOT_CLIENT.change_path(USERNAME + '/projects/' + PROJECT_NAME)

    assert not error(projlist)
    if USERNAME + '_' + PROJECT_NAME in projlist['result']:
        logger.warn('The test database existed already. We have to clean it up.')
        PROJECT.delete()

    # create the project
    ROOT_CLIENT.post(USERNAME + '/projects', project=PROJECT_NAME)
    result = PROJECT.get()
    assert not error(result), result

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

def test_empty_relevance():
    """
    The project was just created, so it shouldn't have any terms in it.
    """
    result = PROJECT.get('terms')
    assert error(result), result

def test_upload():
    """
    Upload three documents, commit them, and wait for the commit.

    Check afterward to ensure that the terms are no longer empty.
    """
    docs = [
        {'text': 'This is an example',
         'title': 'example-1'},
        {'text': 'Examples are a great source of inspiration',
         'title': 'example-2'},
        {'text': 'Great things come in threes',
         'title': 'example-3'},
    ]
    job_id = PROJECT.upload('docs', docs)['result']
    job_id_2 = PROJECT.post('docs/calculate')['result']
    assert job_id_2 > job_id
    PROJECT.wait_for(job_id_2)
    assert not error(PROJECT.get('terms'))

def test_topics():
    """
    Manipulate some topics.

    One thing we check is that a topic is equal after a round-trip to the
    server.
    """
    topics = PROJECT.get('topics')
    assert topics['result'] == []

    PROJECT.post('topics',
        name='Example topic',
        role='topic',
        color='#aabbcc',
        surface_texts=['Examples']
    )

    topics = PROJECT.get('topics')
    result = topics['result']
    assert len(result) == 1
    topic = result[0]
    assert topic['name'] == 'Example topic'
    assert topic['surface_texts'] == ['Examples']
    assert topic['color'] == '#aabbcc'
    topic_id = topic['_id']

    topic2 = PROJECT.get('topics/id/%s' % topic_id)['result']
    assert topic2 == topic, '%s != %s' % (topic2, topic)

def teardown():
    """
    Pack everything up, we're done.
    """
    if ROOT_CLIENT is not None:
        ROOT_CLIENT.delete(USERNAME + '/projects/' + PROJECT_NAME)
        PROJECT = ROOT_CLIENT.change_path(USERNAME + '/projects/' + PROJECT_NAME)
        assert error(PROJECT.get())
