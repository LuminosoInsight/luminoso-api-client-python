from luminoso_api.v5_client import LuminosoClient, get_root_url
from luminoso_api.errors import LuminosoClientError, LuminosoServerError

import pytest
import requests

BASE_URL = 'http://mock-api.localhost/api/v5/'


def test_paths():
    client = LuminosoClient.connect(BASE_URL, token='fake')

    client_copy = client.client_for_path('first_path')
    assert client.url == BASE_URL
    assert client_copy.url == BASE_URL + 'first_path/'

    # Paths are relative to the client's URL; paths with slashes in front are
    # absolute.
    assert client_copy.client_for_path('subpath').url == BASE_URL + 'first_path/subpath/'
    assert client_copy.client_for_path('/second_path').url == BASE_URL + 'second_path/'

    # Similarly, test get_root_url
    with pytest.raises(ValueError):
        get_root_url('not.good.enough/api/v5')

    assert get_root_url('https://analytics.luminoso.com/', warn=False) == 'https://analytics.luminoso.com/api/v5'
    assert get_root_url('http://analytics.luminoso.com/api/v5/who/cares?blaah') == 'http://analytics.luminoso.com/api/v5'


def test_mock_requests(requests_mock):
    project_list = [{'name': 'Example project'}]
    requests_mock.get(BASE_URL + 'projects/', json=project_list)
    requests_mock.post(BASE_URL + 'projects/', json={})
    requests_mock.put(BASE_URL + 'projects/projid/', json={})
    requests_mock.delete(BASE_URL + 'projects/projid/', json={})

    client = LuminosoClient.connect(BASE_URL, token='fake')
    response = client.get('projects')
    assert response == project_list

    client2 = client.client_for_path('projects')
    result = client2.get()
    assert response == project_list

    response = client2.post(param='value')
    assert response == {}
    assert requests_mock.last_request.method == 'POST'
    assert requests_mock.last_request.json() == {'param': 'value'}

    response = client2.put('projid', param='value')
    assert response == {}
    assert requests_mock.last_request.method == 'PUT'
    assert requests_mock.last_request.json() == {'param': 'value'}

    response = client2.delete('projid')
    assert response == {}
    assert requests_mock.last_request.method == 'DELETE'


def test_failing_requests(requests_mock):
    requests_mock.get(BASE_URL + 'bad/', status_code=404)
    requests_mock.get(BASE_URL + 'fail/', status_code=500)
    client = LuminosoClient.connect(BASE_URL, token='fake')

    with pytest.raises(LuminosoClientError):
        client.get('bad')

    with pytest.raises(LuminosoServerError):
        client.get('fail')
