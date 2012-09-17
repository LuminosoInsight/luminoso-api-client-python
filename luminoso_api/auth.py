import requests
from requests.utils import dict_from_cookiejar

from hmac import HMAC
from hashlib import sha1
from base64 import b64encode

from .constants import URL_BASE
from .errors import LuminosoLoginError, LuminosoSessionExpired
from .jstime import epoch

import logging
logger = logging.getLogger(__name__)

from urllib import quote
from urllib2 import urlparse


def js_compatible_quote(string):
    if not isinstance(string, basestring):
        string = str(string)
    if isinstance(string, unicode):
        string = string.encode('utf-8')
    return quote(string, safe='~@#$&()*!+=:;,.?/\'')


class LuminosoAuth(object):
    """Wraps REST requests with Luminoso's required authentication parameters"""
    def __init__(self, username, password, url=URL_BASE,
                 validity_ms=30000, auto_login=False, proxies=None):
        """Log-in to the Luminoso API

           username, password => (str) credentials to access the server
           validity_ms => milliseconds of validity for signed messages
           auto_login => remember the credentials and use them when the
                         connection times out (NOT IMPLEMENTED YET)
           session => requests session to use for queries"""

        # Store the login parameters
        self._auto_login = auto_login
        self.username = username if auto_login else None
        self.password = password if auto_login else None
        self.url = url.rstrip('/')
        parsed = urlparse.urlparse(self.url)
        self._host = parsed.netloc

        # Store the validity parameter
        self._validity_ms = validity_ms

        # Initialize the requests session
        self._session = requests.session(proxies=proxies)

        # Fetch session credentials
        self.login(username, password)

    def login(self, username, password):
        """Fetch a session key to use in this authentication context"""
        params = {'username': username, 'password': password}
        resp = self._session.post(self.url + '/.auth/login/', data=params)

        # Make sure the session is valid
        if resp.status_code == 401:
            logger.error('%s gave response %r' % (resp.url, resp.text))
            raise LuminosoLoginError

        # Save the session cookie
        self._session_cookie = resp.cookies['session']
        logger.info('Cookie: %r', self._session_cookie)

        # Save the key_id
        self._key_id = resp.json['result']['key_id']
        self._secret = resp.json['result']['secret']

    def __on_response(self, resp):
        """Handle auto-login and update session cookies"""
        if resp.status_code == 401:
            if self._auto_login:
                raise NotImplementedError

        self._session_cookie = dict_from_cookiejar(resp.cookies)['session']
        logger.info('Cookie: %r', self._session_cookie)

        return resp

    def __signing_string(self, req, params, expiry,
                         content_type=None, content_body=None):
        """Return the signing string for a proposed request"""
        # Determine if there is a payload
        if content_type is not None:
            content_hash = b64encode(sha1(content_body).digest())
        else:
            content_type = ''
            content_hash = ''

        pathstring = req.path_url.split('?')[0]
        if not pathstring.endswith('/'):
            pathstring += '/'
        # Build the list
        signing_list = [req.method,
                        self._host,
                        pathstring,
                        content_hash,
                        content_type,
                        str(expiry)]

        # Canonicalize the dictionary
        for key in sorted(params.keys()):
            signing_list.append('%s: %s' % (key,
                                            js_compatible_quote(params[key])
                                            )
                                )

        return '\n'.join(signing_list) + '\n'

    def __call__(self, req):
        # Register the on_response hook
        req.register_hook('response', self.__on_response)

        # Determine the expiry
        expiry = epoch() + self._validity_ms

        # Set the key id
        req.params['key_id'] = self._key_id

        # Determine if this is an upload
        if isinstance(req.data, dict):
            params = req.params.copy()
            params.update(req.data)
            content_type = None
            content_body = None
        else:
            params = req.params
            content_type = req.headers['Content-Type']
            content_body = req.data

        # Compute the signing string
        signing_string = self.__signing_string(req, params, expiry,
                                               content_type, content_body)
        logger.debug('signing string: %r' % signing_string)

        # Sign the signing string
        sig = b64encode(HMAC(str(self._secret), signing_string, sha1).digest())

        # Pack the remaining parameters into the request
        req.params['expires'] = expiry
        req.params['sig'] = sig

        # Load the session cookie into the request
        req.cookies['session'] = self._session_cookie

        return req
