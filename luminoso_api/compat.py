import sys

# Detect Python 3
PY3 = (sys.hexversion >= 0x03000000)

if PY3:
    types_not_to_encode = (int, str)
    string_type = str
    unicode_type = str
    from urllib.parse import urlparse, parse_qs, urlunparse, quote, unquote, urlencode
else:
    types_not_to_encode = (int, long, basestring)
    string_type = basestring
    unicode_type = unicode
    from urllib2 import urlparse, quote, unquote
    from urlparse import urlparse, parse_qs, urlunparse
    from urllib import urlencode
