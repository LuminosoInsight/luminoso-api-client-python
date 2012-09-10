class LuminosoError(Exception):
    pass

class LuminosoAuthError(LuminosoError):
    pass

class LuminosoLoginError(LuminosoAuthError):
    pass

class LuminosoSessionExpired(LuminosoAuthError):
    pass

class LuminosoClientError(LuminosoError):
    pass

class LuminosoServerError(LuminosoError):
    pass

class LuminosoAPIError(LuminosoError):
    pass
