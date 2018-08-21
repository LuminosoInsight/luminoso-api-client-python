"""
Provides the LuminosoClient object, a wrapper for making
properly-authenticated requests to the Luminoso REST API.
"""
import json
import logging
import os
import requests
import time
from urllib.parse import urlparse

from .v5_constants import URL_BASE
from .errors import (LuminosoError, LuminosoAuthError, LuminosoClientError,
                     LuminosoServerError)

logger = logging.getLogger(__name__)


class LuminosoClient(object):
    """
    A tool for making authenticated requests to the Luminoso API version 5.

    A LuminosoClient is a thin wrapper around the API documented at
    https://analytics.luminoso.com/api/v5/. As such, you interact with it by
    calling its methods that correspond to HTTP methods: `.get(url)`,
    `.post(url)`, `.put(url)`, `.patch(url)`, and `.delete(url)`.

    These URLs are relative to a 'base URL' for the LuminosoClient. For
    example, you can make requests for a specific project by creating a
    LuminosoClient for
    `https://analytics.luminoso.com/api/v5/projects/<project_id>`.

    Methods take parameters as keyword arguments, and encode them in the
    appropriate way for the request, which is described in the individual
    documentation for each method.

    The easiest way to create a LuminosoClient is using the
    `LuminosoClient.connect()` static method.

    In addition to the base URL, the LuminosoClient has a `root_url`,
    pointing to the root of the API, such as
    https://analytics.luminoso.com/api/v5. This is used, for example, as a
    starting point for the `change_path` method: when it gets a path starting
    with `/`, it will go back to the `root_url` instead of adding to the
    existing URL.
    """
    def __init__(self, session, url):
        """
        Create a LuminosoClient given an existing Session object that has a
        _TokenAuth object as its .auth attribute.

        It is probably easier to call LuminosoClient.connect() to handle
        the authentication for you.
        """
        self.session = session
        self.url = ensure_trailing_slash(url)
        # Don't warn this time; warning happened in connect()
        self.root_url = get_root_url(url, warn=False)

    def __repr__(self):
        return '<LuminosoClient for %s>' % self.url

    @classmethod
    def connect(cls, url=None, token_file=None, token=None):
        """
        Returns an object that makes requests to the API, authenticated
        with a saved or specified long-lived token, at URLs beginning with
        `url`.

        If no URL is specified, or if the specified URL is a path such as
        '/projects' without a scheme and domain, the client will default to
        https://analytics.luminoso.com/api/v5/.

        If neither token nor token_file are specified, the client will look
        for a token in $HOME/.luminoso/tokens.json. The file should contain
        a single json dictionary of the format
        `{'root_url': 'token', 'root_url2': 'token2', ...}`.
        """
        if url is None:
            url = '/'

        if url.startswith('http'):
            root_url = get_root_url(url)
        else:
            url = URL_BASE + '/' + url.lstrip('/')
            root_url = URL_BASE

        if token is None:
            token_file = token_file or get_token_filename()
            with open(token_file) as tf:
                token_dict = json.load(tf)
            try:
                token = token_dict[urlparse(root_url).netloc]
            except KeyError:
                raise LuminosoAuthError('No token stored for %s' % root_url)

        session = requests.session()
        session.auth = _TokenAuth(token)
        return cls(session, url)

    @staticmethod
    def save_token(token, domain='analytics.luminoso.com', token_file=None):
        """
        Take a long-lived API token and store it to a local file.  Long-lived
        tokens can be retrieved through the UI.  Optional arguments are the
        domain for which the token is valid and the file in which to store the
        token.
        """
        token_file = token_file or get_token_filename()
        if os.path.exists(token_file):
            saved_tokens = json.load(open(token_file))
        else:
            saved_tokens = {}
        saved_tokens[domain] = token
        directory, filename = os.path.split(token_file)
        if directory and not os.path.exists(directory):
            os.makedirs(directory)
        with open(token_file, 'w') as f:
            json.dump(saved_tokens, f)

    def _request(self, req_type, url, **kwargs):
        """
        Make a request via the `requests` module. If the result has an HTTP
        error status, convert that to a Python exception.
        """
        logger.debug('%s %s' % (req_type, url))
        func = getattr(self.session, req_type)
        result = func(url, **kwargs)
        try:
            result.raise_for_status()
        except requests.HTTPError:
            error = result.text
            try:
                error = json.loads(error)
            except ValueError:
                pass
            if result.status_code in (401, 403):
                error_class = LuminosoAuthError
            elif result.status_code in (400, 404, 405):
                error_class = LuminosoClientError
            elif result.status_code >= 500:
                error_class = LuminosoServerError
            else:
                error_class = LuminosoError
            raise error_class(error)
        return result

    def _json_request(self, req_type, url, **kwargs):
        """
        Make a request of the specified type and expect a JSON object in
        response.

        If the result has an 'error' value, raise a LuminosoAPIError with
        its contents. Otherwise, return the contents of the 'result' value.
        """
        response = self._request(req_type, url, **kwargs)
        try:
            json_response = response.json()
        except ValueError:
            logger.error("Received response with no JSON: %s %s" %
                         (response, response.content))
            raise LuminosoError('Response body contained no JSON. '
                                'Perhaps you meant to use get_raw?')
        return json_response

    # Simple REST operations
    def get(self, path='', **params):
        """
        Make a GET request to the given path, and return the JSON-decoded
        result.

        Keyword parameters will be converted to URL parameters.

        GET requests are requests that retrieve information without changing
        anything on the server.
        """
        params = jsonify_parameters(params)
        url = ensure_trailing_slash(self.url + path.lstrip('/'))
        return self._json_request('get', url, params=params)

    def post(self, path='', **params):
        """
        Make a POST request to the given path, and return the JSON-decoded
        result.

        Keyword parameters will be converted to form values, sent in the body
        of the POST.

        POST requests are requests that cause a change on the server,
        especially those that ask to create and return an object of some kind.
        """
        url = ensure_trailing_slash(self.url + path.lstrip('/'))
        return self._json_request('post', url, data=json.dumps(params),
                                  headers={'Content-Type': 'application/json'})

    def put(self, path='', **params):
        """
        Make a PUT request to the given path, and return the JSON-decoded
        result.

        Keyword parameters will be converted to form values, sent in the body
        of the PUT.

        PUT requests are usually requests to *update* the object represented by
        this URL. Unlike POST requests, PUT requests can be safely duplicated.
        """
        url = ensure_trailing_slash(self.url + path.lstrip('/'))
        return self._json_request('put', url, data=json.dumps(params),
                                  headers={'Content-Type': 'application/json'})

    def patch(self, path='', **params):
        """
        Make a PATCH request to the given path, and return the JSON-decoded
        result.

        Keyword parameters will be converted to form values, sent in the body
        of the PATCH.

        PATCH requests are usually requests to make *small fixes* to the
        object represented by this URL.
        """
        url = ensure_trailing_slash(self.url + path.lstrip('/'))
        return self._json_request('patch', url, data=json.dumps(params),
                                  headers={'Content-Type': 'application/json'})

    def delete(self, path='', **params):
        """
        Make a DELETE request to the given path, and return the JSON-decoded
        result.

        Keyword parameters will be converted to URL parameters.

        DELETE requests ask to delete the object represented by this URL.
        """
        params = jsonify_parameters(params)
        url = ensure_trailing_slash(self.url + path.lstrip('/'))
        return self._json_request('delete', url, params=params)

    # Useful abstractions
    def change_path(self, path):
        """
        Change the client's path. Paths with leading slashes are appended to
        the root url, otherwise paths are set relative to the current path.
        Returns a copy of the client to avoid breaking old code.
        """
        if path.startswith('/'):
            self.url = ensure_trailing_slash(self.root_url + path)
        else:
            self.url = ensure_trailing_slash(self.url + path)
        return self

    def upload(self, path, docs, **params):
        """
        A deprecated alias for post(path, docs=docs), included only for
        backward compatibility.
        """
        logger.warning('The upload method is deprecated; use post instead.')
        return self.post(path, docs=docs)

    def wait_for_build(self, interval=5, path=None):
        """
        A convenience method designed to inform you when a project build has
        completed.  It polls the API every `interval` seconds until there is
        not a build running.  At that point, it returns the "last_build_info"
        field of the project record if the build succeeded, and raises a
        LuminosoError with the field as its message if the build failed.

        If a `path` is not specified, this method will assume that its URL is
        the URL for the project.  Otherwise, it will use the specified path
        (which should be "/projects/<project_id>/").
        """
        path = path or ''
        start = time.time()
        next_log = 0
        while True:
            response = self.get(path)['last_build_info']
            if not response:
                raise ValueError('This project is not building!')
            if response['stop_time']:
                if response['success']:
                    return response
                else:
                    raise LuminosoError(response)
            elapsed = time.time() - start
            if elapsed > next_log:
                logger.info('Still waiting (%d seconds elapsed).', next_log)
                next_log += 120
            time.sleep(interval)

    def get_raw(self, path, **params):
        """
        Get the raw text of a response.

        This is only generally useful for specific URLs, such as documentation.
        """
        params = jsonify_parameters(params)
        url = ensure_trailing_slash(self.url + path.lstrip('/'))
        return self._request('get', url, params=params).text

    def save_to_file(self, path, filename, **params):
        """
        Saves binary content to a file with name filename. filename should
        include the appropriate file extension, such as .xlsx or .txt, e.g.,
        filename = 'sample.xlsx'.

        Useful for downloading .xlsx files.
        """
        url = ensure_trailing_slash(self.url + path.lstrip('/'))
        content = self._request('get', url, params=params).content
        with open(filename, 'wb') as f:
            f.write(content)


class _TokenAuth(requests.auth.AuthBase):
    """
    An object designed to attach to a requests.Session object to handle
    Luminoso API authentication.
    """
    def __init__(self, token):
        self.token = token

    def __call__(self, request):
        request.headers['Authorization'] = 'Token ' + self.token
        return request


def get_token_filename():
    """
    Return the default filename for storing API tokens.
    """
    return os.path.join(os.path.expanduser('~'), '.luminoso', 'tokens.json')


def get_root_url(url, warn=True):
    """
    Get the "root URL" for a URL, as described in the LuminosoClient
    documentation.
    """
    parsed_url = urlparse(url)

    # Make sure it's a complete URL, not a relative one
    if not parsed_url.scheme:
        raise ValueError('Please supply a full URL, beginning with http:// '
                         'or https:// .')

    # Issue a warning if the path didn't already start with /api/v5
    root_url = '%s://%s/api/v5' % (parsed_url.scheme, parsed_url.netloc)
    if warn and not parsed_url.path.startswith('/api/v5'):
        logger.warning('Using %s as the root url' % root_url)
    return root_url


def ensure_trailing_slash(url):
    """
    Ensure that a URL has a slash at the end, which helps us avoid HTTP
    redirects.
    """
    return url.rstrip('/') + '/'


def jsonify_parameters(params):
    """
    When sent in an authorized REST request, only strings and integers can be
    transmitted accurately. Other types of data need to be encoded into JSON.
    """
    result = {}
    for param, value in params.items():
        if isinstance(value, (int, str)):
            result[param] = value
        else:
            result[param] = json.dumps(value)
    return result
