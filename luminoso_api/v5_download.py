import argparse
import csv
from signal import signal, SIGPIPE, SIG_DFL
from urllib.parse import urlparse
from tqdm import tqdm as progress

from .v5_client import LuminosoClient
from .v5_constants import URL_BASE

# Python raises IOError when reading process (such as `head`) closes a pipe.
# Setting SIG_DFL as the SIGPIPE handler prevents this program from crashing.
signal(SIGPIPE, SIG_DFL)


DESCRIPTION = "Download documents from a Luminoso project via the command line."
DOCS_PER_BATCH = 1000


def download_docs(client, output_filename):
    """
    Given a LuminosoClient pointing to a project and a filename to write to,
    retrieve all its documents in batches and write them as rows of the
    TSV file.
    """
    num_docs = client.get('docs', limit=1)['total_count']
    metadata_fields = []
    for item in client.get('metadata')['result']:
        item_name = '{}_{}'.format(item['name'], item['type'])
        metadata_fields.append(item_name)

    with progress(desc='Downloading documents', total=num_docs) as progress_bar:
        with open(output_filename, 'w', encoding='utf-8') as out:
            fieldnames = sorted(metadata_fields) + ['title', 'text']
            writer = csv.DictWriter(out, fieldnames=fieldnames, dialect=csv.excel_tab)
            writer.writeheader()
            for offset in range(0, num_docs, DOCS_PER_BATCH):
                response = client.get('docs', offset=offset, limit=DOCS_PER_BATCH)
                docs = response['result']
                for doc in docs:
                    doc_fields = {}
                    for item in doc['metadata']:
                        item_name = '{}_{}'.format(item['name'], item['type'])
                        doc_fields[item_name] = item['value']
                    text = doc['text'].replace('\n', '\N{PILCROW SIGN}')
                    doc_fields['text'] = text
                    doc_fields['title'] = doc['title']
                    writer.writerow(doc_fields)
                    progress_bar.update()


def main():
    """
    Handle arguments for the 'lumi-download' command.
    """
    parser = argparse.ArgumentParser(
        description=DESCRIPTION,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument('-b', '--base-url', default=URL_BASE,
                        help="API root url, default: %s" % URL_BASE)
    parser.add_argument('-t', '--token', help="API authentication token")
    parser.add_argument('-s', '--save-token', action='store_true',
                        help="save --token for --base-url to"
                             " ~/.luminoso/tokens.json")
    parser.add_argument('project_id', help='The ID of the project in the Daylight API')
    parser.add_argument('output_file', help='The .tsv file to write to')
    args = parser.parse_args()

    if args.save_token:
        if not args.token:
            raise Exception("error: no token provided")
        LuminosoClient.save_token(
            args.token,
            domain=urlparse(args.base_url).netloc
        )

    client = LuminosoClient.connect(url=args.base_url, token=args.token)
    proj_client = client.client_for_path('projects/{}'.format(args.project_id))
    download_docs(proj_client, args.output_file)
