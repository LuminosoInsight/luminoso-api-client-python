import argparse
import sys
from urllib.parse import urlparse

from .v5_client import LuminosoClient, get_token_filename
from .v5_constants import URL_BASE


def _main(argv):
    default_domain_base = urlparse(URL_BASE).netloc
    default_token_filename = get_token_filename()
    parser = argparse.ArgumentParser(
        description=('Save a token for the Luminoso Daylight API.  If no token'
                     ' is specified, you will be prompted for a username and'
                     ' password, and a new token will be created.'),
    )
    parser.add_argument('token',
                        help='API token (see "Settings - Tokens" in the UI)',
                        nargs='?')
    parser.add_argument('-d', '--domain', default=default_domain_base,
                        help=f'API domain, default {default_domain_base}')
    parser.add_argument('-f', '--token_file', default=default_token_filename,
                        help=(f'File in which to store the token, default'
                              f' {default_token_filename}'))
    args = parser.parse_args(argv)

    LuminosoClient.save_token(token=args.token, domain=args.domain,
                              token_file=args.token_file)


def main():
    """
    The setuptools entry point.
    """
    _main(sys.argv[1:])
