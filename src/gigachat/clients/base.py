import logging
import ssl
import time
from typing import Any, Dict, List, Optional, Tuple, Union

import httpx
from pydantic import SecretStr

from gigachat.schemas.auth import AccessToken, Token
from gigachat.settings import Settings

logger = logging.getLogger(__name__)

GIGACHAT_MODEL = "GigaChat"
SecretValue = Union[str, SecretStr]


def _unwrap_secret(value: Optional[SecretValue]) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, SecretStr):
        return value.get_secret_value()
    return value


def _get_kwargs(settings: Settings) -> Dict[str, Any]:
    """Return settings for connecting to the GigaChat API."""
    kwargs = {
        "base_url": settings.base_url,
        "verify": settings.verify_ssl_certs,
        "timeout": httpx.Timeout(settings.timeout),
    }
    if settings.ssl_context:
        kwargs["verify"] = settings.ssl_context
    if settings.ca_bundle_file:
        kwargs["verify"] = settings.ca_bundle_file
    if settings.cert_file:
        kwargs["cert"] = (
            settings.cert_file,
            settings.key_file,
            _unwrap_secret(settings.key_file_password),
        )
    if settings.max_connections is not None:
        kwargs["limits"] = httpx.Limits(max_connections=settings.max_connections)
    return kwargs


def _get_auth_kwargs(settings: Settings) -> Dict[str, Any]:
    """Return settings for connecting to the OAuth 2.0 authorization server."""
    kwargs = {
        "verify": settings.verify_ssl_certs,
        "timeout": httpx.Timeout(settings.timeout),
    }
    if settings.ssl_context:
        kwargs["verify"] = settings.ssl_context
    if settings.ca_bundle_file:
        kwargs["verify"] = settings.ca_bundle_file
    return kwargs


def _build_access_token(token: Token) -> AccessToken:
    return AccessToken(access_token=token.tok, expires_at=token.exp, x_headers=token.x_headers)


class _BaseClient:
    _access_token: Optional[AccessToken] = None

    def __init__(
        self,
        *,
        base_url: Optional[str] = None,
        auth_url: Optional[str] = None,
        credentials: Optional[SecretValue] = None,
        scope: Optional[str] = None,
        access_token: Optional[SecretValue] = None,
        model: Optional[str] = None,
        profanity_check: Optional[bool] = None,
        user: Optional[str] = None,
        password: Optional[SecretValue] = None,
        timeout: Optional[float] = None,
        verify_ssl_certs: Optional[bool] = None,
        ca_bundle_file: Optional[str] = None,
        cert_file: Optional[str] = None,
        key_file: Optional[str] = None,
        key_file_password: Optional[SecretValue] = None,
        ssl_context: Optional[ssl.SSLContext] = None,
        flags: Optional[List[str]] = None,
        max_connections: Optional[int] = None,
        max_retries: Optional[int] = None,
        retry_backoff_factor: Optional[float] = None,
        retry_on_status_codes: Optional[Tuple[int, ...]] = None,
        **_unknown_kwargs: Any,
    ) -> None:
        if _unknown_kwargs:
            logger.warning("GigaChat: unknown kwargs - %s", _unknown_kwargs)

        kwargs: Dict[str, Any] = {
            "base_url": base_url,
            "auth_url": auth_url,
            "credentials": credentials,
            "scope": scope,
            "access_token": access_token,
            "model": model,
            "profanity_check": profanity_check,
            "user": user,
            "password": password,
            "timeout": timeout,
            "verify_ssl_certs": verify_ssl_certs,
            "ca_bundle_file": ca_bundle_file,
            "cert_file": cert_file,
            "key_file": key_file,
            "key_file_password": key_file_password,
            "ssl_context": ssl_context,
            "flags": flags,
            "max_connections": max_connections,
            "max_retries": max_retries,
            "retry_backoff_factor": retry_backoff_factor,
            "retry_on_status_codes": retry_on_status_codes,
        }
        config = {key: value for key, value in kwargs.items() if value is not None}
        self._settings = Settings(**config)
        if self._settings.access_token:
            self._access_token = AccessToken(
                access_token=self._settings.access_token,
                expires_at=0,
            )

    @property
    def token(self) -> Optional[str]:
        if self._access_token:
            return self._access_token.access_token.get_secret_value()
        return None

    @property
    def _use_auth(self) -> bool:
        return bool(self._settings.credentials or (self._settings.user and self._settings.password))

    def _is_token_usable(self) -> bool:
        """Check if cached token is usable (exists and not expiring within buffer)."""
        if self._access_token and (
            self._access_token.expires_at == 0
            or self._access_token.expires_at > (time.time() * 1000) + self._settings.token_expiry_buffer_ms
        ):
            return True
        return False

    def _reset_token(self) -> None:
        """Reset the token."""
        self._access_token = None
