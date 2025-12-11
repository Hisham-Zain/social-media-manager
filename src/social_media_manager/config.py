import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


class Config:
    def __init__(self):
        # --- LLM CONFIGURATION (Chain: Gemini → Groq → Ollama) ---
        self.LLM_PROVIDER = os.getenv("LLM_PROVIDER", "gemini")  # Primary: Gemini
        self.LLM_MODEL = os.getenv("LLM_MODEL", "gemini-2.0-flash-exp")
        self.LLM_FALLBACK_PROVIDER = os.getenv(
            "LLM_FALLBACK_PROVIDER", "groq"
        )  # Fallback 1: Groq
        self.LLM_FALLBACK_MODEL = os.getenv(
            "LLM_FALLBACK_MODEL", "llama-3.2-3b-preview"
        )
        self.LLM_FALLBACK2_PROVIDER = os.getenv(
            "LLM_FALLBACK2_PROVIDER", "ollama"
        )  # Fallback 2: Ollama
        self.LLM_FALLBACK2_MODEL = os.getenv("LLM_FALLBACK2_MODEL", "llama3.2:3b")

        # --- IMAGE/VIDEO GENERATION ---
        self.IMAGE_PROVIDER = os.getenv(
            "IMAGE_PROVIDER", "huggingface"
        )  # huggingface, replicate
        self.VIDEO_PROVIDER = os.getenv(
            "VIDEO_PROVIDER", "huggingface"
        )  # huggingface, replicate

        # --- API KEYS ---
        self.GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
        self.HF_TOKEN = os.getenv("HF_TOKEN", "")  # Hugging Face token for image/video
        self.GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
        self.PEXELS_API_KEY = os.getenv("PEXELS_API_KEY", "")
        self.PIXABAY_API_KEY = os.getenv("PIXABAY_API_KEY", "")
        self.OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
        self.ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
        self.COHERE_API_KEY = os.getenv("COHERE_API_KEY", "")
        self.PERPLEXITY_API_KEY = os.getenv("PERPLEXITY_API_KEY", "")

        # --- OLLAMA (LOCAL) ---
        self.OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
        self.OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2:3b")

        # --- DATABASE (PostgreSQL) ---
        self.DATABASE_URL = os.getenv(
            "DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/agencyos"
        )
        self.DB_POOL_SIZE = int(os.getenv("DB_POOL_SIZE", "5"))
        self.DB_MAX_OVERFLOW = int(os.getenv("DB_MAX_OVERFLOW", "10"))
        self.DB_POOL_TIMEOUT = int(os.getenv("DB_POOL_TIMEOUT", "30"))
        self.DB_ECHO = os.getenv("DB_ECHO", "false").lower() == "true"

        # --- REMOTE INFERENCE (Brain Box) ---
        self.USE_REMOTE_BRAIN = os.getenv("USE_REMOTE_BRAIN", "false").lower() == "true"
        self.BRAIN_API_URL = os.getenv("BRAIN_API_URL", "http://localhost:8000")
        self.BRAIN_API_TIMEOUT = int(os.getenv("BRAIN_API_TIMEOUT", "120"))

        self.META_ACCESS_TOKEN = os.getenv("META_ACCESS_TOKEN", "")
        self.FACEBOOK_PAGE_ID = os.getenv("FACEBOOK_PAGE_ID", "")
        self.INSTAGRAM_ACCOUNT_ID = os.getenv("INSTAGRAM_ACCOUNT_ID", "")

        # --- PATHS ---
        self.BASE_DIR = Path.home() / ".social_media_manager"
        self.PROCESSED_DIR = self.BASE_DIR / "processed"
        self.GENERATED_DIR = self.BASE_DIR / "generated"
        self.DATA_DIR = self.BASE_DIR / "data"
        self.RAW_DIR = self.BASE_DIR / "raw"
        self.WATCH_FOLDER = Path.home() / "social_media_manager" / "inbox"
        self.ASSETS_DIR = self.BASE_DIR / "assets"
        self.STOCK_DIR = self.BASE_DIR / "stock_cache"
        self.MUSIC_DIR = self.BASE_DIR / "music"
        self.SFX_DIR = self.BASE_DIR / "sfx"
        self.THUMB_DIR = self.BASE_DIR / "thumbnails"
        self.AVATAR_DIR = self.BASE_DIR / "avatar"
        self.CREDS_DIR = self.BASE_DIR / "credentials"
        self.DB_PATH = self.BASE_DIR / "content.db"
        self.MEMORY_PATH = self.BASE_DIR / "memory"
        self.BROWSER_PROFILES_DIR = self.BASE_DIR / "browser_profiles"

        # VoxCPM reference voices directory (bundled with package)
        self.VOICES_DIR = Path(__file__).parent / "assets" / "voices"

        for path in [
            self.BASE_DIR,
            self.PROCESSED_DIR,
            self.GENERATED_DIR,
            self.DATA_DIR,
            self.RAW_DIR,
            self.WATCH_FOLDER,
            self.ASSETS_DIR,
            self.STOCK_DIR,
            self.MUSIC_DIR,
            self.SFX_DIR,
            self.THUMB_DIR,
            self.AVATAR_DIR,
            self.CREDS_DIR,
            self.MEMORY_PATH,
            self.BROWSER_PROFILES_DIR,
        ]:
            path.mkdir(parents=True, exist_ok=True)

    def get(self, key, default=None):
        return getattr(self, key, default)

    def sanitize(self):
        safe_conf = self.__dict__.copy()
        secret_keys = [
            "GROQ_API_KEY",
            "HF_TOKEN",
            "GEMINI_API_KEY",
            "PEXELS_API_KEY",
            "META_ACCESS_TOKEN",
            "OPENAI_API_KEY",
            "ANTHROPIC_API_KEY",
            "COHERE_API_KEY",
            "PERPLEXITY_API_KEY",
        ]
        for key in secret_keys:
            if safe_conf.get(key):
                safe_conf[key] = f"****{safe_conf[key][-4:]}"
        return safe_conf


config = Config()
