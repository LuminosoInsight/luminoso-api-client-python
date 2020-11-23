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
You interact with the API using a V4LuminosoClient object, which sends HTTP
requests to URLs starting with a given path, and keeps track of your
authentication information.

You can connect using a username and password:

```python
>>> from luminoso_api import V4LuminosoClient
>>> client = V4LuminosoClient.connect('/user/', username='my_username')
Password for my_username: [here you enter your password]
>>> client.get('profile')
[your user profile here]
```

Or you can connect using an existing API token:

```python
from luminoso_api import V4LuminosoClient
proj = V4LuminosoClient.connect('/user', token='my-api-token-here')
```

You can save an API token locally so that you do not need to specify it each
time, though that functionality no longer exists in the v4 client; to do so, use
either the v5 client or the `lumi-save-token` command.

Note that while saved tokens are specific for each domain (tokens for
`daylight.luminoso.com` will not work on an onsite installation, or vice
versa), the token for a given domain will provide access to both the v4 and
v5 APIs.  You do not need to save separate tokens for each.

HTTP methods
------------

The URLs you can communicate with are documented at https://daylight.luminoso.com/api/v4.
That documentation is the authoritative source for what you can do with the
API.

A V4LuminosoClient object has methods such as `.get`, `.post`, and `.put`,
which correspond to the corresponding HTTP methods that the API uses. For
example, `.get` is used for retrieving information without changing anything,
`.post` is generally used for creating new things or taking actions, and `.put`
is generally used for updating information.
