from typing import ClassVar

from pydantic import BaseModel, ConfigDict


class ErrorPayload(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    error_code: str
    message: str
    retryable: bool


class MusicMCPError(Exception):
    error_code: ClassVar[str] = "music_mcp_error"
    retryable: ClassVar[bool] = False

    def to_payload(self) -> ErrorPayload:
        return ErrorPayload(
            error_code=self.error_code,
            message=str(self),
            retryable=self.retryable,
        )


class InvalidRequestError(MusicMCPError):
    error_code = "invalid_request"


class AuthenticationRequiredError(MusicMCPError):
    error_code = "authentication_required"


class AuthenticationExpiredError(MusicMCPError):
    error_code = "authentication_expired"


class ResourceNotFoundError(MusicMCPError):
    error_code = "not_found"


class RateLimitedError(MusicMCPError):
    error_code = "rate_limited"
    retryable = True


class UpstreamUnavailableError(MusicMCPError):
    error_code = "upstream_unavailable"
    retryable = True


class UpstreamResponseError(MusicMCPError):
    error_code = "upstream_response_error"


class UnsupportedOperationError(MusicMCPError):
    error_code = "unsupported_operation"
