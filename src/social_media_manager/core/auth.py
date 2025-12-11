import json
import logging
import os

import google.auth
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

from ..config import config

logger = logging.getLogger(__name__)


class GoogleAuthManager:
    """
    Manages Google OAuth2 authentication for AI services.
    """

    # Scopes for Interactive Login (Sign In Button)
    # We keep these for manual login to ensure we get the right permissions
    SCOPES = [
        "https://www.googleapis.com/auth/cloud-platform",
        "https://www.googleapis.com/auth/userinfo.email",
        "openid",
    ]

    def __init__(self) -> None:
        self.creds_dir = config.CREDS_DIR
        self.token_path = self.creds_dir / "google_token.json"
        self.secrets_path = self.creds_dir / "client_secrets.json"

        self._creds: Credentials | None = None
        self._project_id: str | None = None

    def get_credentials(self) -> Credentials | None:
        """
        Get valid credentials from local storage or system defaults (CLI).
        """
        # 1. Try In-App Token (google_token.json)
        if self._creds and self._creds.valid:
            return self._creds

        if self.token_path.exists():
            try:
                self._creds = Credentials.from_authorized_user_file(
                    str(self.token_path), self.SCOPES
                )
                if self._creds and self._creds.expired and self._creds.refresh_token:
                    logger.info("🔄 Refreshing Google Token...")
                    self._creds.refresh(Request())
                    with open(self.token_path, "w") as token:
                        token.write(self._creds.to_json())
                return self._creds
            except Exception as e:
                logger.warning(f"Failed to load local token: {e}")

        # 2. Try System/CLI Credentials (gcloud auth application-default login)
        try:
            # FIX: Do not enforce scopes on ADC.
            # gcloud provides 'cloud-platform' scope by default which is sufficient.
            creds, project_id = google.auth.default()

            # Simple check to ensure we have a valid project_id
            # If gcloud didn't provide one, try to find it in the environment
            if not project_id:
                # Try to load from the ADC file itself to find a quota_project_id
                # This is a common fallback for the "Cannot find quota project" warning
                if hasattr(creds, "quota_project_id") and creds.quota_project_id:
                    project_id = creds.quota_project_id

            self._creds = creds
            self._project_id = project_id

            # Refresh if necessary (ADC handles this, but good to be explicit)
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())

            logger.info(f"✅ Loaded System Credentials (Project: {project_id})")
            return self._creds
        except Exception as e:
            logger.debug(f"System auth check failed: {e}")
            return None

    def login(self) -> bool:
        """
        Start interactive 'Sign in with Google' flow.
        Requires client_secrets.json.
        """
        if not self.secrets_path.exists():
            logger.error("❌ client_secrets.json not found.")
            return False

        try:
            flow = InstalledAppFlow.from_client_secrets_file(
                str(self.secrets_path), self.SCOPES
            )
            self._creds = flow.run_local_server(port=0)

            # Save for future use
            with open(self.token_path, "w") as token:
                token.write(self._creds.to_json())

            logger.info("✅ Signed in successfully")
            return True
        except Exception as e:
            logger.error(f"❌ Login failed: {e}")
            return False

    def logout(self) -> bool:
        """Remove local user credentials."""
        if self.token_path.exists():
            os.remove(self.token_path)
            self._creds = None
            logger.info("👋 Logged out (System credentials may still be active)")
            return True
        return False

    def get_project_id(self) -> str | None:
        """Get the Google Cloud Project ID."""
        if self._project_id:
            return self._project_id

        if os.getenv("GOOGLE_CLOUD_PROJECT"):
            return os.getenv("GOOGLE_CLOUD_PROJECT")

        # Infer from secrets file
        if self.secrets_path.exists():
            try:
                with open(self.secrets_path) as f:
                    data = json.load(f)
                    key = next(iter(data))
                    return data[key].get("project_id")
            except Exception:
                pass
        return None


# Singleton
_google_auth: GoogleAuthManager | None = None


def get_google_auth() -> GoogleAuthManager:
    global _google_auth
    if _google_auth is None:
        _google_auth = GoogleAuthManager()
    return _google_auth


# =============================================================================
# Multi-Platform OAuth Manager
# =============================================================================


# OAuth provider configurations
OAUTH_PROVIDERS = {
    "youtube": {
        "name": "YouTube",
        "auth_url": "https://accounts.google.com/o/oauth2/v2/auth",
        "token_url": "https://oauth2.googleapis.com/token",
        "scopes": [
            "https://www.googleapis.com/auth/youtube.upload",
            "https://www.googleapis.com/auth/youtube.readonly",
        ],
        "redirect_uri": "http://localhost:8080/callback",
    },
    "tiktok": {
        "name": "TikTok",
        "auth_url": "https://www.tiktok.com/v2/auth/authorize/",
        "token_url": "https://open.tiktokapis.com/v2/oauth/token/",
        "scopes": ["user.info.basic", "video.publish", "video.upload"],
        "redirect_uri": "http://localhost:8080/callback",
    },
    "linkedin": {
        "name": "LinkedIn",
        "auth_url": "https://www.linkedin.com/oauth/v2/authorization",
        "token_url": "https://www.linkedin.com/oauth/v2/accessToken",
        "scopes": ["w_member_social", "r_liteprofile"],
        "redirect_uri": "http://localhost:8080/callback",
    },
}


class OAuthManager:
    """
    Unified OAuth2 manager for multiple social media platforms.

    Provides a consistent interface for:
    - YouTube Data API
    - TikTok API
    - LinkedIn API

    Tokens are stored securely using the system keyring when available,
    falling back to encrypted local files.

    Example:
        manager = OAuthManager()

        # Authenticate with YouTube
        if manager.authenticate("youtube"):
            token = manager.get_access_token("youtube")
            # Use token for API calls
    """

    KEYRING_SERVICE = "agencyos"

    def __init__(self) -> None:
        """Initialize OAuth manager."""
        self.creds_dir = config.CREDS_DIR
        self._tokens: dict[str, dict] = {}
        self._keyring_available = self._check_keyring()
        self._load_tokens()

    def _check_keyring(self) -> bool:
        """Check if secure keyring is available."""
        try:
            import keyring

            # Test keyring access
            keyring.get_password(self.KEYRING_SERVICE, "__test__")
            return True
        except Exception:
            return False

    def _load_tokens(self) -> None:
        """Load stored tokens from keyring or file."""
        for provider in OAUTH_PROVIDERS:
            token = self._get_stored_token(provider)
            if token:
                self._tokens[provider] = token

    def _get_stored_token(self, provider: str) -> dict | None:
        """Get stored token for a provider."""
        # Try keyring first
        if self._keyring_available:
            try:
                import keyring

                token_json = keyring.get_password(
                    self.KEYRING_SERVICE, f"{provider}_token"
                )
                if token_json:
                    return json.loads(token_json)
            except Exception:
                pass

        # Fallback to file
        token_path = self.creds_dir / f"{provider}_token.json"
        if token_path.exists():
            try:
                with open(token_path) as f:
                    return json.load(f)
            except Exception:
                pass

        return None

    def _save_token(self, provider: str, token: dict) -> None:
        """Save token securely."""
        self._tokens[provider] = token

        # Try keyring first
        if self._keyring_available:
            try:
                import keyring

                keyring.set_password(
                    self.KEYRING_SERVICE,
                    f"{provider}_token",
                    json.dumps(token),
                )
                return
            except Exception:
                pass

        # Fallback to file (less secure)
        token_path = self.creds_dir / f"{provider}_token.json"
        with open(token_path, "w") as f:
            json.dump(token, f)

    def _delete_token(self, provider: str) -> None:
        """Delete stored token."""
        self._tokens.pop(provider, None)

        # Remove from keyring
        if self._keyring_available:
            try:
                import keyring

                keyring.delete_password(self.KEYRING_SERVICE, f"{provider}_token")
            except Exception:
                pass

        # Remove file
        token_path = self.creds_dir / f"{provider}_token.json"
        if token_path.exists():
            os.remove(token_path)

    def get_providers(self) -> list[dict]:
        """Get list of supported providers with their status."""
        providers = []
        for provider_id, provider_config in OAUTH_PROVIDERS.items():
            token = self._tokens.get(provider_id)
            providers.append(
                {
                    "id": provider_id,
                    "name": provider_config["name"],
                    "connected": token is not None,
                    "expires_at": token.get("expires_at") if token else None,
                }
            )
        return providers

    def authenticate(
        self,
        provider: str,
        client_id: str | None = None,
        client_secret: str | None = None,
    ) -> bool:
        """
        Start OAuth flow for a platform.

        For YouTube, uses the existing GoogleAuthManager.
        For other platforms, requires client_id and client_secret from .env.

        Args:
            provider: Platform identifier (youtube, tiktok, linkedin).
            client_id: OAuth client ID (reads from env if not provided).
            client_secret: OAuth client secret (reads from env if not provided).

        Returns:
            True if authentication succeeded.
        """
        if provider not in OAUTH_PROVIDERS:
            logger.error(f"❌ Unknown OAuth provider: {provider}")
            return False

        # YouTube uses existing Google auth
        if provider == "youtube":
            google_auth = get_google_auth()
            return google_auth.login()

        # Other platforms - get credentials from env or params
        client_id = client_id or os.getenv(f"{provider.upper()}_CLIENT_ID")
        client_secret = client_secret or os.getenv(f"{provider.upper()}_CLIENT_SECRET")

        if not client_id or not client_secret:
            logger.error(
                f"❌ Missing {provider.upper()}_CLIENT_ID or {provider.upper()}_CLIENT_SECRET"
            )
            return False

        # Start OAuth flow
        try:
            from .oauth_flow import start_oauth_flow

            token = start_oauth_flow(
                provider=provider,
                client_id=client_id,
                client_secret=client_secret,
                config=OAUTH_PROVIDERS[provider],
            )
            if token:
                self._save_token(provider, token)
                logger.info(
                    f"✅ Authenticated with {OAUTH_PROVIDERS[provider]['name']}"
                )
                return True
        except ImportError:
            logger.warning(f"⚠️ OAuth flow module not available for {provider}")
        except Exception as e:
            logger.error(f"❌ OAuth failed for {provider}: {e}")

        return False

    def get_access_token(self, provider: str) -> str | None:
        """
        Get valid access token, refreshing if needed.

        Args:
            provider: Platform identifier.

        Returns:
            Access token string, or None if not authenticated.
        """
        if provider not in self._tokens:
            return None

        token = self._tokens[provider]

        # Check expiry and refresh if needed
        import time

        if token.get("expires_at", 0) < time.time():
            if not self._refresh_token(provider):
                return None

        return token.get("access_token")

    def _refresh_token(self, provider: str) -> bool:
        """Refresh an expired token."""
        token = self._tokens.get(provider)
        if not token or "refresh_token" not in token:
            return False

        provider_config = OAUTH_PROVIDERS.get(provider)
        if not provider_config:
            return False

        client_id = os.getenv(f"{provider.upper()}_CLIENT_ID")
        client_secret = os.getenv(f"{provider.upper()}_CLIENT_SECRET")

        if not client_id or not client_secret:
            return False

        try:
            import requests

            response = requests.post(
                provider_config["token_url"],
                data={
                    "grant_type": "refresh_token",
                    "refresh_token": token["refresh_token"],
                    "client_id": client_id,
                    "client_secret": client_secret,
                },
                timeout=30,
            )
            response.raise_for_status()
            new_token = response.json()

            # Merge with existing token (preserve refresh_token if not returned)
            if "refresh_token" not in new_token:
                new_token["refresh_token"] = token["refresh_token"]

            # Calculate expiry
            import time

            new_token["expires_at"] = time.time() + new_token.get("expires_in", 3600)

            self._save_token(provider, new_token)
            logger.info(f"🔄 Refreshed token for {provider}")
            return True

        except Exception as e:
            logger.error(f"❌ Token refresh failed for {provider}: {e}")
            return False

    def is_connected(self, provider: str) -> bool:
        """Check if a provider is connected."""
        return provider in self._tokens

    def disconnect(self, provider: str) -> bool:
        """Disconnect a provider (revoke and delete token)."""
        if provider not in self._tokens:
            return False

        self._delete_token(provider)
        logger.info(
            f"👋 Disconnected from {OAUTH_PROVIDERS.get(provider, {}).get('name', provider)}"
        )
        return True


# Singleton
_oauth_manager: OAuthManager | None = None


def get_oauth_manager() -> OAuthManager:
    """Get the OAuth manager singleton."""
    global _oauth_manager
    if _oauth_manager is None:
        _oauth_manager = OAuthManager()
    return _oauth_manager
