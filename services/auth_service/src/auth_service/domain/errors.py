from common.errors import AppError


class AuthError(AppError):
    code = "AUTH_ERROR"
    status_code = 400
    default_message = "authentication error"


class AuthAlreadyExists(AuthError):
    code = "AUTH_ALREADY_EXISTS"
    status_code = 409
    default_message = "authentication identity already exists"


class AuthRegistrationFailed(AuthError):
    code = "AUTH_REGISTRATION_FAILED"
    status_code = 503
    default_message = "registration failed"
