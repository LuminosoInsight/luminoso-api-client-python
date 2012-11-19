from itertools import islice, chain
from luminoso_api import LuminosoClient
from luminoso_api.json_stream import transcode_to_stream
import json
import codecs

ROOT_URL = 'https://api.lumino.so/v3'

#http://code.activestate.com/recipes/303279-getting-items-in-batches/
def batches(iterable, size):
    sourceiter = iter(iterable)
    while True:
        batchiter = islice(sourceiter, size)
        yield chain([batchiter.next()], batchiter)

def stream_json_lines(filestream):
    for line in filestream:
        line = line.strip().decode('utf-8', errors='replace')
        if line:
            yield json.loads(line)

def upload_stream(stream, account, projname):
    client = LuminosoClient.connect(ROOT_URL)
    client.post(account + '/projects/', project=projname)
    project = client.change_path(account + '/projects/' + projname)

    counter = 0
    for batch in batches(stream, 100):
        counter += 1
        documents = list(batch)
        job_id = project.upload('docs', documents, width=4)
        print 'Uploaded batch #%d into job %s' % (counter, job_id)

    print 'Committing.'
    final_job_id = project.post('docs/calculate', width=4)
    project.wait_for(final_job_id)

def upload_file(filename, account, projname):
    stream = transcode_to_stream(filename)
    upload_stream(stream_json_lines(stream), account, projname)

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('filename')
    parser.add_argument('account')
    parser.add_argument('project_name')
    args = parser.parse_args()
    upload_file(args.filename, args.account, args.project_name)

if __name__ == '__main__':
    main()
