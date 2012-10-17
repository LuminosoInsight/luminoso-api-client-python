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

PROJECT_NAME = os.environ.get('USER', 'jenkins') + '-test'
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
        ROOT_CLIENT.delete(USERNAME + '/projects', project=PROJECT_NAME)

    # create the project
    logger.info("Creating project: "+PROJECT_NAME)
    logger.info("Existing projects: %r" % projlist)
    ROOT_CLIENT.post(USERNAME + '/projects', project=PROJECT_NAME)
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
         'title': 'example-1',
         'date': 0},
        {'text': 'Examples are a great source of inspiration',
         'title': 'example-2',
         'date': 5},
        {'text': 'Great things come in threes',
         'title': 'example-3',
         'date': 20},
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

def test_terms():
    """Simple test of termstats"""
    terms = PROJECT.get('terms')
    assert len(terms)
    assert terms[0]['text'] != 'person'

def test_subset_addition():
    """Adding documents to subsets"""
    documents = PROJECT.get('docs', subset='__all__')
    docids = dict((doc['title'], doc['_id']) for doc in documents)
    ids = '["%s","%s"]' % (docids['example-1'], docids['example-3'])

    # Add two documents to "sample" subset
    job_id = PROJECT.post('docs/subset', subset='sample', ids=ids)
    PROJECT.wait_for(job_id)

    # Ensure that "sample" is now a subset.
    subsets = PROJECT.get()['subsets']
    subsets.sort()
    assert subsets == ['__all__', 'sample']

    # Ensure two documents and not the third are in that subset.
    sample_ids = PROJECT.get('docs/ids', subset='sample')
    assert docids['example-1'] in sample_ids
    assert docids['example-3'] in sample_ids
    assert docids['example-2'] not in sample_ids

    # Test termstats?

def test_csv_endpoints():
    """Test the three CSV-producing endpoints."""

    # Add another topic
    PROJECT.post('topics',
        name='Another example',
        role='topic',
        color='#aabbcc',
        surface_texts=['inspiration']
    )

    # Check topic-vs-topic correlations
    correlations = PROJECT.get_raw('topics/correlation')
    correlations = [line.split(',') for line in correlations.splitlines()]

    assert len(correlations) == 3
    assert correlations[0][1] == correlations[1][0]
    assert correlations[0][2] == correlations[2][0]
    assert .99 < float(correlations[1][1]) < 1
    assert .99 < float(correlations[2][2]) < 1
    
    # Check topic-vs-subset correlations
    topic_names = correlations[0][1:]
    correlations = PROJECT.get_raw('topics/subset_correlation')
    correlations = [line.split(',') for line in correlations.splitlines()]

    assert len(correlations) == 3
    assert correlations[0][1:] == topic_names
    assert correlations[1][0] == 'All Documents'
    assert correlations[2][0] == 'sample'

    # Check topic-by-timeline
    correlations = PROJECT.get_raw('topics/timeline_correlation')
    correlations = [line.split(',') for line in correlations.splitlines()]

    assert len(correlations) == 4
    assert set(correlations[0][1:]) == set(topic_names)
    assert float(correlations[1][1])

    # Better tests to ensure that the numbers are right?

def test_subset_removal():
    """Removing documents from subsets"""
    documents = PROJECT.get('docs', subset='__all__')
    docids = dict((doc['title'], doc['_id']) for doc in documents)

    # Remove one document from "sample".
    ids = '["%s"]' % docids['example-1']
    job_id = PROJECT.delete('docs/subset', subset='sample', ids=ids)
    PROJECT.wait_for(job_id)

    # Ensure that it is no longer in the subset (but the other is).
    sample_ids = PROJECT.get('docs/ids', subset='sample')
    assert docids['example-1'] not in sample_ids
    assert docids['example-3'] in sample_ids


def test_pipeline_crushing():
    """Overlord should kill pipelines on crash"""
    # The presence of "poison_pill" as a keyword will cause stage-two to assert
    # False.
    docs = [
        {'text': 'This is an example',
         'title': 'example-1',
         'date': 0},
        {'text': 'Examples are a great source of inspiration',
         'title': 'example-2',
         'date': 5},
        {'text': 'Great things come in threes',
         'title': 'example-3',
         'date': 20,
         'poison_pill': True},
    ]
    job_id = PROJECT.upload('docs', docs)
    job_result = PROJECT.wait_for(job_id)
    assert job_result['success'] is False

def teardown():
    """
    Pack everything up, we're done.
    """
    if ROOT_CLIENT is not None:
        ROOT_CLIENT.delete(USERNAME + '/projects', project=PROJECT_NAME)
        PROJECT = ROOT_CLIENT.change_path(USERNAME + '/projects/' + PROJECT_NAME)
        try:
            got = PROJECT.get()
        except LuminosoError:
            # it should be an error, we just deleted the project
            return
        else:
            assert False, got
