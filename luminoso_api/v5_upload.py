import argparse
import json
import time
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
def _batches(iterable, size):
    """
    Take an iterator and yield its contents in groups of `size` items.
    """
    sourceiter = iter(iterable)
    while True:
        batchiter = islice(sourceiter, size)
        yield chain([next(batchiter)], batchiter)


def _simplify_doc(doc):
    """
    Limit a document to just the three fields we should upload.
    """
    simplified = {}
    for field in UPLOAD_FIELDS:
        if field not in doc:
            raise ValueError(
                "The document {!r} didn't contain the field {!r}".format(
                    doc, field
                )
            )
        simplified[field] = doc[field]

    return simplified


def iterate_json_lines(filename):
    """
    Get an iterator of the JSON objects in a JSON lines file.
    """
    for line in open(filename, encoding='utf-8'):
        yield json.loads(line)


def create_project_with_docs(client, docs, language, name, progress=False):
    description = 'Uploaded using lumi-upload at {}'.format(time.asctime())
    proj_record = client.post(
        'projects', name=name, language=language, description=description
    )
    proj_id = proj_record['project_id']
    proj_client = client.client_for_path(proj_id)
    try:
        if progress:
            progress_bar = tqdm(desc='Uploading documents')
        else:
            progress_bar = None

        for batch in batches(docs, BATCH_SIZE):
            docs_to_upload = [_simplify_doc(doc) for doc in batch]
            proj_client.post('upload', docs=docs_to_upload)
            if progress:
                progress_bar.update(BATCH_SIZE)

    finally:
        if progress:
            progress_bar.close()

    if progress:
        print('The server is building project {!r}.'.format(proj_id))
    proj_client.post('build')

    while True:
        time.sleep(10)
        build_info = proj_client.get()['last_build_info']
        if 'success' in build_info:
            if not build_info['success']:
                raise LuminosoServerError(build_info['reason'])

    return proj_client.get()


def upload_docs(client, input_filename, language, name, progress=False):
    """
    Given a LuminosoClient pointing to the root of the API, and a filename to
    read JSON lines from, create a project from the documents in that file.
    """
    docs = iterate_json_lines(input_filename)
    return create_project_with_docs(
        client, docs, language, name, progress=progress
    )


def main():
    """
    Handle arguments for the 'lumi-download' command.
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
    parser.add_argument('-t', '--token', help='API authentication token')
    parser.add_argument(
        '-l',
        '--language',
        default='en',
        help='The language code for the language the text is in. Default: en',
    )
    parser.add_argument(
        '-s',
        '--save-token',
        action='store_true',
        help='save --token for --base-url to ~/.luminoso/tokens.json',
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
    args = parser.parse_args()

    if args.save_token:
        if not args.token:
            raise ValueError('error: no token provided')
        LuminosoClient.save_token(
            args.token, domain=urlparse(args.base_url).netloc
        )

    # Get a name, interactively if necessary, and make sure it's not the empty
    # string
    name = args.project_name
    if name is None:
        name = input('Enter a name for the project: ')
        if not name:
            print('Aborting because no name was provided.')
            return

    client = LuminosoClient.connect(url=args.base_url, token=args.token)
    result = upload_docs(
        client, args.input_filename, args.language, name, progress=True
    )
    print(
        'Project {!r} created with {} documents'.format(
            result['project_id'], result['document_count']
        )
    )
