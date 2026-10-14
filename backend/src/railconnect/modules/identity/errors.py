class AuthenticationError(ValueError):
    pass


class PermissionDeniedError(ValueError):
    pass


class LoginRateLimitError(ValueError):
    def __init__(self, retry_after: int) -> None:
        super().__init__("Login rate limit exceeded.")
        self.retry_after = retry_after
