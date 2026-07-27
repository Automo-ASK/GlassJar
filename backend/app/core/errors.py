"""Domain exceptions raised by services and mapped to HTTP responses in main.py.

Services never raise HTTPException — they raise these, so business logic stays
framework-agnostic and every error passes through one translation point.
"""


class DomainError(Exception):
    status_code = 400

    def __init__(self, detail: str):
        self.detail = detail
        super().__init__(detail)


class InvalidInputError(DomainError):
    status_code = 400


class UnauthorizedError(DomainError):
    status_code = 401


class ForbiddenError(DomainError):
    status_code = 403


class NotFoundError(DomainError):
    status_code = 404


class ConflictError(DomainError):
    status_code = 409


class GatewayError(DomainError):
    status_code = 502
