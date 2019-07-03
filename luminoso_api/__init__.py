from .errors import *
from .v4_client import LuminosoClient as V4LuminosoClient
from .v5_client import LuminosoClient as V5LuminosoClient

LuminosoClient = V5LuminosoClient
name = "luminoso-api"
