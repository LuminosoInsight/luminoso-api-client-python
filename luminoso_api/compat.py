import sys, os

# Detect Python 3
PY3 = (sys.hexversion >= 0x03000000)
OSNT = (os.name == 'nt')
encode_getpass = False

if PY3:
    types_not_to_encode = (int, str)
    string_type = str
    from urllib.parse import urlparse
else:
    types_not_to_encode = (int, long, basestring)
    string_type = basestring
    from urlparse import urlparse
    if OSNT:
        encode_getpass = True
