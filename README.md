Python bindings for the Luminoso client API
===========================================

This package contains Python code for interacting with a Luminoso text
processing server through its REST API.

In this code, instead of having to authenticate each request separately,
you make a "session" object that keeps track of your login information,
and call methods on it that will be properly authenticated.

Installation
---------------
This client API is designed to be used with Python 2.6 or 2.7.

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

```
>>> from luminoso_api import LuminosoClient
>>> proj = LuminosoClient.connect('/my_billing_account/projects/my_project',
                                  username='my_username')
Password for my_username: [here you enter your password]
>>> proj.get('terms')
{u'result': [lots of terms and vectors here]}
```

When the first thing you want to do is create a new project, we've provided
a useful default URL that uses a reasonable account_id where you can create
projects:

```
>>> from luminoso_api import LuminosoClient
>>> projects = LuminosoClient.connect(username='testuser')
Password: ...
>>> print projects
<LuminosoClient for https://api.lumino.so/v3/lumi-test/projects/>
```

HTTP methods
------------

The URLs you can communicate with are documented at https://api.lumino.so/v3.
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
from luminoso_api import LuminosoClient
client = LuminosoClient.connect('/my_billing_account',username='jane', password=MY_SECRET_PASSWORD)
project_names = client.get('projects')
print project_names
```


An example of working with a project, including the `upload` method
that we provide to make it convenient to upload documents in the right format:

```python
from luminoso_api import LuminosoClient

account = LuminosoClient.connect('/janes_billing_account', username='jane')

# Create a new project by POSTing its name
account.post('projects', project='testproject')

# use that project from here on
project = account.change_path('projects/testproject')

docs = [{'title': 'First example', 'text': 'This is an example document.'},
        {'title': 'Second example', 'text': 'Examples are a great source of inspiration.'},
        {'title': 'Third example', 'text': 'Great things come in threes.'}]
project.upload('docs',docs)
job_id = project.post('docs/calculate')
```

This starts an asynchronous job, returning us its ID number. We can use
`wait\_for` to block until it's ready:

```python
project.wait_for(job_id)
```

When the project is ready:

```python
response = project.get('terms')
terms = [(term['text'], term['score']) for term in response['result']]
print terms
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
Instead of sending your documents as a list of Python dictionaries, you can upload a file
containing documents in JSON format.

The file should contain one JSON object per line (we suggest using the extension `.jsons`
to indicate that the entire file is not a single JSON object). It will look like this:

```json
{"title": "First example", "text": "This is an example document."},
{"title": "Second example", "text": "Examples are a great source of inspiration."}
{"title": "Third example", "text": "Great things come in threes."}
```

It can also be a CSV file (which can be created by Excel, for example) with columns named
`title` and `text`:

```
title   text
First example   This is an example document.
Second example  Examples are a great source of inspiration.
Third example   Great things come in threes.
```

This library installs a script called `lumi-upload` for uploading files in one of these formats.
For example, you would type at the command line:

    lumi_upload example.jsons ACCOUNT_NAME example_project

Getting the correct version of `requests`
-----------------------------------------
This API client is a simple wrapper around a Python module called `requests`.
Unfortunately, that module made some incompatible changes when it released version 1.0 in mid-December.

In case your Python environment has the new version, our setup script installs
the old version that the client is compatible with as a package called
`requests0`. This is part of the `requests-transition` package:

    https://github.com/LuminosoInsight/python-requests-transition

If you cannot import `requests0`, please re-run the setup script to get this
package:

    python setup.py install

Our next API version will include a client that supports Requests 1.0.
