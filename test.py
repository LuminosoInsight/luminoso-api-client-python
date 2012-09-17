import logging
import subprocess
import sys
import os
from nose.tools import raises

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

from luminoso_api import LuminosoClient
from luminoso_api.errors import LuminosoAPIError, LuminosoError

ROOT_CLIENT = None
PROJECT = None
USERNAME = None

PROJECT_NAME = os.environ['USER'] + '-test'
ROOT_URL = 'http://localhost:5000/v3'

def fileno_monkeypatch(self):
    return sys.__stdout__.fileno()

import StringIO
StringIO.StringIO.fileno = fileno_monkeypatch

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
    projects = ROOT_CLIENT.get(USERNAME + '/projects')
    projlist = [proj['name'] for proj in projects]
    PROJECT = ROOT_CLIENT.change_path(USERNAME + '/projects/' + PROJECT_NAME)

    if PROJECT_NAME in projlist:
        logger.warn('The test database existed already. We have to clean it up.')
        PROJECT.delete()

    # create the project
    logger.info("Creating project: "+PROJECT_NAME)
    logger.info("Existing projects: %r" % projlist)
    ROOT_CLIENT.post(USERNAME + '/projects', project=PROJECT_NAME)
    PROJECT.get()

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

@raises(LuminosoAPIError)
def test_empty_relevance():
    """
    The project was just created, so it shouldn't have any terms in it.
    """
    PROJECT.get('terms')

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
    job_id = PROJECT.upload('docs', docs)
    job_id_2 = PROJECT.post('docs/calculate')
    assert job_id_2 > job_id
    PROJECT.wait_for(job_id_2)
    assert PROJECT.get('terms')

def test_topics():
    """
    Manipulate some topics.

    One thing we check is that a topic is equal after a round-trip to the
    server.
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

def teardown():
    """
    Pack everything up, we're done.
    """
    if ROOT_CLIENT is not None:
        ROOT_CLIENT.delete(USERNAME + '/projects/' + PROJECT_NAME)
        PROJECT = ROOT_CLIENT.change_path(USERNAME + '/projects/' + PROJECT_NAME)
        try:
            got = PROJECT.get()
        except LuminosoError:
            # it should be an error, we just deleted the project
            return
        else:
            assert False, got
