import argparse
import json
import time
import sys
from itertools import islice, chain
from tqdm import tqdm

from .v5_client import LuminosoClient
from .errors import LuminosoServerError
from .v5_constants import URL_BASE


DESCRIPTION = 'Create a Luminoso project from documents in a file.'

# These fields (and only these fields) must exist on every uploaded document.
UPLOAD_FIELDS = ['title', 'text', 'metadata']
BATCH_SIZE = 1000

# http://code.activestate.com/recipes/303279-getting-items-in-batches/
# Updated for Python 3.5+ by catching StopIteration
def _batches(iterable, size):
    """
    Take an iterator and yield its contents in groups of `size` items.
    """
    sourceiter = iter(iterable)
    while True:
        try:
            batchiter = islice(sourceiter, size)
            yield chain([next(batchiter)], batchiter)
        except StopIteration:
            return


def _simplify_doc(doc):
    """
    Limit a document to just the three fields we should upload.
    """
    # Mutate a copy of the document to fill in missing fields
    doc = dict(doc)
    if 'text' not in doc:
        raise ValueError("The document {!r} has no text field".format(doc))
    return {
        'text': doc['text'],
        'metadata': doc.get('metadata', []),
        'title': doc.get('title', '')
    }


def iterate_json_lines(filename):
    """
    Get an iterator of the JSON objects in a JSON lines file.
    """
    for line in open(filename, encoding='utf-8'):
        yield json.loads(line)


def create_project_with_docs(
    client, docs, language, name, workspace=None, progress=False
):
    """
    Given an iterator of documents, upload them as a Luminoso project.
    """
    description = 'Uploaded using lumi-upload at {}'.format(time.asctime())
    if workspace is not None:
        proj_record = client.post(
            'projects',
            name=name,
            language=language,
            description=description,
            workspace_id=workspace,
        )
    else:
        proj_record = client.post(
            'projects', name=name, language=language, description=description
        )
    proj_id = proj_record['project_id']
    proj_client = client.client_for_path('projects/' + proj_id)
    try:
        if progress:
            progress_bar = tqdm(desc='Uploading documents')
        else:
            progress_bar = None

        for batch in _batches(docs, BATCH_SIZE):
            docs_to_upload = [_simplify_doc(doc) for doc in batch]
            proj_client.post('upload', docs=docs_to_upload)
            if progress:
                progress_bar.update(BATCH_SIZE)

    finally:
        if progress:
            progress_bar.close()

    print('The server is building project {!r}.'.format(proj_id))
    proj_client.post('build')

    while True:
        time.sleep(10)
        proj_status = proj_client.get()
        build_info = proj_status['last_build_info']
        if 'success' in build_info:
            if not build_info['success']:
                raise LuminosoServerError(build_info['reason'])
            return proj_status


def upload_docs(
    client, input_filename, language, name, workspace=None, progress=False
):
    """
    Given a LuminosoClient pointing to the root of the API, and a filename to
    read JSON lines from, create a project from the documents in that file.
    """
    docs = iterate_json_lines(input_filename)
    return create_project_with_docs(
        client, docs, language, name, workspace=workspace, progress=progress
    )


def _main(argv):
    """
    Handle arguments for the 'lumi-upload' command.
    """
    parser = argparse.ArgumentParser(
        description=DESCRIPTION,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        '-b',
        '--base-url',
        default=URL_BASE,
        help='API root url, default: %s' % URL_BASE,
    )
    parser.add_argument(
        '-f',
        '--token-file',
        help='file where an API token was saved'
    )
    parser.add_argument(
        '-w',
        '--workspace-id',
        default=None,
        help='Workspace ID that should own the project, if not the default',
    )
    parser.add_argument(
        '-l',
        '--language',
        default='en',
        help='The language code for the language the text is in. Default: en',
    )
    parser.add_argument(
        'input_filename',
        help='The JSON-lines (.jsons) file of documents to upload',
    )
    parser.add_argument(
        'project_name',
        nargs='?',
        default=None,
        help='What the project should be called',
    )
    args = parser.parse_args(argv)

    client = LuminosoClient.connect(
        url=args.base_url, token_file=args.token_file,
        user_agent_suffix='lumi-upload'
    )

    name = args.project_name
    if name is None:
        name = input('Enter a name for the project: ')
        if not name:
            print('Aborting because no name was provided.')
            return

    result = upload_docs(
        client,
        args.input_filename,
        args.language,
        name,
        workspace=args.workspace_id,
        progress=True,
    )
    print(
        'Project {!r} created with {} documents'.format(
            result['project_id'], result['document_count']
        )
    )


def main():
    """
    The setuptools entry point.
    """
    _main(sys.argv[1:])
