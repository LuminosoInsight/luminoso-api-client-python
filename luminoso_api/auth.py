import requests

import logging
logger = logging.getLogger(__name__)


class TokenAuth(requests.auth.AuthBase):
    def __init__(self, token):
        """
        Initialize the auth object to be used for token authentication.
        """
        self.token = token

    def __call__(self, request):
        """
        Add an authorization header containing the token.
        """
        request.headers['Authorization'] = 'Token ' + self.token
        return request
