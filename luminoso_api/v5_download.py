import argparse
import json
import sys
import os
from tqdm import tqdm

from .v5_client import LuminosoClient
from .v5_constants import URL_BASE


DESCRIPTION = 'Download documents from a Luminoso project via the command line.'
DOCS_PER_BATCH = 1000

# The fields we want for "concise" or "expanded" downloads
CONCISE_FIELDS = ['title', 'text', 'metadata']
EXPANDED_FIELDS = CONCISE_FIELDS + ['terms', 'fragments', 'vector']


def _sanitize_filename(filename):
    """
    Get a filename that lacks the / character (so it doesn't express a path by
    accident) and also lacks spaces (just for tab-completion convenience).
    """
    return filename.replace('/', '_').replace(' ', '_')


def iterate_docs(client, expanded=False, progress=False):
    """
    Yield each document in a Luminoso project in turn. Requires a client whose
    URL points to a project.

    If expanded=True, it will include additional fields that Luminoso added in
    its analysis, such as 'terms' and 'vector'.

    Otherwise, it will contain only the fields necessary to reconstruct the
    document: 'title', 'text', and 'metadata'.

    Shows a progress bar if progress=True.
    """
    # Get total number of docs from the project record
    num_docs = client.get()['document_count']
    progress_bar = None
    try:
        if progress:
            progress_bar = tqdm(desc='Downloading documents', total=num_docs)

        for offset in range(0, num_docs, DOCS_PER_BATCH):
            response = client.get(
                'docs', offset=offset, limit=DOCS_PER_BATCH,
                fields=EXPANDED_FIELDS if expanded else CONCISE_FIELDS
            )
            docs = response['result']
            for doc in docs:
                if progress:
                    progress_bar.update()
                yield doc

    finally:
        if progress:
            progress_bar.close()


def download_docs(client, output_filename=None, expanded=False):
    """
    Given a LuminosoClient pointing to a project and a filename to write to,
    retrieve all its documents in batches, and write them to a JSON lines
    (.jsons) file with one document per line.
    """
    if output_filename is None:
        # Find a default filename to download to, based on the project name.
        projname = _sanitize_filename(client.get()['name'])
        output_filename = '{}.jsons'.format(projname)

        # If the file already exists, add .1, .2, ..., after the project name
        # to unobtrusively get a unique filename.
        counter = 0
        while os.access(output_filename, os.F_OK):
            counter += 1
            output_filename = '{}.{}.jsons'.format(projname, counter)

        print('Downloading project to {!r}'.format(output_filename))

    with open(output_filename, 'w', encoding='utf-8') as out:
        for doc in iterate_docs(client, expanded=expanded, progress=True):
            print(json.dumps(doc, ensure_ascii=False), file=out)


def _main(argv):
    """
    Handle arguments for the 'lumi-download' command.
    """
    parser = argparse.ArgumentParser(
        description=DESCRIPTION,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        '-b',
        '--base-url',
        default=URL_BASE,
        help='API root url, default: %s' % URL_BASE,
    )
    parser.add_argument('-f', '--token-file',
                        help='file where an API token was saved')
    parser.add_argument(
        '-e', '--expanded',
        help="Include Luminoso's analysis of each document, such as terms and"
             ' document vectors',
        action='store_true',
    )
    parser.add_argument(
        'project_id', help='The ID of the project in the Daylight API'
    )
    parser.add_argument(
        'output_file', nargs='?', default=None,
        help='The JSON lines (.jsons) file to write to'
    )
    args = parser.parse_args(argv)

    client = LuminosoClient.connect(
        url=args.base_url, token_file=args.token_file,
        user_agent_suffix='lumi-download'
    )
    proj_client = client.client_for_path('projects/{}'.format(args.project_id))
    download_docs(proj_client, args.output_file, args.expanded)


def main():
    """
    The setuptools entry point.
    """
    _main(sys.argv[1:])
