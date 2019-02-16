Python bindings for the Luminoso client API
===========================================

This package contains Python code for interacting with a Luminoso text
processing server through its REST API.

Important note: API version and client version
----------------------------------------------

This page covers the client that connects to the v4 API; this client is the
object named `luminoso_api.LuminosoClient`, which is an alias for
`luminoso_api.v4_client.LuminosoClient`.

However, the v5 API is now available, as is a client for using it.  That client
can be accessed as `luminoso_api.V5LuminosoClient` (or directly at
`luminoso_api.v5_client.LuminosoClient`).  Documentation for the new client can
be found
[here](https://github.com/LuminosoInsight/luminoso-api-client-python/blob/master/V5_README.md).
When the sunset period for the v4 API ends on March 3, 2019, we will remove
the v4 version of the client, and `luminoso_api.LuminosoClient` will become an
alias for the v5 client.

Using this client
=================

In this code, instead of having to authenticate each request separately,
you make a "session" object that keeps track of your login information,
and call methods on it that will be properly authenticated.

Installation
---------------
This client API is designed to be used with Python 2.6, 2.7, 3.3, or 3.4.

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

You can connect using a username and password:

```python
>>> from luminoso_api import LuminosoClient
>>> proj = LuminosoClient.connect('/projects/account_id/my_project_id',
                                  username='my_username')
Password for my_username: [here you enter your password]
>>> proj.get('terms')
[lots of terms and vectors here]
```

Or you can connect using an existing API token:

```python
from luminoso_api import LuminosoClient
proj = LuminosoClient.connect('/projects/account_id/my_project_id',
                              token='my-api-token-here')
```

You can even save your API token to a file on your computer and load it
automatically, so that you don't have to specify any credentials:

```python
from luminoso_api import LuminosoClient
client = LuminosoClient.connect(token='my-api-token-here')
# This will save a non-expiring token, regardless of whether you are currently
# using that token or some other token.
client.save_token()
# Now you can exit Python, restart your computer, etc., and your token will
# still be saved when you come back.
proj = LuminosoClient.connect('/projects/account_id/my_project_id')
```

When you connect without specifying a URL, the URL will be set to your default
account_id under /projects:

```python
>>> from luminoso_api import LuminosoClient
>>> projects = LuminosoClient.connect(username='testuser')
Password: ...
>>> print(projects)
<LuminosoClient for https://analytics.luminoso.com/api/v4/projects/lumi-test/>
```

HTTP methods
------------

The URLs you can communicate with are documented at https://analytics.luminoso.com/api/v4.
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
client = LuminosoClient.connect(username='jane', password=MY_SECRET_PASSWORD)
# this points to the /projects/janeaccount/ endpoint by default,
# where janeaccount is the account_id of jane's default account
project_info_list = client.get()
print(project_info_list)
```


An example of working with a project, including the `upload` method
that we provide to make it convenient to upload documents in the right format:

```python
from luminoso_api import LuminosoClient

projects = LuminosoClient.connect(username='jane')

# Create a new project by POSTing its name
project_id = projects.post(name='testproject')['project_id']

# use that project from here on
project = projects.change_path(project_id)

docs = [{'title': 'First example', 'text': 'This is an example document.'},
        {'title': 'Second example', 'text': 'Examples are a great source of inspiration.'},
        {'title': 'Third example', 'text': 'Great things come in threes.'}]
project.upload('docs', docs)
job_id = project.post('docs/recalculate')
```

This starts an asynchronous job, returning us its ID number. We can use
`wait_for` to block until it's ready:

```python
project.wait_for(job_id)
```

When the project is ready:

```python
response = project.get('terms')
terms = [(term['text'], term['score']) for term in response]
print(terms)
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
