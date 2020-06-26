from luminoso_api.v5_client import LuminosoClient, get_root_url
from luminoso_api.errors import (
    LuminosoClientError, LuminosoServerError, LuminosoError,
    LuminosoTimeoutError
)

import pytest
import requests
import sys

BASE_URL = 'http://mock-api.localhost/api/v5/'


def test_paths():
    """
    Test creating a client and navigating to various paths with sub-clients.
    """
    client = LuminosoClient.connect(BASE_URL, token='fake')

    client_copy = client.client_for_path('first_path')
    assert client.url == BASE_URL
    assert client_copy.url == BASE_URL + 'first_path/'

    # Paths are relative to the client's URL; paths with slashes in front are
    # absolute.
    assert (
        client_copy.client_for_path('subpath').url
        == BASE_URL + 'first_path/subpath/'
    )
    assert (
        client_copy.client_for_path('/second_path').url
        == BASE_URL + 'second_path/'
    )

    # Similarly, test get_root_url
    with pytest.raises(ValueError):
        get_root_url('not.good.enough/api/v5')

    assert (
        get_root_url('https://daylight.luminoso.com/', warn=False)
        == 'https://daylight.luminoso.com/api/v5'
    )
    assert (
        get_root_url('http://daylight.luminoso.com/api/v5/who/cares?blaah')
        == 'http://daylight.luminoso.com/api/v5'
    )


# The test cases that mock HTTP responses depend on the 'requests-mock' pytest
# plugin, which can be installed with 'pip install requests-mock', or by using
# a Python packaging mechanism for installing the test dependencies of a package.
# (No such mechanism is standardized as of November 2018.)
#
# pytest plugins are passed in as an argument to the test function, and which
# plugin to use is specified by the name of the argument.

def test_mock_requests(requests_mock):
    """
    Test the way that we make GET, POST, PUT, and DELETE requests using the
    correspondingly-named methods of the client.
    """
    project_list = [{'name': 'Example project'}]

    # Set up the mock URLs that should respond
    requests_mock.get(BASE_URL + 'projects/', json=project_list)
    requests_mock.post(BASE_URL + 'projects/', json={})
    requests_mock.put(BASE_URL + 'projects/projid/', json={})
    requests_mock.delete(BASE_URL + 'projects/projid/', json={})

    client = LuminosoClient.connect(BASE_URL, token='fake')
    response = client.get('projects')
    assert response == project_list

    # Check that we sent the auth token in the request headers
    assert requests_mock.last_request.headers['Authorization'] == 'Token fake'

    client2 = client.client_for_path('projects')
    response = client2.get()
    assert response == project_list
    assert requests_mock.last_request.headers['Authorization'] == 'Token fake'
    # Okay, that's enough testing of the auth header

    # Test different kinds of requests with parameters
    response = client2.get(param='value')
    assert response == project_list
    assert requests_mock.last_request.qs == {'param': ['value']}

    client2.post(param='value')
    assert requests_mock.last_request.method == 'POST'
    assert requests_mock.last_request.json() == {'param': 'value'}

    client2.put('projid', param='value')
    assert requests_mock.last_request.method == 'PUT'
    assert requests_mock.last_request.json() == {'param': 'value'}

    client2.delete('projid')
    assert requests_mock.last_request.method == 'DELETE'


def test_failing_requests(requests_mock):
    requests_mock.get(BASE_URL + 'bad/', status_code=404)
    requests_mock.get(BASE_URL + 'fail/', status_code=500)
    client = LuminosoClient.connect(BASE_URL, token='fake')

    with pytest.raises(LuminosoClientError):
        client.get('bad')

    with pytest.raises(LuminosoServerError):
        client.get('fail')

# Test that passing the timeout value has no impact on a normal request
def test_timeout_not_timing_out(requests_mock):
    requests_mock.post(BASE_URL + 'projects/', json={})
    client = LuminosoClient.connect(BASE_URL, token='fake', timeout=2)
    client = client.client_for_path('projects')
    client.post(param='value')
    assert requests_mock.last_request.method == 'POST'
    assert requests_mock.last_request.json() == {'param': 'value'}

# Test that passing the timeout and it timing out raises the right error
def test_timeout_actually_timing_out(requests_mock):
    requests_mock.post(BASE_URL + 'projects/',
                       exc=requests.exceptions.ConnectTimeout)
    client = LuminosoClient.connect(BASE_URL, token='fake', timeout=2)
    client = client.client_for_path('projects')
    try:
        client.post(param='value')
    except LuminosoTimeoutError:
        pass

# The logic in wait_for_build() and wait_for_sentiment_build() gets a little
# complex, so we test that logic more thoroughly here.

def _last_build_infos_to_mock_returns(last_builds):
    """
    Helper function for testing waiting for a build.  Turns a series of
    last_build_info dictionaries into a list suitable for returning
    sequentially from requests_mock.
    """
    return [{'json': {'last_build_info': build_info}}
            for build_info in last_builds]


def test_wait_for_build(requests_mock):
    project_url = BASE_URL + 'projects/pr123456/'
    client = LuminosoClient.connect(project_url, token='fake')

    # A somewhat pared-down representation of what a project record's
    # `last_build_info` field looks like in various states
    build_running = {'start_time': 1590000000.0, 'stop_time': None,
                     'sentiment': {}}
    build_failed = {'start_time': 1590000000.0, 'stop_time': 1590000001.0,
                    'sentiment': {}, 'success': False}
    build_succeeded = {'start_time': 1590000000.0, 'stop_time': 1590000001.0,
                       'sentiment': {}, 'success': True}

    # If there is no build: error
    requests_mock.get(project_url, json={'last_build_info': {}})
    with pytest.raises(ValueError, match='not building'):
        client.wait_for_build()

    # If the build succeeds: the project's last build info
    requests_mock.get(
        project_url,
        _last_build_infos_to_mock_returns(
            [build_running, build_running, build_succeeded]
        )
    )
    result = client.wait_for_build(interval=.0001)
    assert result == build_succeeded

    # If the build fails: error with the project's last build info
    requests_mock.get(
        project_url,
        _last_build_infos_to_mock_returns([build_running, build_failed])
    )
    with pytest.raises(LuminosoError) as e:
        client.wait_for_build(interval=.0001)
    assert e.value.args == (build_failed,)


def test_wait_for_sentiment_build(requests_mock):
    project_url = BASE_URL + 'projects/pr123456/'
    client = LuminosoClient.connect(project_url, token='fake')

    # A somewhat pared-down representation of what a project record's
    # `last_build_info` field looks like in various states, including
    # the sentiment build
    build_running = {'start_time': 1590000000.0, 'stop_time': None,
                     'sentiment': {'start_time': None, 'stop_time': None}}
    build_failed = {'start_time': 1590000000.0, 'stop_time': 1590000001.0,
                    'sentiment': {'start_time': None, 'stop_time': None},
                    'success': False}
    build_succeeded = {'start_time': 1590000000.0,
                       'stop_time': 1590000001.0,
                       'sentiment': {'start_time': None, 'stop_time': None},
                       'success': True}
    sentiment_running = {'start_time': 1590000000.0, 'stop_time': 1590000001.0,
                         'sentiment': {'start_time': 1590000002.0,
                                       'stop_time': None},
                         'success': True}
    sentiment_failed = {'start_time': 1590000000.0, 'stop_time': 1590000001.0,
                        'sentiment': {'start_time': 1590000002.0,
                                      'stop_time': 1590000003.0,
                                      'success': False},
                        'success': True}
    sentiment_succeeded = {'start_time': 1590000000.0,
                           'stop_time': 1590000001.0,
                           'sentiment': {'start_time': 1590000002.0,
                                         'stop_time': 1590000003.0,
                                         'success': True},
                           'success': True}

    # If the base build doesn't exist, or fails: same errors as for regular
    # wait_for_build
    requests_mock.get(project_url, json={'last_build_info': {}})
    with pytest.raises(ValueError, match='not building'):
        client.wait_for_sentiment_build()

    requests_mock.get(
        project_url,
        _last_build_infos_to_mock_returns([build_running, build_failed])
    )
    with pytest.raises(LuminosoError) as e:
        client.wait_for_sentiment_build(interval=.0001)
    assert e.value.args == (build_failed,)

    # If the base build exists but sentiment is not building: error
    requests_mock.get(
        project_url,
        json={'last_build_info': {
            'start_time': 1590000000.0, 'stop_time': None, 'sentiment': {}
        }}
    )
    with pytest.raises(ValueError, match='not building sentiment'):
        client.wait_for_sentiment_build()

    # If the sentiment build succeeds: the project's last build info
    requests_mock.get(
        project_url,
        _last_build_infos_to_mock_returns(
            [build_running, build_running, build_succeeded,
             sentiment_running, sentiment_running, sentiment_succeeded]
        )
    )
    result = client.wait_for_sentiment_build(interval=.0001)
    assert result == sentiment_succeeded

    # If the sentiment build fails: error with the project's last build info
    requests_mock.get(
        project_url,
        _last_build_infos_to_mock_returns(
            [build_running, build_running, build_succeeded,
             sentiment_running, sentiment_running, sentiment_failed]
        )
    )
    with pytest.raises(LuminosoError) as e:
        client.wait_for_sentiment_build(interval=.0001)
    assert e.value.args == (sentiment_failed,)
