"""
OAuth2 Flow Handler for AgencyOS.

Handles the OAuth2 authorization code flow for social media platforms.
Opens a browser for user consent and runs a local callback server.
"""

import secrets
import time
import urllib.parse
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any

from loguru import logger


class OAuthCallbackHandler(BaseHTTPRequestHandler):
    """HTTP request handler for OAuth callbacks."""

    def log_message(self, fmt: str, *args: Any) -> None:
        """Suppress default HTTP logs."""
        pass

    def do_GET(self) -> None:
        """Handle OAuth callback GET request."""
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)

        # Store the authorization code on the server instance
        if "code" in params:
            self.server.auth_code = params["code"][0]  # type: ignore
            self.server.auth_error = None  # type: ignore
            self._send_success_response()
        elif "error" in params:
            self.server.auth_code = None  # type: ignore
            self.server.auth_error = params.get("error_description", params["error"])[0]  # type: ignore
            self._send_error_response(self.server.auth_error)  # type: ignore
        else:
            self._send_error_response("No code or error in callback")

    def _send_success_response(self) -> None:
        """Send success HTML response."""
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        html = """
        <!DOCTYPE html>
        <html>
        <head><title>Authorization Successful</title></head>
        <body style="font-family: Arial, sans-serif; text-align: center; padding: 50px;">
            <h1 style="color: #4CAF50;">✓ Authorization Successful!</h1>
            <p>You can close this window and return to AgencyOS.</p>
            <script>setTimeout(() => window.close(), 3000);</script>
        </body>
        </html>
        """
        self.wfile.write(html.encode())

    def _send_error_response(self, error: str) -> None:
        """Send error HTML response."""
        self.send_response(400)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        html = f"""
        <!DOCTYPE html>
        <html>
        <head><title>Authorization Failed</title></head>
        <body style="font-family: Arial, sans-serif; text-align: center; padding: 50px;">
            <h1 style="color: #f44336;">✗ Authorization Failed</h1>
            <p>{error}</p>
            <p>Please try again or check your credentials.</p>
        </body>
        </html>
        """
        self.wfile.write(html.encode())


def start_oauth_flow(
    provider: str,
    client_id: str,
    client_secret: str,
    config: dict[str, Any],
    timeout: int = 120,
) -> dict[str, Any] | None:
    """
    Start OAuth2 authorization code flow.

    Opens browser for user consent and handles the callback.

    Args:
        provider: Provider identifier (e.g., 'tiktok', 'linkedin').
        client_id: OAuth client ID.
        client_secret: OAuth client secret.
        config: Provider configuration with auth_url, token_url, scopes.
        timeout: Timeout in seconds for user to complete auth.

    Returns:
        Token dict with access_token, refresh_token, expires_at, or None if failed.
    """
    import requests

    # Parse redirect URI to get port
    redirect_uri = config.get("redirect_uri", "http://localhost:8080/callback")
    parsed = urllib.parse.urlparse(redirect_uri)
    port = parsed.port or 8080

    # Generate state for CSRF protection
    state = secrets.token_urlsafe(32)

    # Build authorization URL
    auth_params = {
        "client_key" if provider == "tiktok" else "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": " ".join(config.get("scopes", [])),
        "state": state,
    }

    auth_url = f"{config['auth_url']}?{urllib.parse.urlencode(auth_params)}"

    logger.info(f"🔐 Starting OAuth flow for {provider}...")

    # Start local callback server
    server = HTTPServer(("localhost", port), OAuthCallbackHandler)
    server.auth_code = None  # type: ignore
    server.auth_error = None  # type: ignore
    server.timeout = timeout

    # Open browser for authorization
    webbrowser.open(auth_url)
    logger.info(f"🌐 Opened browser for {provider} authorization")

    # Wait for callback
    start_time = time.time()
    while server.auth_code is None and server.auth_error is None:  # type: ignore
        if time.time() - start_time > timeout:
            logger.error(f"❌ OAuth timeout for {provider}")
            server.server_close()
            return None
        server.handle_request()

    server.server_close()

    if server.auth_error:  # type: ignore
        logger.error(f"❌ OAuth error for {provider}: {server.auth_error}")  # type: ignore
        return None

    # Exchange authorization code for tokens
    auth_code = server.auth_code  # type: ignore
    logger.info(f"✅ Received authorization code for {provider}")

    try:
        # Build token request (TikTok has different parameter names)
        if provider == "tiktok":
            token_data = {
                "client_key": client_id,
                "client_secret": client_secret,
                "code": auth_code,
                "grant_type": "authorization_code",
                "redirect_uri": redirect_uri,
            }
        else:
            token_data = {
                "client_id": client_id,
                "client_secret": client_secret,
                "code": auth_code,
                "grant_type": "authorization_code",
                "redirect_uri": redirect_uri,
            }

        response = requests.post(
            config["token_url"],
            data=token_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=30,
        )
        response.raise_for_status()
        token = response.json()

        # Normalize token response
        if provider == "tiktok" and "data" in token:
            # TikTok wraps token in 'data' object
            token = token["data"]

        # Calculate absolute expiry time
        expires_in = token.get("expires_in", 3600)
        token["expires_at"] = time.time() + expires_in

        logger.info(f"✅ Successfully authenticated with {provider}")
        return token

    except requests.exceptions.RequestException as e:
        logger.error(f"❌ Token exchange failed for {provider}: {e}")
        return None
    except Exception as e:
        logger.error(f"❌ OAuth flow failed for {provider}: {e}")
        return None


def build_auth_url(
    provider: str,
    client_id: str,
    config: dict[str, Any],
    redirect_uri: str | None = None,
) -> tuple[str, str]:
    """
    Build OAuth authorization URL without starting the flow.

    Useful for embedding in web UIs that handle their own callbacks.

    Args:
        provider: Provider identifier.
        client_id: OAuth client ID.
        config: Provider configuration.
        redirect_uri: Override redirect URI.

    Returns:
        Tuple of (authorization_url, state).
    """
    state = secrets.token_urlsafe(32)
    redirect = redirect_uri or config.get(
        "redirect_uri", "http://localhost:8080/callback"
    )

    auth_params = {
        "client_key" if provider == "tiktok" else "client_id": client_id,
        "redirect_uri": redirect,
        "response_type": "code",
        "scope": " ".join(config.get("scopes", [])),
        "state": state,
    }

    auth_url = f"{config['auth_url']}?{urllib.parse.urlencode(auth_params)}"
    return auth_url, state
