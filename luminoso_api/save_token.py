import argparse
import getpass
import os
import sys
from urllib.parse import urlparse

from .v4_client import LuminosoClient as V4LuminosoClient
from .v5_client import LuminosoClient, get_token_filename
from .v5_constants import URL_BASE


def _main(argv):
    default_domain_base = urlparse(URL_BASE).netloc
    default_token_filename = get_token_filename()
    parser = argparse.ArgumentParser(
        description='Save a token for the Luminoso Daylight API.',
    )
    token_group = parser.add_mutually_exclusive_group(required=True)
    token_group.add_argument('-t','--token',
                        help='API token (see "Settings - Tokens" in the UI)',
                        required=False)
    token_group.add_argument('-u','--username',
                        help='The username to use for login',
                        required=False)

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

    if args.token:
        LuminosoClient.save_token(args.token, domain=domain,
                                token_file=args.token_file)

    if args.username:
        print("got username: "+args.username)
        print("domainbase: "+args.domain)
        password = getpass.getpass()
        client = V4LuminosoClient.connect(url=args.domain,username=args.username,password=password)
        client.save_token()



def main():
    """
    The setuptools entry point.
    """
    _main(sys.argv[1:])
