from .auth import LuminosoAuth
from .constants import URL_BASE
from .errors import (LuminosoError, LuminosoAuthError, LuminosoClientError,
    LuminosoServerError)
from getpass import getpass
import os
import requests
import logging
import json
import time
logger = logging.getLogger(__name__)


def get_root_url(url):
    """
    If we have to guess a root URL, assume it contains the scheme,
    hostname, and one path component, as in "https://api.lumino.so/v4".
    """
    # make sure it's a complete URL, not a relative one
    assert ':' in url
    return '/'.join(url.split('/')[:4])

def ensure_trailing_slash(url):
    return url.rstrip('/') + '/'

def jsonify_parameters(params):
    """
    When sent in an authorized REST request, only strings and integers can be
    transmitted accurately. Other types of data need to be encoded into JSON.
    """
    result = {}
    for param, value in params.iteritems():
        if (isinstance(value, int) or isinstance(value, long)
            or isinstance(value, basestring)):
            result[param] = value
        else:
            result[param] = json.dumps(value)
    return result

class LuminosoClient(object):
    """
    A tool for making authenticated requests to the Luminoso API version 3.

    A LuminosoClient is a thin wrapper around the REST API documented at
    https://api.lumino.so/v3. As such, you interact with it by calling its
    methods that correspond to HTTP methods: `.get(url)`, `.post(url)`,
    `.put(url)`, and `.delete(url)`.

    These calls take parameters as keyword arguments, and encode them in
    the appropriate way for the request.

    A LuminosoClient requires a LuminosoAuth object. The easiest way to
    create a LuminosoClient is using the `LuminosoClient.connect(url)`
    static method, which will take in your username and optionally your
    password, or prompt you for the password if it is not specified.

    The LuminosoClient has a `root_url`, pointing to the root of the API,
    such as https://api.lumino.so/v3. It also has a `url` that forms the
    prefix of all of its requests, such as
    `https://api.lumino.so/v3/myname/projects`. You can break the URLs
    down into client objects in whatever way is convenient.
    """
    def __init__(self, auth, url, root_url=None, proxies=None):
        self._auth = auth
        self._session = requests.session(auth=auth, proxies=proxies)
        self.url = ensure_trailing_slash(url)
        self.root_url = root_url or get_root_url(url)

    def __repr__(self):
        return '<LuminosoClient for %s>' % self.url

    @staticmethod
    def connect(url='/', username=None, password=None, root_url=None,
                proxies=None):
        """
        Returns an object that makes requests to the API, authenticated
        with the provided username/password, at URLs beginning with `url`.

        If the URL is simply a path, omitting the scheme and domain, then
        it will default to https://api.lumino.so, which is probably what
        you want.

        You probably want `path` to include your account/database name, unless
        you are working with multiple databases simultaneously or don't
        know which database you need yet.

        `proxies` is a dictionary from URL schemes (like 'http') to proxy
        servers, in the same form used by the `requests` module.
        """
        if url.startswith('/'):
            url = URL_BASE + url

        if root_url is None:
            root_url = get_root_url(url)

        logger.info('collecting credentials')
        username = username or os.environ['USER']
        if password is None:
            password = getpass('Password for %s: ' % username)

        logger.info('creating LuminosoAuth object')
        auth = LuminosoAuth(username, password, url=root_url, proxies=proxies)
        return LuminosoClient(auth, url)

    def _request(self, req_type, url, **kwargs):
        logger.debug('%s %s' % (req_type, url))
        func = getattr(self._session, req_type)
        result = func(url, **kwargs)
        try:
            result.raise_for_status()
        except requests.HTTPError:
            error = result.text
            if result.status_code == 401:
                error_class = LuminosoAuthError
            if result.status_code in (404, 405):
                error_class = LuminosoClientError
            elif result.status_code >= 500:
                error_class = LuminosoServerError
            else:
                error_class = LuminosoError
            raise error_class(error)
        return result

    # Simple REST operations
    def get(self, path='', **params):
        params = jsonify_parameters(params)
        url = ensure_trailing_slash(self.url + path.lstrip('/'))
        return self._request('get', url, params=params).json

    def post(self, path='', **params):
        params = jsonify_parameters(params)
        url = ensure_trailing_slash(self.url + path.lstrip('/'))
        return self._request('post', url, data=params).json

    def put(self, path='', **params):
        params = jsonify_parameters(params)
        url = ensure_trailing_slash(self.url + path.lstrip('/'))
        return self._request('put', url, data=params).json

    def delete(self, path='', **params):
        params = jsonify_parameters(params)
        url = ensure_trailing_slash(self.url + path.lstrip('/'))
        return self._request('delete', url, params=params).json

    # Operations with a data payload
    def post_data(self, path, data, content_type, **params):
        params = jsonify_parameters(params)
        url = ensure_trailing_slash(self.url + path.lstrip('/'))
        return self._request('post', url,
            params=params,
            data=data,
            headers={'Content-Type': content_type}
        ).json

    def put_data(self, path, data, content_type, **params):
        params = jsonify_parameters(params)
        url = ensure_trailing_slash(self.url + path.lstrip('/'))
        return self._request('put', url,
            params=params,
            data=data,
            headers={'Content-Type': content_type}
        ).json

    def patch(self, path, data, content_type, **params):
        params = jsonify_parameters(params)
        url = ensure_trailing_slash(self.url + path.lstrip('/'))
        return self._request('patch', url,
            params=params,
            data=data,
            headers={'Content-Type': content_type}
        ).json

    # Useful abstractions
    def change_path(self, path):
        """
        Return a new LuminosoClient for a subpath of this one.

        For example, you might want to start with a LuminosoClient for
        `https://api.lumino.so/v3/`, then get a new one for
        `https://api.lumino.so/v3/myname/projects/myproject`. You
        accomplish that with the following call:

            newclient = client.change_path('myname/projects/myproject')

        If you start the path with `/`, it will start from the root_url
        instead of the current url:

            project_area = newclient.change_path('/myname/projects')

        The advantage of using `.change_path` is that you will not need to
        re-authenticate like you would if you ran `.connect` again.

        You can
        use `.change_path` to split off as many sub-clients as you want, and
        you don't have to stop using the old one just because you got a new
        one with `.change_path`.
        """
        if path.startswith('/'):
            url = self.root_url + path
        else:
            url = self.url + path
        return LuminosoClient(self._auth, url, self.root_url)

    def documentation(self):
        """
        Get the documentation that the server sends for the API.
        """
        newclient = LuminosoClient(self._auth, self.root_url, self.root_url)
        return newclient._get_raw('/')

    def upload(self, path, docs):
        """
        A convenience method for uploading a set of dictionaries representing
        documents. You still need to specify the URL to upload to, which will
        look like ROOT_URL/myname/projects/projectname/docs.
        """
        json_data = json.dumps(docs)
        return self.post_data(path, json_data, 'application/json')

    def wait_for_assoc(self, path='', min_version=0, interval=5):
        """
        DEPRECATED: use wait_for instead.

        Poll every 5 seconds until you get an assoc_space with a version
        greater than or equal to `min_version`. Returns the version
        number.
        """
        while True:
            response = self.get(path)
            if response['error']:
                raise LuminosoError(str(response['error']))
            else:
                result = response['result']
                if result['current_assoc_version'] >= min_version:
                    return result['current_assoc_version']
                time.sleep(interval)

    def wait_for(self, job_id, basepath=None, interval=5):
        """
        Poll every 5 seconds until the job numbered `job_id` is done.
        """
        if basepath is None:
            basepath = 'jobs/id'
        path = '%s%d' % (ensure_trailing_slash(basepath), job_id)
        while True:
            response = self.get(path)
            if response['error']:
                raise LuminosoError(str(response['error']))
            else:
                result = response['result']
                if result['stop_time']:
                    return result
                time.sleep(interval)

    # Internal stuff
    def _get_raw(self, path, **params):
        """
        Get the raw text of a response.

        Marked as a private function because it is only useful for specific
        URLs, such as documentation.
        """
        url = ensure_trailing_slash(self.url + path.lstrip('/'))
        return self._request('get', url, params=params).text
