
class LuminosoAuthError(Exception):
    pass

class LuminosoLoginError(LuminosoAuthError):
    pass

class LuminosoSessionExpired(LuminosoAuthError):
    pass
