import logging

import jwt

from truemetric.constants import JWT_EMAIL_CLAIM, JWT_HMAC_ALGORITHMS, JWT_JWKS_ALGORITHMS
from truemetric.errors import Errors
from truemetric.interfaces import ITokenVerifier
from truemetric.schemas import TokenClaims

logger = logging.getLogger(__name__)


class JwtVerifier(ITokenVerifier):
    """
    #Feature: Authentication
    #Scenario: Verify standard JWTs: HS256 with a shared secret, or RS256/ES256 keys from a JWKS URL
    #Complexity: Time O(len(token)); JWKS keys are cached by PyJWKClient

    Switching identity provider (Clerk, Firebase, Auth0) is a settings change: set the JWKS URL, audience, issuer.
    """

    def __init__(self, secret: str | None, jwks_url: str | None, audience: str | None, issuer: str | None) -> None:
        """
        #Feature: Authentication
        #Scenario: Configure exactly one key source
        #Complexity: Time O(1)

        Args:
            secret: HS256 shared secret, or None.
            jwks_url: JWKS endpoint, or None.
            audience: Expected aud claim, or None to skip.
            issuer: Expected iss claim, or None to skip.

        Raises:
            ValueError: When neither or both key sources are set.
        """
        try:
            if bool(secret) == bool(jwks_url):
                raise ValueError("[JwtVerifier.__init__] Set exactly one of TRUEMETRIC_JWT_SECRET or "
                                 "TRUEMETRIC_JWKS_URL. Fix: configure one key source.")
            self._secret, self._audience, self._issuer = secret, audience, issuer
            self._jwks = jwt.PyJWKClient(jwks_url) if jwks_url else None
        except Exception as exc:
            logger.error("JwtVerifier init failed: %s", exc)
            raise

    def _decode(self, token: str) -> dict:
        """
        #Feature: Authentication
        #Scenario: Signature, expiry, audience and issuer checks
        #Complexity: Time O(len(token))

        Args:
            token: Raw JWT.

        Returns:
            The verified payload.
        """
        try:
            key = self._jwks.get_signing_key_from_jwt(token).key if self._jwks else self._secret
            algorithms = JWT_JWKS_ALGORITHMS if self._jwks else JWT_HMAC_ALGORITHMS
            return jwt.decode(token, key, algorithms=algorithms, audience=self._audience, issuer=self._issuer,
                              options={"require": ["sub", "exp"], "verify_aud": self._audience is not None})
        except Exception as exc:
            logger.warning("_decode rejected token: %s", exc)
            raise

    def verify(self, token: str) -> TokenClaims:
        """
        #Feature: Authentication
        #Scenario: Verify a token and read the user's identity
        #Complexity: Time O(len(token))

        Args:
            token: Raw JWT.

        Returns:
            Verified claims.

        Raises:
            ValueError: When token is None.
            Errors.HTTP.Unauthorized: When the token is invalid, expired or has no email.
        """
        if token is None:
            raise ValueError("[JwtVerifier.verify] 'token' is required.")
        try:
            payload = self._decode(token)
            return TokenClaims(subject=payload["sub"], email=payload.get(JWT_EMAIL_CLAIM, ""))
        except Exception as exc:
            raise Errors.HTTP.Unauthorized(
                "[JwtVerifier.verify] Token rejected. Invariant violated: a valid, unexpired JWT with sub and email "
                "claims is required. Fix: sign in again."
            ) from exc
