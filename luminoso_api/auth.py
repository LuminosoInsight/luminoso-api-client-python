from __future__ import unicode_literals
import json
import requests

from .constants import URL_BASE
from .errors import LuminosoLoginError

import logging
logger = logging.getLogger(__name__)


class TokenAuth(requests.auth.AuthBase):
    def __init__(self, token):
        """
        Initialize the auth object to be used for token authentication.  The
        token can be either a long-lived API token or a short-lived token
        obtained from logging in with a username and password.
        """
        self.token = token

    def __call__(self, request):
        """
        Add an authorization header containing the token.
        """
        request.headers['Authorization'] = 'Token ' + self.token
        return request

    @classmethod
    def from_user_creds(cls, username, password, url=URL_BASE):
        """
        Obtain a short-lived token using a username and password, and use that
        token to create an auth object.
        """
        session = requests.session()
        token_resp = session.post(url.rstrip('/') + '/user/login/',
                                  data={'username': username,
                                        'password': password})
        if token_resp.status_code != 200:
            error = token_resp.text
            try:
                error = json.loads(error)['error']
            except (KeyError, ValueError):
                pass
            raise LuminosoLoginError(error)

        return cls(token_resp.json()['result']['token'])
