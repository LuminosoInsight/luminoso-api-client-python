from __future__ import print_function, unicode_literals
from itertools import islice, chain
from luminoso_api import LuminosoClient
from luminoso_api.constants import URL_BASE
from luminoso_api.json_stream import transcode_to_stream, stream_json_lines


# http://code.activestate.com/recipes/303279-getting-items-in-batches/
def batches(iterable, size):
    """
    Take an iterator and yield its contents in groups of `size` items.
    """
    sourceiter = iter(iterable)
    while True:
        batchiter = islice(sourceiter, size)
        yield chain([next(batchiter)], batchiter)


def upload_stream(stream, server, account, projname, language=None,
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
        print('New project ID:', project_id)
    else:
        projects = client.get('/projects/' + account, name=projname)
        if len(projects) == 0:
            print('No such project exists!')
            return
        if len(projects) > 1:
            print('Warning: Multiple projects with name "%s".  ' % projname,
                  end='')
        project_id = projects[0]['project_id']
        print('Using existing project with id %s.' % project_id)

    project = client.change_path('/projects/' + account + '/' + project_id)

    counter = 0
    for batch in batches(stream, 1000):
        counter += 1
        documents = list(batch)
        project.upload('docs', documents)
        print('Uploaded batch #%d' % (counter))

    if not stage:
        # Calculate the docs into the assoc space.
        print('Calculating.')
        kwargs = {}
        if language is not None:
            kwargs = {'language': language}
        job_id = project.post('docs/recalculate', **kwargs)
        project.wait_for(job_id)


def upload_file(filename, server, account, projname, language=None,
                username=None, password=None,
                append=False, stage=False, date_format=None):
    """
    Upload a file to Luminoso with the given account and project name.

    Given a file containing JSON, JSON stream, or CSV data, this verifies
    that we can successfully convert it to a JSON stream, then uploads that
    JSON stream.
    """
    stream = transcode_to_stream(filename, date_format)
    upload_stream(stream_json_lines(stream),
                  server, account, projname, language=language,
                  username=username, password=password,
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
    parser.add_argument(
        '--append',
        help=("If append flag is used, upload documents to existing project, "
              "rather than creating a new project."),
        action="store_true"
    )
    parser.add_argument(
        '-s', '--stage',
        help="If stage flag is used, just upload docs, don't recalculate.",
        action="store_true"
    )
    parser.add_argument(
        '-a', '--api-url',
        help="Specify an alternate API url",
        default=URL_BASE
    )
    parser.add_argument(
        '-l', '--language',
        help=("Two-letter language code to use when recalculating (e.g. 'en' "
              "or 'ja')")
    )
    parser.add_argument(
        '-u', '--username', default=None,
        help="username (defaults to your username on your computer)"
    )
    parser.add_argument(
        '-p', '--password', default=None,
        help="password (you can leave this out and type it in later)"
    )
    parser.add_argument(
        '-d', '--date-format', default='iso',
        help=("format string for parsing dates, following "
              "http://strftime.org/.  Default is 'iso', which is "
              "'%%Y-%%m-%%dT%%H:%%M:%%S+00:00'.  Other shortcuts are 'epoch' "
              "for epoch time or 'us-standard' for '%%m/%%d/%%y'")
     )
    args = parser.parse_args()

    # Implement some human-understandable shortcuts for date_format
    date_format_lower = args.date_format.lower()
    if date_format_lower == 'iso':
        date_format = '%Y-%m-%dT%H:%M:%S+00:00'
    elif date_format_lower in ['unix', 'epoch']:
        date_format = 'epoch'
    elif date_format_lower == 'us-standard':
        date_format = '%m/%d/%y'
    else:
        date_format = args.date_format

    upload_file(args.filename, args.api_url, args.account, args.project_name,
                language=args.language,
                username=args.username, password=args.password,
                append=args.append, stage=args.stage,
                date_format=date_format)

if __name__ == '__main__':
    main()
