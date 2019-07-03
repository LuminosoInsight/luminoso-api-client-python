Python bindings for the Luminoso client API
===========================================

This package contains Python code for interacting with a Luminoso text
processing server through its REST API.

Important note: API version and client version
----------------------------------------------

This page covers the client that connects to the v4 API; this client is the
object named `luminoso_api.V4LuminosoClient`, which is an alias for
`luminoso_api.v4_client.LuminosoClient`.

Please note that the v4 client can only be used to connect to v4 endpoints,
which do not include any science endpoints for building or interacting with
projects.  This client can only be used for user and account management.

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
>>> client = LuminosoClient.connect('/user/', username='my_username')
Password for my_username: [here you enter your password]
>>> client.get('profile')
[your user profile here]
```

Or you can connect using an existing API token:

```python
from luminoso_api import LuminosoClient
proj = LuminosoClient.connect('/user', token='my-api-token-here')
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

HTTP methods
------------

The URLs you can communicate with are documented at https://daylight.luminoso.com/api/v4.
That documentation is the authoritative source for what you can do with the
API.

A LuminosoClient object has methods such as `.get`, `.post`, and `.put`,
which correspond to the corresponding HTTP methods that the API uses. For
example, `.get` is used for retrieving information without changing anything,
`.post` is generally used for creating new things or taking actions, and `.put`
is generally used for updating information.
