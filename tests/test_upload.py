from luminoso_api.v5_client import LuminosoClient
from luminoso_api.v5_upload import create_project_with_docs, BATCH_SIZE

from unittest.mock import patch
import pytest


BASE_URL = 'http://mock-api.localhost/api/v5/'
DOCS_TO_UPLOAD = [
    {'title': 'Document 1', 'text': 'Bonjour'},
    {'title': 'Document 2', 'text': 'Au revoir'},
]

DOCS_UPLOADED = [
    {'title': 'Document 1', 'text': 'Bonjour', 'metadata': []},
    {'title': 'Document 2', 'text': 'Au revoir', 'metadata': []},
]

REPETITIVE_DOC = {'title': 'Yadda', 'text': 'yadda yadda', 'metadata': []}


def _build_info_response(ndocs, language, done):
    """
    Construct the expected response when we get the project's info after
    requesting a build.
    """
    response = {
        'json': {
            'project_id': 'projid',
            'document_count': ndocs,
            'language': language,
            'last_build_info': {
                'number': 1,
                'start_time': 0.,
                'stop_time': None,
            },
        }
    }
    if done:
        response['json']['last_build_info']['success'] = True
        response['json']['last_build_info']['stop_time'] = 1.
    return response


def test_project_creation(requests_mock):
    """
    Test creating a project by mocking what happens when it is successful.
    """
    # First, configure what the mock responses should be:

    # The initial response from creating the project
    requests_mock.post(
        BASE_URL + 'projects/',
        json={
            'project_id': 'projid',
            'document_count': 0,
            'language': 'fr',
            'last_build_info': None,
        },
    )
    # Empty responses from further build steps
    requests_mock.post(BASE_URL + 'projects/projid/upload/', json={})
    requests_mock.post(BASE_URL + 'projects/projid/build/', json={})

    # Build status response, which isn't done yet the first time it's checked,
    # and is done the second time
    requests_mock.get(
        BASE_URL + 'projects/projid/',
        [
            _build_info_response(2, 'fr', done=False),
            _build_info_response(2, 'fr', done=True),
        ],
    )

    # Now run the main uploader function and get the result
    client = LuminosoClient.connect(BASE_URL, token='fake')
    with patch('time.sleep', return_value=None):
        response = create_project_with_docs(
            client,
            DOCS_TO_UPLOAD,
            language='fr',
            name='Projet test',
            progress=False,
        )

    # Test that the right sequence of requests happened
    history = requests_mock.request_history

    assert history[0].method == 'POST'
    assert history[0].url == BASE_URL + 'projects/'
    params = history[0].json()
    assert params['name'] == 'Projet test'
    assert params['language'] == 'fr'

    assert history[1].method == 'POST'
    assert history[1].url == BASE_URL + 'projects/projid/upload/'
    params = history[1].json()
    assert params['docs'] == DOCS_UPLOADED

    assert history[2].method == 'POST'
    assert history[2].url == BASE_URL + 'projects/projid/build/'
    assert history[2].json() == {}

    assert history[3].method == 'GET'
    assert history[3].url == BASE_URL + 'projects/projid/'
    assert history[4].method == 'GET'
    assert history[4].url == BASE_URL + 'projects/projid/'

    assert len(history) == 5
    assert response['last_build_info']['success']


def test_missing_text(requests_mock):
    """
    Test a project that fails to be created, on the client side, because a bad
    document is supplied.
    """
    # The initial response from creating the project
    requests_mock.post(
        BASE_URL + 'projects/',
        json={
            'project_id': 'projid',
            'document_count': 0,
            'language': 'en',
            'last_build_info': None,
        },
    )

    with pytest.raises(ValueError):
        client = LuminosoClient.connect(BASE_URL, token='fake')
        create_project_with_docs(
            client,
            [{'bad': 'document'}],
            language='en',
            name='Bad project test',
            progress=False,
        )


def test_pagination(requests_mock):
    """
    Test that we can create a project whose documents would be broken into
    multiple pages, and when we iterate over its documents, we correctly
    request all the pages.
    """
    # The initial response from creating the project
    requests_mock.post(
        BASE_URL + 'projects/',
        json={
            'project_id': 'projid',
            'document_count': 0,
            'language': 'fr',
            'last_build_info': None,
        },
    )
    # Empty responses from further build steps
    requests_mock.post(BASE_URL + 'projects/projid/upload/', json={})
    requests_mock.post(BASE_URL + 'projects/projid/build/', json={})

    ndocs = BATCH_SIZE + 2

    # Build status response, which isn't done yet the first or second time
    # it's checked, and is done the third time
    requests_mock.get(
        BASE_URL + 'projects/projid/',
        [
            _build_info_response(ndocs, 'fr', done=False),
            _build_info_response(ndocs, 'fr', done=False),
            _build_info_response(ndocs, 'fr', done=True),
        ],
    )
    # Now run the main uploader function and get the result
    client = LuminosoClient.connect(BASE_URL, token='fake')
    with patch('time.sleep', return_value=None):
        create_project_with_docs(
            client,
            [REPETITIVE_DOC] * (BATCH_SIZE + 2),
            language='fr',
            name='Projet test',
            progress=False,
        )

    # Test that the right sequence of requests happened, this time just as
    # a list of URLs
    history = requests_mock.request_history
    reqs = [(req.method, req.url) for req in history]
    assert reqs == [
        ('POST', BASE_URL + 'projects/'),
        ('POST', BASE_URL + 'projects/projid/upload/'),
        ('POST', BASE_URL + 'projects/projid/upload/'),
        ('POST', BASE_URL + 'projects/projid/build/'),
        ('GET', BASE_URL + 'projects/projid/'),
        ('GET', BASE_URL + 'projects/projid/'),
        ('GET', BASE_URL + 'projects/projid/'),
    ]
