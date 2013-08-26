from itertools import islice, chain
from luminoso_api import LuminosoClient
from luminoso_api.json_stream import transcode_to_stream, stream_json_lines

ROOT_URL = 'https://api.luminoso.com/v4'
LOCAL_URL = 'http://localhost:5000/v4'

#http://code.activestate.com/recipes/303279-getting-items-in-batches/
def batches(iterable, size):
    """
    Take an iterator and yield its contents in groups of `size` items.
    """
    sourceiter = iter(iterable)
    while True:
        batchiter = islice(sourceiter, size)
        yield chain([batchiter.next()], batchiter)

def upload_stream(stream, server, account, projname, reader_dict,
                  username=None, password=None,
                  append=False, stage=False):
    """
    Given a file-like object containing a JSON stream, upload it to
    Luminoso with the given account name and project name.
    """
    client = LuminosoClient.connect(server,
                                    username=username, password=password)
    if not append:
        # If we're not appending to an existing project, create new project.
        info = client.post('/projects/' + account, name=projname)
        project_id = info['project_id']
    else:
        projects = client.get('/projects/' + account, name=projname)
        if len(projects) == 0:
            print 'No such project exists!'
            return
        if len(projects) > 1:
            print 'Warning: Multiple projects with name "%s".  ' % projname,
        project_id = projects[0]['project_id']
        print 'Using existing project with id %s.' % project_id

    project = client.change_path('/projects/' + account + '/' + project_id)

    if stage:
        url = 'docs'
    else:
        url = 'docs/preload'

    counter = 0
    final_job_id = None
    for batch in batches(stream, 1000):
        counter += 1
        documents = list(batch)
        job_id = project.upload(url, documents, width=4, readers=reader_dict)
        print 'Uploaded batch #%d' % (counter)
        final_job_id = job_id

    if not stage:
        # Calculate the docs into the assoc space.
        print 'Calculating.'
        final_job_id = project.post('docs/recalculate', width=4, readers=reader_dict)

    if final_job_id is not None:
        project.wait_for(final_job_id)


def upload_file(filename, server, account, projname, reader_dict=None,
                username=None, password=None,
                append=False, stage=False):
    """
    Upload a file to Luminoso with the given account and project name.

    Given a file containing JSON, JSON stream, or CSV data, this verifies
    that we can successfully convert it to a JSON stream, then uploads that
    JSON stream.
    """
    if reader_dict is None:
        reader_dict = {}
    stream = transcode_to_stream(filename)
    upload_stream(stream_json_lines(stream), server, account, projname,
                  reader_dict, username=username, password=password,
                  append=append, stage=stage)

def main():
    """
    Handle command line arguments, to upload a file to a Luminoso project
    as a script.
    """
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('filename')
    parser.add_argument('account')
    parser.add_argument('project_name')
    parser.add_argument('--append',
        help=("If append flag is used, upload documents to existing project,"
              "rather than creating a new project."),
        action="store_true")
    parser.add_argument('-s', '--stage',
        help=("If stage flag is used, just upload docs, don't recalculate."),
        action="store_true")
    parser.add_argument('-a', '--api-url',
        help="Specify an alternate API url",
        default=ROOT_URL)
    parser.add_argument('-l', '--local',
        help="Run on localhost:5000 instead of the default API server "
             "(overrides -a)",
        action="store_true")
    parser.add_argument('-r', '--readers', metavar='LANG=READER',
        help="Custom reader to use, in a form such as 'ja=metanl.ja,en=freeling.en'")
    parser.add_argument('-u', '--username', default=None,
        help="username (defaults to your username on your computer)")
    parser.add_argument('-p', '--password', default=None,
        help="password (you can leave this out and type it in later)")
    args = parser.parse_args()
    url = args.api_url
    if args.local:
        url = LOCAL_URL

    reader_dict = {}
    if args.readers:
        for item in args.readers.split(','):
            if '=' not in item:
                raise ValueError("You entered %r as a reader, but it should "\
                                 "have the form 'lang=reader.name'")
            lang, reader_name = item.split('=', 1)
            reader_dict[lang] = reader_name

    upload_file(args.filename, url, args.account, args.project_name,
                reader_dict, username=args.username, password=args.password,
                append=args.append, stage=args.stage)

if __name__ == '__main__':
    main()
