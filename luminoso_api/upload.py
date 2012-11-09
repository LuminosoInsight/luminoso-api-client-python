from itertools import islice, chain
from luminoso_api import LuminosoClient
import json

ROOT_URL = 'http://localhost:5000/v3'

#http://code.activestate.com/recipes/303279-getting-items-in-batches/
def batches(iterable, size):
    sourceiter = iter(iterable)
    while True:
        batchiter = islice(sourceiter, size)
        yield chain([batchiter.next()], batchiter)

def upload(filename, username, projname):
    client = LuminosoClient.connect(ROOT_URL)
    client.post(username+'/projects/', project=projname)
    project = client.change_path(username+'/projects/'+projname)

    data = json.load(open(filename))

    counter = 0
    for batch in batches(data, 50):
        counter += 1
        documents = list(batch)
        job_id = project.upload('docs', documents)
        print 'Uploaded batch #%d into job %s' % (counter, job_id)

    print 'Committing.'
    final_job_id = project.post('docs/calculate')
    project.wait_for(final_job_id)

def main():
    import sys
    upload(sys.argv[1], sys.argv[2], sys.argv[3])

if __name__ == '__main__':
    main()
