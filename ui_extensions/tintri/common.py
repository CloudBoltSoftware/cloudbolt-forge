import json


class TintriError(Exception):
    """
    Base class of all Tintri specific exceptions
    
    Args:
        cause (str): Error cause
        message (str) : Error message
        details (str): Error details
    """

    def __init__(self, cause=None, message=None, details=None):
        self.cause = cause
        self.message = message
        self.details = details
        Exception.__init__(self, cause, message, details)


class TintriServerError(TintriError):
    """
    Exception returned from Tintri server (VMstore or TGC)
    
    Args:
        status (int): HTTP status code from a REST call
        code (str): Tintri error code
        details (str): Error details 
    """

    def __init__(self, status, code=None, cause=None, message=None, details=None):
        self.status = status
        self.code = code
        TintriError.__init__(self, cause=cause, message=message, details=details)


class TintriAuthenticationError(TintriServerError):
    """
    Tintri authentication error (HTTP status code: 403)
    
    Args:
        cause (str): Error cause
        message (str) : Error message
        details (str): Error details
    """

    def __init__(self, code, message, details):
        TintriServerError.__init__(self, 403, code=code, message=message, details=details)


class TintriAuthorizationError(TintriServerError):
    """
    Tintri authorization error (HTTP status code: 403)

    Args:
        cause (str): Error cause
        message (str) : Error message
        details (str): Error details
    """

    def __init__(self, code, message, details):
        TintriServerError.__init__(self, 403, code=code, message=message, details=details)


class TintriInvalidSessionError(TintriServerError):
    """
    Tintri invalid session error (HTTP status code: 401)
    
    Args:
        cause (str): Error cause
        message (str) : Error message
        details (str): Error details
    """

    def __init__(self, code, message, details):
        TintriServerError.__init__(self, 401, code=code, message=message, details=details)


class TintriBadRequestError(TintriServerError):
    """
    Tintri bad request error (HTTP status code: 400)
    
    Args:
        cause (str): Error cause
        message (str) : Error message
        details (str): Error details
    """

    def __init__(self, code, message, details):
        TintriServerError.__init__(self, 400, code=code, message=message, details=details)

class TintriJSONEncoder(json.JSONEncoder):
    def default(self, o):
        if o is None: return None
        else: return o.__dict__
