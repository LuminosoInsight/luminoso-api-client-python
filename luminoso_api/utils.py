
import logging; logger = logging.getLogger(__name__)

import requests
from .auth import LuminosoAuth
from getpass import getpass
import os

def get_session(username=None, password=None):
    """Convenience routine. Initialize a requests session using the provided
       username and password as provided, using the login username or prompting
       for a password as omitted."""

    logger.info('collecting credentials')
    username = username or os.environ['USER']
    if password is None:
        password = getpass('Password for %s: ' % username)

    logger.info('creating LuminosoAuth object')
    auth = LuminosoAuth(username, password)

    logger.info('creating requests session')
    return requests.session(auth=auth)
