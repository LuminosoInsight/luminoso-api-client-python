import json
import tempfile

from luminoso_api.v5_client import LuminosoClient
from luminoso_api.v5_upload import iterate_json_lines
from luminoso_api.v5_download import (
    iterate_docs, download_docs, DOCS_PER_BATCH
)

BASE_URL = 'http://mock-api.localhost/api/v5/'

PROJECT_RECORD = {
    'name': 'Test Project',
    'description': 'Project Description',
    'language': 'en',
    'creator': 'user',
    'creation_date': 1541777234,
    'last_successful_build_time': None,
    'last_metaupdate': None,
    'last_build_info': {},
    'project_id': 'projid',
    'workspace_id': 'workspace',
    'document_count': 2,
    'permissions': ['read', 'write', 'create']
}

FULL_DOCS = [
    {
        'title': 'Document 1',
        'text': 'hello',
        'terms': [{'term_id': 'hello|en', 'start': 0, 'end': 5}],
        'fragments': [],
        'metadata': [],
        'vector': 'AAAA',
        'doc_id': 'uuid-0',
        'match_score': None
    },
    {
        'title': 'Document 2',
        'text': 'hello',
        'terms': [{'term_id': 'hello|en', 'start': 0, 'end': 5}],
        'fragments': [],
        'metadata': [],
        'vector': 'AAAA',
        'doc_id': 'uuid-1',
        'match_score': None
    },
]

EXPANDED_DOCS = [
    {
        'title': 'Document 1',
        'text': 'hello',
        'terms': [{'term_id': 'hello|en', 'start': 0, 'end': 5}],
        'fragments': [],
        'metadata': [],
        'vector': 'AAAA',
    },
    {
        'title': 'Document 2',
        'text': 'hello',
        'terms': [{'term_id': 'hello|en', 'start': 0, 'end': 5}],
        'fragments': [],
        'metadata': [],
        'vector': 'AAAA',
    },
]

CONCISE_DOCS = [
    {'title': 'Document 1', 'text': 'hello', 'metadata': []},
    {'title': 'Document 2', 'text': 'hello', 'metadata': []},
]

REPETITIVE_DOC = {'title': 'Yadda', 'text': 'yadda yadda', 'metadata': []}


def doc_paring_callback(request, context):
    # The "qs" attribute on the mock request is the result of running
    # urllib.parse.parse_qs on the query string, which maps the query variable
    # names to lists of their values; thus we want the json-decoded value of
    # the first (and only) element of the "fields" parameter
    fields = json.loads(request.qs['fields'][0])
    docs = [
        {field: value for field, value in doc.items() if field in fields}
        for doc in FULL_DOCS
    ]
    return {'result': docs, 'total_count': 2, 'filter_count': 2, 'search': None}


def test_iteration(requests_mock):
    """
    Test iterating over the documents in a project.
    """
    requests_mock.get(BASE_URL + 'projects/projid/', json=PROJECT_RECORD)
    requests_mock.get(BASE_URL + 'projects/projid/docs/',
                      json=doc_paring_callback)
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
        json=dict(PROJECT_RECORD, document_count=DOCS_PER_BATCH + 2),
    )
    requests_mock.get(
        BASE_URL + 'projects/projid/docs/?limit=%d' % DOCS_PER_BATCH,
        json={'result': page1}
    )
    requests_mock.get(
        BASE_URL + ('projects/projid/docs/?offset=%d&limit=%d' %
                    (DOCS_PER_BATCH, DOCS_PER_BATCH)),
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
    requests_mock.get(BASE_URL + 'projects/projid/docs/',
                      json=doc_paring_callback)
    client = LuminosoClient.connect(BASE_URL + 'projects/projid', token='fake')

    with tempfile.TemporaryDirectory() as tempdir:
        output_file = tempdir + '/test.jsons'
        download_docs(client, output_file)

        read_docs = list(iterate_json_lines(output_file))
        assert read_docs == CONCISE_DOCS
