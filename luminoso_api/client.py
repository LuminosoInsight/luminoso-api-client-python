"""
Provides the LuminosoClient object, a wrapper for making
properly-authenticated requests to the Luminoso REST API.
"""
from __future__ import unicode_literals
from .auth import TokenAuth
from .constants import URL_BASE
from .errors import (LuminosoError, LuminosoAuthError, LuminosoClientError,
    LuminosoServerError, LuminosoAPIError)
from .compat import types_not_to_encode, urlparse, encode_getpass
from getpass import getpass
import os
import requests
import logging
import json
import time
logger = logging.getLogger(__name__)

class LuminosoClient(object):
    """
    A tool for making authenticated requests to the Luminoso API version 4.

    A LuminosoClient is a thin wrapper around the REST API documented at
    https://analytics.luminoso.com/api/v4/. As such, you interact with it by
    calling its methods that correspond to HTTP methods: `.get(url)`,
    `.post(url)`, `.put(url)`, `.patch(url)`, and `.delete(url)`.

    These URLs are relative to a 'base URL' for the LuminosoClient. For
    example, you can make requests for a specific account's projects
    by creating a LuminosoClient for
    `https://analytics.luminoso.com/api/v4/projects/<account_id>`,
    or you can go deeper to create a client that makes requests for a
    specific project.

    Some methods are most useful when the client's URL refers to a project.

    These methods take parameters as keyword arguments, and encode them in
    the appropriate way for the request, which is described in the
    individual documentation for each method.

    The easiest way to create a LuminosoClient is using the
    `LuminosoClient.connect()` static method.

    In addition to the base URL, the LuminosoClient has a `root_url`,
    pointing to the root of the API, such as
    https://analytics.luminoso.com/api/v4. This is used, for example, as a
    starting point for the `change_path` method: when it gets a path starting
    with `/`, it will go back to the `root_url` instead of adding to the
    existing URL.
    """
    def __init__(self, session, url):
        """
        Create a LuminosoClient given an existing Session object that has a
        TokenAuth object as its .auth attribute.

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
    def connect(cls, url=None, username=None, password=None, token=None,
                token_file=None):
        """
        Returns an object that makes requests to the API, authenticated
        with the provided username/password, at URLs beginning with `url`.

        You can leave out the URL and get your 'default URL', a base path
        that is probably appropriate for creating projects on your
        account:

            client = LuminosoClient.connect(username=username)

        If the URL is simply a path, omitting the scheme and domain, then
        it will default to https://analytics.luminoso.com/api/v4/, which is
        probably what you want:

            client = LuminosoClient.connect('/projects/public', username=username)

        If you leave out the username, it will use your system username,
        which is convenient if it matches your Luminoso username:

            client = LuminosoClient.connect()
        """
        auto_account = False
        if url is None:
            auto_account = True
            url = '/'

        if url.startswith('http'):
            root_url = get_root_url(url)
        else:
            url = URL_BASE + '/' + url.lstrip('/')
            root_url = URL_BASE

        auth = cls._get_token_auth(username, password, token, token_file,
                                   root_url)
        session = requests.session()
        session.auth = auth
        client = cls(session, url)
        if auto_account:
            client = client.change_path('/projects/%s' %
                client._get_default_account())
        return client

    @staticmethod
    def _get_token_auth(username, password, token, token_file, root_url):
        logger.info('creating TokenAuth object')
        if token is None and username is None:
            # If no token or username was specified, check for a token saved
            # in a local file.
            token_file = token_file or get_token_filename()
            try:
                token_dict = json.load(open(token_file))
                token = token_dict.get(urlparse(root_url).netloc)
            except IOError:
                logger.info('unable to read file %s; not using saved token')
        if token is None:
            if username is None:
                username = os.environ['USER']
            if password is None:
                prompt = 'Password for %s: ' % username
                if encode_getpass:
                    prompt = prompt.encode('utf-8')
                password = getpass(prompt)
            auth = TokenAuth.from_user_creds(username, password, url=root_url)
        else:
            if username is not None:
                logger.warning('ignoring "username" argument (using token)')
            if password is not None:
                logger.warning('ignoring "password" argument (using token)')
            auth = TokenAuth(token)

        return auth

    def save_token(self, token_file=None):
        """
        Obtain the user's long-lived API token and save it in a local file.
        If the user has no long-lived API token, one will be created.
        Returns the token that was saved.
        """
        tokens = self._json_request('get', self.root_url + '/user/tokens/')
        long_lived = [token['type'] == 'long_lived' for token in tokens]
        if any(long_lived):
            dic = tokens[long_lived.index(True)]
        else:
            # User doesn't have a long-lived token, so create one
            dic = self._json_request('post', self.root_url + '/user/tokens/')
        token = dic['token']
        token_file = token_file or get_token_filename()
        if os.path.exists(token_file):
            saved_tokens = json.load(open(token_file))
        else:
            saved_tokens = {}
        saved_tokens[urlparse(self.root_url).netloc] = token
        directory, filename = os.path.split(token_file)
        if directory and not os.path.exists(directory):
            os.makedirs(directory)
        with open(token_file, 'w') as f:
            json.dump(saved_tokens, f)
        return token

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
                error = json.loads(error)['error']
            except (KeyError, ValueError):
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
        if json_response.get('error'):
            raise LuminosoAPIError(json_response.get('error'))
        return json_response['result']

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
        params = jsonify_parameters(params)
        url = ensure_trailing_slash(self.url + path.lstrip('/'))
        return self._json_request('post', url, data=params)

    def put(self, path='', **params):
        """
        Make a PUT request to the given path, and return the JSON-decoded
        result.

        Keyword parameters will be converted to form values, sent in the body
        of the PUT.

        PUT requests are usually requests to *update* the object represented by
        this URL. Unlike POST requests, PUT requests can be safely duplicated.
        """
        params = jsonify_parameters(params)
        url = ensure_trailing_slash(self.url + path.lstrip('/'))
        return self._json_request('put', url, data=params)

    def patch(self, path='', **params):
        """
        Make a PATCH request to the given path, and return the JSON-decoded
        result.

        Keyword parameters will be converted to form values, sent in the body
        of the PATCH.

        PATCH requests are usually requests to make *small fixes* to the
        object represented by this URL.
        """
        params = jsonify_parameters(params)
        url = ensure_trailing_slash(self.url + path.lstrip('/'))
        return self._json_request('patch', url, data=params)

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

    # Operations with a data payload
    def post_data(self, path, data, content_type, **params):
        """
        Make a POST request to the given path, with `data` in its body.
        Return the JSON-decoded result.

        The content_type must be set to reflect the kind of data being sent,
        which is often `application/json`.

        Keyword parameters will be converted to URL parameters. This is unlike
        other POST requests which encode those parameters in the body, because
        the body is already being used.

        This is used by the Luminoso API to upload new documents in JSON
        format.
        """
        params = jsonify_parameters(params)
        url = ensure_trailing_slash(self.url + path.lstrip('/'))
        return self._json_request('post', url,
            params=params,
            data=data,
            headers={'Content-Type': content_type}
        )

    def put_data(self, path, data, content_type, **params):
        """
        Make a PUT request to the given path, with `data` in its body.
        Return the JSON-decoded result.

        The content_type must be set to reflect the kind of data being sent,
        which is often `application/json`.

        Keyword parameters will be converted to URL parameters. This is unlike
        other PUT requests which encode those parameters in the body, because
        the body is already being used.

        This is used by the Luminoso API to update an existing document.
        """
        params = jsonify_parameters(params)
        url = ensure_trailing_slash(self.url + path.lstrip('/'))
        return self._json_request('put', url,
            params=params,
            data=data,
            headers={'Content-Type': content_type}
        )

    def patch_data(self, path, data, content_type, **params):
        """
        Make a PATCH request to the given path, with `data` in its body.
        Return the JSON-decoded result.

        The content_type must be set to reflect the kind of data being sent,
        which is often `application/json`.

        Keyword parameters will be converted to URL parameters. This is unlike
        other PUT requests which encode those parameters in the body, because
        the body is already being used.

        This verb is included for completeness and for the sake of a future API
        that might use it, but there are no existing Luminoso API endpoints
        that expect to be PATCHed.
        """
        params = jsonify_parameters(params)
        url = ensure_trailing_slash(self.url + path.lstrip('/'))
        return self._json_request('patch', url,
            params=params,
            data=data,
            headers={'Content-Type': content_type}
        )

    # Useful abstractions
    def change_path(self, path):
        """
        Return a new LuminosoClient for a subpath of this one.

        For example, you might want to start with a LuminosoClient for
        `https://analytics.luminoso.com/api/v4/`, then get a new one for
        `https://analytics.luminoso.com/api/v4/projects/myaccount/myprojectid`.
        You accomplish that with the following call:

            newclient = client.change_path('projects/myaccount/myproject_id')

        If you start the path with `/`, it will start from the root_url
        instead of the current url:

            project_area = newclient.change_path('/projects/myaccount')

        The advantage of using `.change_path` is that you will not need to
        re-authenticate like you would if you ran `.connect` again.

        You can use `.change_path` to split off as many sub-clients as you
        want, and you don't have to stop using the old one just because you
        got a new one with `.change_path`.
        """
        if path.startswith('/'):
            url = self.root_url + path
        else:
            url = self.url + path
        return self.__class__(self.session, url)

    def _get_default_account(self):
        """
        Get the ID of an account you can use to access projects.
        """
        newclient = self.__class__(self.session, self.root_url)
        account_info = newclient.get('/accounts/')
        if account_info['default_account'] is not None:
            return account_info['default_account']
        valid_accounts = [a['account_id'] for a in account_info['accounts']
                          if a['account_id'] != 'public']
        if len(valid_accounts) == 0:
            raise ValueError("Can't determine your default URL. "
                             "Please request a specific URL or ask "
                             "Luminoso for support.")
        return valid_accounts[0]

    def documentation(self):
        """
        Get the documentation that the server sends for the API.
        """
        newclient = self.__class__(self.session, self.root_url)
        return newclient.get_raw('/')

    def upload(self, path, docs, **params):
        """
        A convenience method for uploading a set of dictionaries representing
        documents. You still need to specify the URL to upload to, which will
        look like ROOT_URL/projects/myaccount/project_id/docs.
        """
        json_data = json.dumps(list(docs))
        return self.post_data(path, json_data, 'application/json', **params)

    def wait_for(self, job_id, base_path=None, interval=5):
        """
        Wait for an asynchronous task to finish.

        Unlike the thin methods elsewhere on this object, this one is actually
        specific to how the Luminoso API works. This will poll an API
        endpoint to find out the status of the job numbered `job_id`,
        repeating every 5 seconds (by default) until the job is done. When
        the job is done, it will return an object representing the result of
        that job.

        In the Luminoso API, requests that may take a long time return a
        job ID instead of a result, so that your code can continue running
        in the meantime. When it needs the job to be done to proceed, it can
        use this method to wait.

        The base URL where it looks for that job is by default `jobs/id/`
        under the current URL, assuming that this LuminosoClient's URL
        represents a project. You can specify a different URL by changing
        `base_path`.

        If the job failed, will raise a LuminosoError with the job status
        as its message.
        """
        if base_path is None:
            base_path = 'jobs/id'
        path = '%s%d' % (ensure_trailing_slash(base_path), job_id)
        start = time.time()
        next_log = 0
        while True:
            response = self.get(path)
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


def get_token_filename():
    """
    Return the default filename for storing API tokens.
    """
    return os.path.join(os.path.expanduser('~'),
                        '.luminoso',
                        'tokens.json')

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

    # Issue a warning if the path didn't already start with /api/v4
    root_url = '%s://%s/api/v4' % (parsed_url.scheme, parsed_url.netloc)
    if warn and not parsed_url.path.startswith('/api/v4'):
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
        if isinstance(value, types_not_to_encode):
            result[param] = value
        else:
            result[param] = json.dumps(value)
    return result
