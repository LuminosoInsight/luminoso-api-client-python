import argparse
import json
import time
from itertools import islice, chain
from tqdm import tqdm

from .v5_client import LuminosoClient
from .errors import LuminosoServerError
from .v5_constants import URL_BASE


# These fields (and only these fields) must exist on every uploaded document.
UPLOAD_FIELDS = ["title", "text", "metadata"]
BATCH_SIZE=1000

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
            raise ValueError("The document {!r} didn't contain the field {!r}".format(doc, field))
        simplified[field] = doc[field]

    return simplified


def iterate_json_lines(filename):
    """
    Get an iterator of the JSON objects in a JSON lines file.
    """
    for line in open(filename, encoding='utf-8'):
        yield json.loads(line)


def upload_project(client, name, language, docs, progress=False):
    description = 'Uploaded using lumi-upload at {}'.format(time.asctime())
    proj_record = client.post('projects', name=name, language=language, description=description)
    proj_id = proj_record['project_id']
    proj_client = client.client_for_path(proj_id)
    try:
        if progress:
            progress_bar = tqdm(desc="Uploading documents"), 
        else:
            progress_bar = None

        for batch in batches(docs, BATCH_SIZE):
            docs_to_upload = [_simplify_doc(doc) for doc in batch]
            proj_client.post('upload', docs=docs_to_upload)
            progress_bar.update(BATCH_SIZE)

    finally:
        if progress:
            progress_bar.close()

    if progress:
        print("Building project {!r}.".format(proj_id))
    proj_client.post('build')

    while True:
        time.sleep(10)
        build_info = proj_client.get()['last_build_info']
        if 'success' in build_info:
            if not build_info['success']:
                raise LuminosoServerError(build_info['reason'])

    return proj_client.get()



def iterate_docs(client, expanded=False, progress=False):
    """
    Yield each document in a Luminoso project in turn. Requires a client whose
    URL points to a project.

    If expanded=True, it will include additional fields that Luminoso added in
    its analysis, such as 'tokens' and 'vector'.
    
    Otherwise, it will contain only the fields necessary to reconstruct the
    document: 'title', 'text', and 'metadata'.

    Shows a progress bar if progress=True.
    """
    num_docs = client.get("docs", limit=1)["total_count"]
    progress_bar = None
    try:
        if progress:
            progress_bar = tqdm(desc="Downloading documents", total=num_docs)
        
        for offset in range(0, num_docs, DOCS_PER_BATCH):
            response = client.get("docs", offset=offset, limit=DOCS_PER_BATCH)
            docs = response["result"]
            for doc in docs:
                # Get the appropriate set of fields for each document
                if expanded:
                    for field in UNNECESSARY_FIELDS:
                        if field in doc:
                            del doc[field]
                else:
                    concise_doc = {field: doc[field] for field in CONCISE_FIELDS}
                    doc = concise_doc
                
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
        projname = _sanitize_filename(client.get()["name"])
        output_filename = "{}.jsons".format(projname)

        # If the file already exists, add .1, .2, ..., after the project name
        # to unobtrusively get a unique filename.
        counter = 0
        while os.access(output_filename, os.F_OK):
            counter += 1
            output_filename = "{}.{}.jsons".format(projname, counter)

        print("Downloading {!r}".format(output_filename))

    with open(output_filename, 'w', encoding='utf-8') as out:
        for doc in iterate_docs(client, expanded=expanded, progress=True):
            print(json.dumps(doc, ensure_ascii=False), file=out)


def main():
    """
    Handle arguments for the 'lumi-download' command.
    """
    parser = argparse.ArgumentParser(
        description=DESCRIPTION, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "-b",
        "--base-url",
        default=URL_BASE,
        help="API root url, default: %s" % URL_BASE,
    )
    parser.add_argument(
        "-e",
        "--expanded",
        help="Include Luminoso's analysis of each document, such as tokens and document vectors",
        action="store_true",
    )
    parser.add_argument("-t", "--token", help="API authentication token")
    parser.add_argument(
        "-s",
        "--save-token",
        action="store_true",
        help="save --token for --base-url to ~/.luminoso/tokens.json",
    )
    parser.add_argument("project_id", help="The ID of the project in the Daylight API")
    parser.add_argument(
        "output_file", help="The .tsv file to write to", nargs="?", default=None
    )
    args = parser.parse_args()

    if args.save_token:
        if not args.token:
            raise Exception("error: no token provided")
        LuminosoClient.save_token(args.token, domain=urlparse(args.base_url).netloc)

    client = LuminosoClient.connect(url=args.base_url, token=args.token)
    proj_client = client.client_for_path("projects/{}".format(args.project_id))
    download_docs(proj_client, args.output_file, args.expanded)
