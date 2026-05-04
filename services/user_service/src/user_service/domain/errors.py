from common.errors import AppError


class UserError(AppError):
    code = "USER_ERROR"
    status_code = 400
    default_message = "user error"


class UserAlreadyExists(UserError):
    code = "USER_ALREADY_EXISTS"
    status_code = 409
    default_message = "user already exists"


class UserNotFound(UserError):
    code = "USER_NOT_FOUND"
    status_code = 404
    default_message = "user not found"


class UserContextRequired(UserError):
    code = "USER_CONTEXT_REQUIRED"
    status_code = 401
    default_message = "user context is required"


class UserContextInvalid(UserError):
    code = "USER_CONTEXT_INVALID"
    status_code = 400
    default_message = "user context is invalid"


class UserInternalAuthFailed(UserError):
    code = "USER_INTERNAL_AUTH_FAILED"
    status_code = 403
    default_message = "invalid internal api token"


class UserPermissionDenied(UserError):
    code = "USER_PERMISSION_DENIED"
    status_code = 403
    default_message = "permission denied"
