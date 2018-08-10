import argparse
import csv
import json
import os
import sys
from signal import signal, SIGPIPE, SIG_DFL
from urllib.parse import urlparse

from .client import LuminosoClient
from .constants import URL_BASE
from .errors import LuminosoError

# Python raises IOError when reading process (such as `head`) closes a pipe.
# Setting SIG_DFL as the SIGPIPE handler prevents this program from crashing.
signal(SIGPIPE, SIG_DFL)


DESCRIPTION = "Access the luminoso API via the command line."

USAGE = """
Supply an HTTP verb and a path, with optional parameters.
Output is returned as JSON, CSV, or an error message.

Parameters may be specified in one of three ways:

A user-friendly key=value parameter list:
    -p 'key=value' -p 'key2=value'

A JSON object from the command line:
    -j '{"key": "value", "key2": "value"}'

A file containing a JSON object:
    filename.json

Parameter options may be combined. A JSON object on the command line is merged
over one in a file, and -p options are merged over both.

GET and DELETE requests append the parameters to the URL.
POST, PUT, and PATCH send the given parameters as the body of the
request with Content-Type set to 'application/json'.
"""


def _print_csv(result):
    """Print a JSON list of JSON objects in CSV format."""
    first_line = result[0]
    w = csv.DictWriter(sys.stdout, fieldnames=sorted(first_line.keys()))
    w.writeheader()
    for line in result:
        w.writerow(line)


def _read_params(input_file, json_body, p_params):
    """Read parameters from input file, -j, and -p arguments, in that order."""
    params = {}
    try:
        if input_file:
            params.update(json.load(input_file))
        if json_body is not None:
            params.update(json.loads(json_body))
    except ValueError as e:
        raise ValueError("input is not valid JSON: %s" % e)
    try:
        params.update({p.split('=', 1)[0]: p.split('=', 1)[1] for p in p_params})
    except IndexError:
        raise ValueError("--param arguments must have key=value format")
    return params


def _main():
    parser = argparse.ArgumentParser(
        description=DESCRIPTION, epilog=USAGE,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('-b', '--base-url', default=URL_BASE,
                        help="API root url, default: %s" % URL_BASE)
    parser.add_argument('-t', '--token', help="API authentication token")
    parser.add_argument('-s', '--save-token', action='store_true',
                        help="save --token for --base-url to"
                             " ~/.luminoso/tokens.json")
    parser.add_argument('-p', '--param', action='append', default=[],
                        help="key=value parameters")
    parser.add_argument('-j', '--json-body', help="JSON object parameter")
    parser.add_argument('-c', '--csv', action='store_true',
                        help="print output in CSV format")
    parser.add_argument('method',
                        choices=['get', 'post', 'put', 'patch', 'delete'])
    parser.add_argument('path')
    parser.add_argument('input_file', nargs='?', type=open)

    args = parser.parse_args()

    if args.save_token:
        if not args.token:
            raise Exception("error: no token provided")
        LuminosoClient.save_token(args.token,
                                  domain=urlparse(args.base_url).netloc)

    client = LuminosoClient.connect(url=args.base_url, token=args.token)

    if args.method == 'delete':
        confirm = input('confirm %s %s? [Y/n] ' % (args.method, args.path))
        if confirm not in ('', 'y', 'Y'):
            sys.exit(os.EX_OK)

    params = _read_params(args.input_file, args.json_body, args.param)
    func = getattr(client, args.method)
    result = func(args.path, **params)

    if args.csv:
        try:
            _print_csv(result)
        except TypeError as e:
            raise ValueError("output not able to be displayed as CSV. %s" % e)
    else:
        print(json.dumps(result, sort_keys=True, indent=4))


def main():
    try:
        _main()
    except (Exception, LuminosoError) as e:
        print("lumi-api: %s" % e, file=sys.stderr)
        sys.exit(1)
