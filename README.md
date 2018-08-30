Python bindings for the Luminoso client API
===========================================

This package contains Python code for interacting with a Luminoso text
processing server through its REST API.

In this code, instead of having to authenticate each request separately,
you make a "session" object that keeps track of your login information,
and call methods on it that will be properly authenticated.

Installation
---------------
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

```python
from luminoso_api import V5LuminosoClient
project = V5LuminosoClient.connect('/projects/my_project_id', token='my_token')

# And then, for instance:
docs = project.get('docs', limit=10)
```

Instead of specifying the token when connecting, you can also use the
LuminosoClient to save a token to a file, at which point you can connect
without having to specify a token.

```python
from luminoso_api import V5LuminosoClient
V5LuminosoClient.save_token(token='my_token')
project = V5LuminosoClient.connect('/projects/my_project_id')
docs = project.get('docs', limit=10)
```

Note that the LuminosoClient will ensure that slashes are put in the right
places, so that all of the following calls will go to the endpoint
`https://analytics.luminoso.com/api/v5/projects/my_project_id/docs/`:

```python
V5LuminosoClient.connect('/projects/my_project_id').get('docs')
V5LuminosoClient.connect('/projects/my_project_id').get('/docs')
V5LuminosoClient.connect('/projects/my_project_id').get('docs/')
V5LuminosoClient.connect('/projects/my_project_id').get('/docs/')
V5LuminosoClient.connect('/projects/my_project_id/').get('docs')
V5LuminosoClient.connect('/projects/my_project_id/').get('/docs')
V5LuminosoClient.connect('/projects/my_project_id/').get('docs/')
V5LuminosoClient.connect('/projects/my_project_id/').get('/docs/')
```

HTTP methods
------------

The URLs you can communicate with are documented at https://analytics.luminoso.com/api/v5/.
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
project (also known as a database), but one case where you don't is to get a list of projects in the first place:

```python
from luminoso_api import V5LuminosoClient
client = V5LuminosoClient.connect()
project_info_list = client.get('/projects/')
print(project_info_list)
```

An example of working with a project, including the use of the convenience method `.wait_for_build`:

```python
from luminoso_api import V5LuminosoClient
client = V5LuminosoClient.connect()

# Create a new project by POSTing its name and language
project_id = client.post('/projects/', name='testproject', language='en')['project_id']

# use that project from here on
client.change_path('/projects/' + project_id)

docs = [{'title': 'First example', 'text': 'This is an example document.'},
        {'title': 'Second example', 'text': 'Examples are a great source of inspiration.'},
        {'title': 'Third example', 'text': 'Great things come in threes.'}]
client.post('upload', docs=docs)
client.post('build')
client.wait_for_build()

# When the previous call finishes:
response = client.get('concepts')
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

Uploading from the command line
-------------------------------

While there is no dedicated command to upload documents, this library does
include the command `lumi-api`, which can be used to access the API in general
and to upload documents in particular.  Run `lumi-api -h` for more information.