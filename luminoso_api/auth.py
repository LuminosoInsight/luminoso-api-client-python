import requests
from requests.utils import dict_from_cookiejar, cookiejar_from_dict

from hmac import HMAC
from hashlib import sha1
from base64 import b64encode

from .constants import URL_BASE
from .errors import LuminosoLoginError
from .jstime import epoch

import logging
logger = logging.getLogger(__name__)

import sys
PY3 = (sys.hexversion >= 0x03000000)

if PY3:
    from urllib.parse import urlparse, quote, unquote, urlencode
else:
    from urllib2 import urlparse, quote, unquote
    from urllib import urlencode


def js_compatible_quote(string):
    if not isinstance(string, basestring):
        string = str(string)
    if isinstance(string, unicode):
        string = string.encode('utf-8')
    return quote(string, safe='~@#$&()*!+=:;,.?/\'')


class LuminosoAuth(requests.auth.AuthBase):
    """Wraps REST requests with Luminoso's required authentication parameters"""
    def __init__(self, username, password, url=URL_BASE,
                 validity_ms=120000, auto_login=False, proxies=None):
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
        self._session = requests.session()
        if proxies is not None:
            self._session.proxies = proxies

        # Fetch session credentials
        self.login(username, password)

    def no_retry_copy(self):
        """
        Return a duplicate LuminosoAuth object that will not retry a connection
        """
        return LuminosoAuth(self.username, self.password,
                            url=self.url,
                            validity_ms=self._validity_ms,
                            auto_login=False,
                            proxies=self._session.proxies)

    def login(self, username, password):
        """Fetch a session key to use in this authentication context"""
        params = {'username': username, 'password': password}
        resp = self._session.post(self.url + '/user/login/', data=params)

        # Make sure the session is valid
        if resp.status_code != 200:
            logger.error('%s gave response %r' % (resp.url, resp.text))
            raise LuminosoLoginError(resp.text)

        # Save the session cookie
        self._session_cookie = resp.cookies['session']

        # Save the key_id
        self._key_id = resp.json()['result']['key_id']
        self._secret = resp.json()['result']['secret']

    def __on_response(self, resp, **kwargs):
        """Handle auto-login and update session cookies"""
        # Note: the kwargs are not used, but they're given to this method
        # by the requests hook-dispatcher, so we have to accept them.  They
        # exist because the session sets defaults for them when sending.
        if resp.status_code == 401:
            if self._auto_login:
                logger.info('request failed with 401; retrying with fresh login')
                # Do not enter an infinite retry loop
                retry_auth = self.no_retry_copy()
                resp.request.deregister_hook('response', self.__on_response)

                # Re-issue the request
                resp.request.prepare_auth(retry_auth)
                cookies = cookiejar_from_dict({'session': retry_auth._session_cookie})
                if 'Cookie' in resp.request.headers:
                    resp.request.headers.pop('Cookie', None)
                resp.request.prepare_cookies(cookies)
                new_resp = retry_auth._session.send(resp.request)
                logger.info('resent request')

                # Save the new credentials if successful
                new_result = new_resp.status_code
                if 200 <= new_result < 300:
                    # Save the new credentials
                    logger.info('retry successful')
                    self._key_id = retry_auth._key_id
                    self._secret = retry_auth._secret
                    self._session_cookie = retry_auth._session_cookie

                    # Return the new result
                    return new_resp
                else:
                    logger.error('retry failed')
                    return resp

        # If a replacement session cookie was returned, save it
        resp_cookies = dict_from_cookiejar(resp.cookies)
        if 'session' in resp_cookies:
            self._session_cookie = resp_cookies['session']
        logger.debug('Cookie: %r', self._session_cookie)

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
        pathstring = unquote(pathstring)
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
        logger.debug('auto_login is %s', 'on' if self._auto_login else 'off')

        # Determine the expiry
        expiry = epoch() + self._validity_ms

        # Get the URL parameters out
        (scheme, netloc, path, paramstring, querystring, fragment) = \
            urlparse.urlparse(req.url)
        req_params = {key: value[0] for (key, value) in
                      urlparse.parse_qs(querystring).items()}

        # Set the key id
        req_params['key_id'] = self._key_id

        # Remove auth fields
        for field in ('expires', 'sig'):
            if field in req_params:
                req_params.pop(field)

        # Determine if this is an upload
        params = req_params.copy()
        content_type = req.headers.get('Content-Type')
        content_body = None
        if content_type == 'application/x-www-form-urlencoded':
            # These are form parameters for a POST or PUT or something
            form_params = {key: value[0] for (key, value) in
                           urlparse.parse_qs(req.body).items()}
            params.update(form_params)
            content_type = None
        elif content_type == 'application/json':
            # This is a file upload
            content_body = req.body
        elif content_type is not None:
            # Some other content type??
            raise ValueError('Content-Type %s not supported' % content_type)

        # Compute the signing string
        signing_string = self.__signing_string(req, params, expiry,
                                               content_type, content_body)
        logger.debug('signing string: %r' % signing_string)

        # Sign the signing string
        sig = b64encode(HMAC(str(self._secret), signing_string, sha1).digest())

        # Pack the remaining parameters into the request
        req_params['expires'] = expiry
        req_params['sig'] = sig

        # Put the parameters back onto the request
        new_query = urlencode(req_params)
        new_url = urlparse.urlunparse((scheme, netloc, path, paramstring,
                                       new_query, fragment))
        req.prepare_url(new_url, '')
        print 'req url is', req.url

        # Load the session cookie into the request
        cookies = cookiejar_from_dict({'session': self._session_cookie})
        if 'Cookie' in req.headers:
            req.headers.pop('Cookie')
        req.prepare_cookies(cookies)

        return req
