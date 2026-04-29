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
