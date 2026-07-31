from dataclasses import dataclass

from netease_music_mcp.config import Settings
from netease_music_mcp.domain.enums import AuthenticationState
from netease_music_mcp.domain.errors import AuthenticationRequiredError


@dataclass(frozen=True, repr=False)
class AuthenticationProvider:
    """Assemble authentication in one place without exposing secret values."""

    _cookie: str | None
    _music_u: str | None
    _csrf: str | None
    configured_user_id: str | None

    @classmethod
    def from_settings(cls, settings: Settings) -> "AuthenticationProvider":
        return cls(
            _cookie=settings.cookie.get_secret_value() if settings.cookie else None,
            _music_u=settings.music_u.get_secret_value() if settings.music_u else None,
            _csrf=settings.csrf.get_secret_value() if settings.csrf else None,
            configured_user_id=settings.user_id,
        )

    def __repr__(self) -> str:
        return (
            "AuthenticationProvider(state="
            f"{self.state.value!r}, configured_user_id={self.configured_user_id!r})"
        )

    @property
    def state(self) -> AuthenticationState:
        return (
            AuthenticationState.AUTHENTICATED
            if self._cookie or self._music_u
            else AuthenticationState.ANONYMOUS
        )

    def cookie_header(self) -> str | None:
        parts: list[str] = []
        if self._cookie:
            parts.append(self._cookie.strip().rstrip(";"))
        if self._music_u:
            parts.append(f"MUSIC_U={self._music_u}")
        if self._csrf:
            parts.append(f"__csrf={self._csrf}")
        value = "; ".join(part for part in parts if part)
        if "\r" in value or "\n" in value:
            raise ValueError("cookie configuration contains an invalid line break")
        return value or None

    def csrf_token(self) -> str:
        if self._csrf:
            return self._csrf
        if self._cookie:
            for part in self._cookie.split(";"):
                key, separator, value = part.strip().partition("=")
                if separator and key == "__csrf":
                    return value
        return ""

    def require_user_id(self, requested_user_id: str | None) -> str:
        if self.state is AuthenticationState.ANONYMOUS:
            raise AuthenticationRequiredError(
                "private music library access requires authentication"
            )
        user_id = requested_user_id or self.configured_user_id
        if not user_id:
            raise AuthenticationRequiredError(
                "NETEASE_USER_ID is required when no user_id is supplied"
            )
        return user_id

    def authentication_scope(self, user_id: str | None) -> str:
        return f"user:{user_id}" if user_id else "public"
