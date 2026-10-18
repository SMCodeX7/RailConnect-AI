class InvalidReportError(ValueError):
    pass


class ReportRateLimitedError(Exception):
    def __init__(self, retry_after: int) -> None:
        super().__init__("Report submission rate limit exceeded.")
        self.retry_after = retry_after


class ReportNotFoundError(LookupError):
    pass


class ReportReviewConflictError(ValueError):
    pass


class InvalidApprovedIncidentError(ValueError):
    pass
