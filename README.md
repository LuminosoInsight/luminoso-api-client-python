Python bindings for the Luminoso client API
===========================================

This package contains Python code for interacting with a Luminoso text
processing server through its REST API.

In this code, instead of having to authenticate each request separately,
you make a "session" object that keeps track of your login information,
and call methods on it that will be properly authenticated.

Installation
------------
This client API is designed to be used with Python 3.

You can download and install it using a Python package manager:

    pip install luminoso-api

or

    easy_install luminoso-api

Or you can download this repository and install it the usual way:

    python setup.py install

If you are installing into the main Python environment on a Mac or Unix
system, you will probably need to prefix those commands with `sudo` and
enter your password, as in `sudo python setup.py install`.

Getting started
---------------
You interact with the API using a LuminosoClient object, which sends HTTP
requests to URLs starting with a given path, and keeps track of your
authentication information.

Before you can connect to an API, you will need to go to the UI on the web and
get a long-lived API token.  (To get a token, go to the "User settings" option
in the upper right dropdown menu, and click the "API tokens" button.)  Once you
have one, you can use it to connect to the API.

Note that saved tokens are specific for each domain (tokens for
`daylight.luminoso.com` will not work on an onsite installation, or vice
versa).

```python
from luminoso_api import LuminosoClient
project = LuminosoClient.connect('/projects/my_project_id', token='my_token')

# And then, for instance:
docs = project.get('docs', limit=10)
```

Instead of specifying the token when connecting, you can also use the
LuminosoClient to save a token to a file, at which point you can connect
without having to specify a token.  (Saving a token can also be done at the
command line; see "Using the API from the command line" below.)

```python
from luminoso_api import LuminosoClient
LuminosoClient.save_token('my_token')
project = LuminosoClient.connect('/projects/my_project_id')
docs = project.get('docs', limit=10)
```

Note that all leading and trailing slashes in paths are optional, because the
LuminosoClient ensures that slashes are put in the right places.  For example,
all of the following calls will go to the endpoint
`https://daylight.luminoso.com/api/v5/projects/my_project_id/docs/`:

```python
LuminosoClient.connect('/projects/my_project_id').get('docs')
LuminosoClient.connect('projects/my_project_id/').get('/docs')
LuminosoClient.connect('/projects/my_project_id/').get('docs/')
LuminosoClient.connect('projects/my_project_id').get('/docs/')
```

The connect method also provides an optional timeout parameter. This will set
both the connect and read timeout used in the underlying request. If this is set
and the connection or reading the response on the requests times out then a
LuminosoTimeoutError exception will be raised.

HTTP methods
------------

The URLs you can communicate with are documented at https://daylight.luminoso.com/api/v5/.
That documentation is the authoritative source for what you can do with the
API, and this Python code is just here to help you do it.

A LuminosoClient object has methods such as `.get`, `.post`, and `.put`,
which correspond to the corresponding HTTP methods that the API uses. For
example, `.get` is used for retrieving information without changing anything,
`.post` is generally used for creating new things or taking actions, and `.put`
is generally used for updating information.

Examples
--------

Most of the time, you'll want your LuminosoClient to refer to a particular
project, but one case where you don't is to get a list of projects in the first
place:

```python
from luminoso_api import LuminosoClient
client = LuminosoClient.connect()
project_info_list = client.get('/projects/')
print(project_info_list)
```

An example of working with a project, including the use of the convenience method `.wait_for_build`:

```python
from luminoso_api import LuminosoClient
client = LuminosoClient.connect()

# Create a new project by POSTing its name and language
project_id = client.post('/projects/', name='testproject', language='en')['project_id']

# use that project from here on
project = client.client_for_path('/projects/' + project_id)

docs = [{'title': 'First example', 'text': 'This is an example document.'},
        {'title': 'Second example', 'text': 'Examples are a great source of inspiration.'},
        {'title': 'Third example', 'text': 'Great things come in threes.'}]
project.post('upload', docs=docs)
project.post('build')
project.wait_for_build()

# When the previous call finishes:
response = project.get('concepts')
for concept in response['result']:
    print('%s - %f' % (concept['texts'][0], concept['relevance']))
```

Vectors
-------
The semantics of terms are represented by "vector" objects, which this API
will return as inscrutable base64-encoded strings like this:

    'WAB6AJG6kL_6D_6yAHE__R9kSAE8BlgKMo_80y8cCOCCSN-9oAQcABP_TMAFhAmMCUA'

If you want to look inside these vectors and compare them to each other,
download our library called `pack64`, available as `pip install pack64`. It
will turn these into NumPy vectors, so it requires NumPy.

```python
>>> from pack64 import unpack64
>>> unpack64('WAB6AJG6kL_6D_6y')
array([ 0.00046539,  0.00222015, -0.08491898, -0.0014534 , -0.00127411], dtype=float32)
```

Using the API from the command line
-----------------------------------

This library includes experimental tools usable from the command line:
`lumi-save-token`, `lumi-api`, `lumi-upload`, and `lumi-download`.  Running them
with `-h` will provide more detailed documentation on available parameters.  In
addition, the following examples may provide some guidance on using `lumi-api`
to access the API:

```
# save a token obtained from the UI - note that you must run this first for the following commands to work!
# (also, this is not a real API token, but yours will look similar)
lumi-save-token gF1XgbExN30O4DfBXse95vCjm6V069Ko

# get a project list
lumi-api -b https://daylight.luminoso.com/api/v5/ get /projects

# get a project list in CSV format
lumi-api -b https://daylight.luminoso.com/api/v5/ get /projects -c

# create a project
lumi-api -b https://daylight.luminoso.com/api/v5/ post /projects/ -p 'name=project name' -p 'language=en'

# upload documents
# my_data.json format: {"docs":[{"text": "..", "title": "..", "metadata": [..]}, {"text": "..", "title": "..", "metadata": [..]}]}
lumi-api -b https://daylight.luminoso.com/api/v5/ post /projects/my_project_id/upload my_data.json

# build project
# this takes time, if you want to be notified via email when the build is done, add -j '{"notify": true}' parameter
lumi-api -b https://daylight.luminoso.com/api/v5/ post /projects/my_project_id/build

# get concepts from project
lumi-api -b https://daylight.luminoso.com/api/v5/ get /projects/my_project_id/concepts

# get project's match counts
lumi-api -b https://daylight.luminoso.com/api/v5/ get /projects/my_project_id/concepts/match_counts

# create a saved concept
lumi-api -b https://daylight.luminoso.com/api/v5/ post /projects/my_project_id/concepts/saved -j '{"concepts": [{"texts": ["My new concept text"]}]}'
```
