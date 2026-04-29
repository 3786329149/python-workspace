class AppError(Exception):
    code = "APP_ERROR"
    status_code = 500
    default_message = "application error"

    def __init__(
        self,
        message: str | None = None,
        *,
        code: str | None = None,
        status_code: int | None = None,
    ) -> None:
        self.message = message or self.default_message
        self.code = code or self.code
        self.status_code = status_code or self.status_code
        super().__init__(self.message)
