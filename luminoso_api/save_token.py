import argparse
import os
import sys
from urllib.parse import urlparse

from .v5_client import LuminosoClient, get_token_filename
from .v5_constants import URL_BASE


def _main(argv):
    default_domain_base = urlparse(URL_BASE).netloc
    default_token_filename = get_token_filename()
    parser = argparse.ArgumentParser(
        description='Save a token for the Luminoso Daylight API.',
    )
    parser.add_argument('token',
                        help='API token (see "Settings - Tokens" in the UI)')
    parser.add_argument('domain', default=default_domain_base,
                        help=f'API domain, default {default_domain_base}',
                        nargs='?')
    parser.add_argument('-f', '--token_file', default=default_token_filename,
                        help=(f'File in which to store the token, default'
                              f' {default_token_filename}'))
    args = parser.parse_args(argv)

    # Make this as friendly as possible: turn any of "daylight.luminoso.com",
    # "daylight.luminoso.com/api/v5", or "http://daylight.luminoso.com/", into
    # just the domain
    domain = args.domain
    if '://' in domain:
        domain = urlparse(domain).netloc
    else:
        domain = domain.split('/')[0]

    LuminosoClient.save_token(args.token, domain=domain,
                              token_file=args.token_file)


def main():
    """
    The setuptools entry point.
    """
    _main(sys.argv[1:])
