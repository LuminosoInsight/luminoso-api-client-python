from .errors import *
from .v4_client import LuminosoClient as V4LuminosoClient
from .v5_client import LuminosoClient as V5LuminosoClient
from .version import VERSION

LuminosoClient = V5LuminosoClient
name = "luminoso-api"
__version__ = VERSION