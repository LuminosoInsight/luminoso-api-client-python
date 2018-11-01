from luminoso_api.v5_client import LuminosoClient
from luminoso_api.v5_download import iterate_docs, download_docs

import pytest
import requests
import tempfile
import json

BASE_URL = 'http://mock-api.localhost/api/v5/'
RESPONSE = {
    'result': [
        {'title': 'Document 1', 'text': 'hello', 'tokens': [{'term_id': 'hello|en'}], 'metadata': [], 'vector': 'AAAA', 'doc_id': 'uuid-0'},
        {'title': 'Document 2', 'text': 'hello', 'tokens': [{'term_id': 'hello|en'}], 'metadata': [], 'vector': 'AAAA', 'doc_id': 'uuid-0'},
    ],
    'total_count': 2
}

EXPANDED_DOCS = [
    {'title': 'Document 1', 'text': 'hello', 'tokens': [{'term_id': 'hello|en'}], 'metadata': [], 'vector': 'AAAA'},
    {'title': 'Document 2', 'text': 'hello', 'tokens': [{'term_id': 'hello|en'}], 'metadata': [], 'vector': 'AAAA'},
]

CONCISE_DOCS = [
    {'title': 'Document 1', 'text': 'hello', 'metadata': []},
    {'title': 'Document 2', 'text': 'hello', 'metadata': []},
]


def test_iteration(requests_mock):
    """
    Test the way that we make GET, POST, PUT, and DELETE requests using the
    correspondingly-named methods of the client.
    """
    requests_mock.get(BASE_URL + 'projects/projid/docs/', json=RESPONSE)
    client = LuminosoClient.connect(BASE_URL + 'projects/projid', token='fake')
    
    docs = list(iterate_docs(client, progress=False))
    assert docs == CONCISE_DOCS

    docs = list(iterate_docs(client, progress=False, expanded=True))
    assert docs == EXPANDED_DOCS


def test_writing(requests_mock):
    """
    Test the way that we make GET, POST, PUT, and DELETE requests using the
    correspondingly-named methods of the client.
    """
    requests_mock.get(BASE_URL + 'projects/projid/docs/', json=RESPONSE)
    client = LuminosoClient.connect(BASE_URL + 'projects/projid', token='fake')
    
    with tempfile.TemporaryDirectory() as tempdir:
        output_file = tempdir + '/test.jsons'
        download_docs(client, output_file)

        # TODO: if we add a .jsons reader helper function to the client, use
        # it here
        read_docs = []
        for line in open(output_file, encoding='utf-8'):
            obj = json.loads(line)
            read_docs.append(obj)

        assert read_docs == CONCISE_DOCS

