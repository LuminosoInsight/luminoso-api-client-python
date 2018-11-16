from luminoso_api.v5_client import LuminosoClient
from luminoso_api.v5_download import  (
    iterate_docs, download_docs, DOCS_PER_BATCH
)

import pytest
import requests
import tempfile
import json

BASE_URL = 'http://mock-api.localhost/api/v5/'
RESPONSE = {
    'result': [
        {
            'title': 'Document 1',
            'text': 'hello',
            'terms': [{'term_id': 'hello|en'}],
            'metadata': [],
            'vector': 'AAAA',
            'doc_id': 'uuid-0',
        },
        {
            'title': 'Document 2',
            'text': 'hello',
            'terms': [{'term_id': 'hello|en'}],
            'metadata': [],
            'vector': 'AAAA',
            'doc_id': 'uuid-1',
        },
    ],
}

PROJECT_RECORD = {
    'counts': {'__all__': 2}
}

EXPANDED_DOCS = [
    {
        'title': 'Document 1',
        'text': 'hello',
        'terms': [{'term_id': 'hello|en'}],
        'metadata': [],
        'vector': 'AAAA',
    },
    {
        'title': 'Document 2',
        'text': 'hello',
        'terms': [{'term_id': 'hello|en'}],
        'metadata': [],
        'vector': 'AAAA',
    },
]

CONCISE_DOCS = [
    {'title': 'Document 1', 'text': 'hello', 'metadata': []},
    {'title': 'Document 2', 'text': 'hello', 'metadata': []},
]

REPETITIVE_DOC = {'title': 'Yadda', 'text': 'yadda yadda', 'metadata': []}


def test_iteration(requests_mock):
    """
    Test iterating over the documents in a project.
    """
    requests_mock.get(BASE_URL + 'projects/projid/', json=PROJECT_RECORD)
    requests_mock.get(BASE_URL + 'projects/projid/docs/', json=RESPONSE)
    client = LuminosoClient.connect(BASE_URL + 'projects/projid', token='fake')

    docs = list(iterate_docs(client, progress=False))
    assert docs == CONCISE_DOCS

    docs = list(iterate_docs(client, progress=False, expanded=True))
    assert docs == EXPANDED_DOCS


def test_pagination(requests_mock):
    """
    Test iterating over 1002 documents that come in two pages.
    """
    page1 = [REPETITIVE_DOC] * DOCS_PER_BATCH
    page2 = [REPETITIVE_DOC] * 2

    requests_mock.get(
        BASE_URL + 'projects/projid/', 
        json={'counts': {'__all__': DOCS_PER_BATCH + 2}},
    )
    requests_mock.get(
        BASE_URL + 'projects/projid/docs/?limit=%d' % DOCS_PER_BATCH, 
        json={'result': page1}
    )
    requests_mock.get(
        BASE_URL + 'projects/projid/docs/?offset=%d&limit=%d' % 
            (DOCS_PER_BATCH, DOCS_PER_BATCH),
        json={'result': page2},
    )

    client = LuminosoClient.connect(BASE_URL + 'projects/projid', token='fake')
    docs = list(iterate_docs(client, progress=False))
    assert docs == [REPETITIVE_DOC] * (DOCS_PER_BATCH + 2)


def test_writing(requests_mock):
    """
    Test writing downloaded documents to a JSON-lines file.
    """
    requests_mock.get(BASE_URL + 'projects/projid/', json=PROJECT_RECORD)
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
