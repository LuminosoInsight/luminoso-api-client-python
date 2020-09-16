import argparse
import getpass
import os
import sys
from urllib.parse import urlparse

from .v5_client import LuminosoClient, get_token_filename
from .v5_constants import URL_BASE


def _main(argv):
    default_token_filename = get_token_filename()
    parser = argparse.ArgumentParser(
        description='Save a token for the Luminoso Daylight API.',
    )
    token_group = parser.add_mutually_exclusive_group(required=True)
    token_group.add_argument('-t', '--token',
                             help='API token (see "Settings - Tokens" in the UI)',
                             required=False)
    token_group.add_argument('-u', '--username',
                             help='The username to use for login',
                             required=False)

    parser.add_argument('-b', '--base_url', default=URL_BASE,
                        help="API root url, default: %s" % URL_BASE)
    parser.add_argument('-f', '--token_file', default=default_token_filename,
                        help=(f'File in which to store the token, default'
                              f' {default_token_filename}'))
    args = parser.parse_args(argv)

    # extract the domain from theurl
    domain = args.base_url
    if '://' in domain:
        domain = urlparse(domain).netloc
    else:
        domain = domain.split('/')[0]

    if args.token:
        LuminosoClient.save_token(args.token, domain=domain,
                                  token_file=args.token_file)

    if args.username:
        password = getpass.getpass()
        print("url: "+args.base_url)
        client = LuminosoClient.connect_with_username_and_password(url=args.base_url,
                                                                   username=args.username, password=password)
        token = client.post('/tokens/', description='generated by lumi-save-token',
                            password=password)
        client.save_token(token['token'], domain=domain,
                          token_file=args.token_file)


def main():
    """
    The setuptools entry point.
    """
    _main(sys.argv[1:])
