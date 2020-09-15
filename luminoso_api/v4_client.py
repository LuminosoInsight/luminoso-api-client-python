"""
Provides the LuminosoClient object, a wrapper for making
properly-authenticated requests to the Luminoso REST API.
"""
from urllib.parse import urlparse

from .v5_client import LuminosoClient as v5LuminosoClient
from .errors import LuminosoAPIError

import logging
logger = logging.getLogger(__name__)


class LuminosoClient(v5LuminosoClient):
    """
    A tool for making authenticated requests to the Luminoso API version 4.

    A LuminosoClient is a thin wrapper around the REST API documented at
    https://daylight.luminoso.com/api/v4/. As such, you interact with it by
    calling its methods that correspond to HTTP methods: `.get(url)`,
    `.post(url)`, `.put(url)`, `.patch(url)`, and `.delete(url)`.

    These URLs are relative to a 'base URL' for the LuminosoClient. For
    example, you can make requests for a specific account by creating a
    LuminosoClient for
    `https://daylight.luminoso.com/api/v4/accounts/<account_id>`.

    Methods that make requests take parameters as keyword arguments, and encode
    them in the appropriate way for the request, which is described in the
    individual documentation for each method.

    The easiest way to create a LuminosoClient is using the
    `LuminosoClient.connect()` static method.

    In addition to the base URL, the LuminosoClient has a `root_url`,
    pointing to the root of the API, such as
    https://daylight.luminoso.com/api/v4. This is used, for example, as a
    starting point for the `change_path` method: when it gets a path starting
    with `/`, it will go back to the `root_url` instead of adding to the
    existing URL.
    """
    _URL_BASE = 'https://daylight.luminoso.com/api/v4'

    def save_token(self, *args, **kwargs):
        """
        The functionality backing this method has been removed from the v4 API.
        Please use save_token() on the v5 client, or the command-line tool
        lumi-save-token.
        """
        raise NotImplementedError(
            "The functionality backing this method has been removed from the"
            " v4 API.  Please use save_token() on the v5 client, or the"
            " command-line tool lumi-save-token."
        )

    def _json_request(self, req_type, url, **kwargs):
        """
        Make a request of the specified type and expect a JSON object in
        response.

        If the result has an 'error' value, raise a LuminosoAPIError with
        its contents. Otherwise, return the contents of the 'result' value.
        """
        json_response = super()._json_request(req_type, url, **kwargs)
        if json_response.get('error'):
            raise LuminosoAPIError(json_response.get('error'))
        return json_response['result']

    # Useful abstractions
    def change_path(self, path):
        """
        Return a new LuminosoClient for a subpath of this one.

        For example, you might want to start with a LuminosoClient for
        `https://daylight.luminoso.com/api/v4/`, then get a new one for
        `https://daylight.luminoso.com/api/v4/accounts/myaccount/`.
        You accomplish that with the following call:

            newclient = client.change_path('accounts/myaccount')

        If you start the path with `/`, it will start from the root_url
        instead of the current url:

            account_area = newclient.change_path('/accounts/myaccount')

        The advantage of using `.change_path` is that you will not need to
        re-authenticate like you would if you ran `.connect` again.

        You can use `.change_path` to split off as many sub-clients as you
        want, and you don't have to stop using the old one just because you
        got a new one with `.change_path`.
        """
        return super().client_for_path(path)

    def get_raw(self, path, **params):
        """
        Get the raw text of a response.
        """
        url = ensure_trailing_slash(self.url + path.lstrip('/'))
        return self._request('get', url, params=params).text

    @staticmethod
    def get_root_url(url, warn=True):
        """
        Get the "root URL" for a URL, as described in the LuminosoClient
        documentation.
        """
        parsed_url = urlparse(url)

        # Make sure it's a complete URL, not a relative one
        if not parsed_url.scheme:
            raise ValueError('Please supply a full URL, beginning with http://'
                             ' or https:// .')

        # Issue a warning if the path didn't already start with /api/v4
        root_url = '%s://%s/api/v4' % (parsed_url.scheme, parsed_url.netloc)
        if warn and not parsed_url.path.startswith('/api/v4'):
            logger.warning('Using %s as the root url' % root_url)
        return root_url


get_root_url = LuminosoClient.get_root_url


def ensure_trailing_slash(url):
    """
    Ensure that a URL has a slash at the end, which helps us avoid HTTP
    redirects.
    """
    return url.rstrip('/') + '/'
