from abc import ABC, abstractmethod

from truemetric.schemas import TokenClaims


class ITokenVerifier(ABC):
    """
    #Feature: Authentication
    #Scenario: Verify a bearer token from any identity provider (local HS256, Clerk, Firebase, Auth0)
    #Complexity: Time O(1) plus a cached key fetch for JWKS providers
    """

    @abstractmethod
    def verify(self, token: str) -> TokenClaims:
        """
        #Feature: Authentication
        #Scenario: Check signature, expiry, audience and issuer, then read the identity
        #Complexity: Time O(len(token))

        Args:
            token: Raw JWT.

        Returns:
            The verified claims.

        Raises:
            Errors.HTTP.Unauthorized: When the token is invalid, expired or lacks an email.
        """
