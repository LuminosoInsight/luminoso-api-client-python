from .auth import LuminosoAuth
from .constants import URL_BASE
from getpass import getpass
import os
import requests
import logging
import json
logger = logging.getLogger(__name__)

def ensure_trailing_slash(url):
    return url.rstrip('/')+'/'

class LuminosoClient(object):
    def __init__(self, auth, path='/'):
        self._auth = auth
        self._session = requests.session(auth=auth)
        self.path = ensure_trailing_slash(URL_BASE+path)

    def __repr__(self):
        return '<LuminosoClient for %s>' % self.path

    @staticmethod
    def connect(path='/', username=None, password=None):
        """
        Returns an object that makes requests to the API, authenticated
        with the provided username/password, at URL paths beginning
        with `path`.

        You probably want `path` to be your account/database name, unless
        you are working with multiple databases simultaneously or don't
        know which database you need yet.
        """
        logger.info('collecting credentials')
        username = username or os.environ['USER']
        if password is None:
            password = getpass('Password for %s: ' % username)

        logger.info('creating LuminosoAuth object')
        auth = LuminosoAuth(username, password)
        return LuminosoClient(auth, path)

    @staticmethod
    def get_single(path, username=None, password=None, **params):
        """
        Gets the result of a single request, without creating a persistent
        object.

        This is useful for top-level things like listing databases:

            LuminosoClient.get_single('/.list_dbs', username=username)
        """
        path = '/' + path.lstrip('/')
        return LuminosoClient.connect(
            path, username=username, password=password
        ).get(**params)

    def _request(self, req_type, url, **kwargs):
        logger.debug('%s %s' % (req_type, url))
        func = getattr(self._session, req_type)
        result = func(url, **kwargs)
        result.raise_for_status()
        return result

    def get(self, path='', **params):
        path = ensure_trailing_slash(path.lstrip('/'))
        return self._request('get', self.path+path, params=params).json

    def post(self, path, **params):
        path = ensure_trailing_slash(path.lstrip('/'))
        return self._request('post', self.path+path, params=params).json

    def put(self, path, **params):
        path = ensure_trailing_slash(path.lstrip('/'))
        return self._request('put', self.path+path, params=params).json

    def post_data(self, path, data, content_type, **params):
        path = ensure_trailing_slash(path.lstrip('/'))
        return self._request('post', self.path+path,
            params=params,
            data=data,
            headers={'Content-Type': content_type}
        ).json

    def upload_documents(self, docs):
        """
        A convenience method for uploading a set of dictionaries representing
        documents.
        """
        json_data = json.dumps(docs)
        return self.post_data('upload_documents', json_data, 'application/json')

    def put_data(self, path, data, content_type, **params):
        path = ensure_trailing_slash(path.lstrip('/'))
        return self._request('put', self.path+path,
            params=params,
            data=data,
            headers={'Content-Type': content_type}
        ).json

    def patch(self, path, data, content_type, **params):
        path = ensure_trailing_slash(path.lstrip('/'))
        return self._request('patch', self.path+path,
            params=params,
            data=data,
            headers={'Content-Type': content_type}
        ).json

    def delete(self, path, **params):
        path = ensure_trailing_slash(path.lstrip('/'))
        return self._request('delete', self.path+path, params=params).json

    def get_raw(self, path, **params):
        """DEPRECATED: this method will disappear with api-v3"""
        path = ensure_trailing_slash(path.lstrip('/'))
        return self._request('get', self.path+path, params=params).text

    def post_raw(self, path, **params):
        """DEPRECATED: this method will disappear with api-v3"""
        path = ensure_trailing_slash(path.lstrip('/'))
        return self._request('post', self.path+path, params=params).text
