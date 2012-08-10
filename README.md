Python bindings for the Luminoso client API
===========================================

This package contains Python code for interacting with a Luminoso text
processing server through its REST API.

In this code, instead of having to authenticate each request separately,
you make a "session" object that keeps track of your login information,
and call methods on it that will be properly authenticated.

Getting started
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
>>> db = LuminosoClient.connect('/my_username/my_database',
                                username='my_username')
Password for my_username: [here you enter your password]
>>> db.get('get_relevance')
{u'result': [lots of terms and vectors here]}
```

The URLs you can communicate with are documented at https://api.lumino.so/v2.
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
client = LuminosoClient.connect(username='jane', password=MY_SECRET_PASSWORD)
project_names = [project['name'] for project in client.get('.list_dbs')]
print project_names
```

For that reason, we have a simpler form for making a single GET request:
```python
result = LuminosoClient.get_once('.list_dbs', username='jane', password=SECRET_PASSWORD)
project_names = [project['name'] for project in result]
print project_names
```

An example of working with a project, including the `.upload_documents` method
that we provide to make it convenient to upload documents in the right format:

```python
from luminoso_api import LuminosoClient

project = LuminosoClient.connect('/jane/test-project')
project.post('create_project')
docs = [{'title': 'First example', 'text': 'This is an example document.'},
        {'title': 'Second example', 'text': 'Examples are a great source of inspiration.'}
        {'title': 'Third example', 'text': 'Great things come in threes.'}]
project.upload_documents(docs)

result = project.post('create_project')
```

When the project is ready (it shouldn't take long with 2 documents)*:

```python
response = project.get('get_relevance')
terms = [(term['text'], term['score']) for term in response['result']]
print terms
```

\* We're working on an API call to see the progress of your project.

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
