import json
import logging
from typing import Any

from ..config import config

logger = logging.getLogger(__name__)


class ClientManager:
    """
    Manages Client Profiles and their specific Social Credentials.
    """

    def __init__(self) -> None:
        self.clients_file = config.BASE_DIR / "clients.json"
        if not self.clients_file.exists():
            self._save_db({})

    def _get_db(self) -> dict[str, Any]:
        try:
            with open(self.clients_file, "r") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def _save_db(self, data: dict[str, Any]) -> None:
        try:
            with open(self.clients_file, "w") as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            logger.error(f"❌ Failed to save client DB: {e}")

    def get_clients(self) -> dict[str, Any]:
        return self._get_db()

    def get_client_config(self, name: str) -> dict[str, Any]:
        return self._get_db().get(name, {})

    def update_client_profile(
        self, name: str, niche: str, tone: str, description: str = ""
    ) -> None:
        db = self._get_db()
        if name not in db:
            db[name] = {}

        db[name].update({"niche": niche, "tone": tone, "description": description})
        self._save_db(db)
        logger.info(f"✅ Updated profile for {name}")

    def update_client_creds(
        self, name: str, platform: str, creds: dict[str, str]
    ) -> None:
        db = self._get_db()
        if name not in db:
            db[name] = {}

        if "platforms" not in db[name]:
            db[name]["platforms"] = {}

        db[name]["platforms"][platform] = creds
        self._save_db(db)
        logger.info(f"🔐 Updated {platform} creds for {name}")

    def get_client_context(self, name: str) -> str:
        c = self.get_client_config(name)
        if not c:
            return "Role: Professional Creator."
        return f"ROLE: Manager for '{name}'. NICHE: {c.get('niche')}. VOICE: {c.get('tone')}."
