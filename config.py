"""
Prity AI - Central Configuration
All settings are overridable via environment variables or .env file.
"""

from pathlib import Path
from typing import Literal, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ── App ──────────────────────────────────────────────
    APP_NAME: str = "Prity AI"
    CHARACTER_NAME: str = "Prity"
    VERSION: str = "0.2.0"
    DEBUG: bool = True
    HOST: str = "127.0.0.1"
    PORT: int = 8000

    # ── Paths ────────────────────────────────────────────
    BASE_DIR: Path = Path(__file__).parent.resolve()
    DATABASE_PATH: Path = BASE_DIR / "database" / "memory.db"
    ASSETS_DIR: Path = BASE_DIR / "assets"
    AVATAR_ASSETS: Path = ASSETS_DIR / "avatar"
    VOICES_DIR: Path = ASSETS_DIR / "voices"

    # ── AI Provider (internally uses local model server) ─
    # Displayed to user as "Prity". Backend still talks to local OpenAI-compatible endpoint.
    AI_PROVIDER: Literal["prity", "gemini", "openai", "local"] = "prity"
    AI_MODEL: str = "prity"             # Display / logical model name
    AI_TEMPERATURE: float = 0.7
    AI_MAX_TOKENS: int = 1024
    AI_STREAM: bool = True

    # Gemini (optional cloud)
    GEMINI_API_KEY: Optional[str] = None
    GEMINI_MODEL: str = "gemini-1.5-flash"

    # Local model server (OpenAI-compatible – e.g. Ollama under the hood, hidden from UI)
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_BASE_URL: str = "http://localhost:11434/v1"
    OPENAI_MODEL: str = "llama3.2"      # actual model pulled locally

    # ── Local Mode ───────────────────────────────────────
    LOCAL_MODE: bool = True
    ONLINE_SEARCH_ENABLED: bool = False

    # ── Voice ────────────────────────────────────────────
    WAKE_WORD: str = "hello prity"
    WAKE_WORD_ENABLED: bool = True
    STT_ENGINE: Literal["whisper", "browser", "none"] = "browser"
    TTS_ENGINE: Literal["browser", "edge", "piper", "none"] = "browser"
    TTS_VOICE: str = "en-US-JennyNeural"
    TTS_RATE: str = "+0%"
    TTS_PITCH: str = "+0Hz"
    DEFAULT_LANGUAGE: str = "en"

    # ── Memory & Privacy ─────────────────────────────────
    MEMORY_ENABLED: bool = True
    ENCRYPT_SENSITIVE: bool = False
    MAX_CONVERSATION_HISTORY: int = 50

    # ── Proactive / Notifications ────────────────────────
    PROACTIVE_ENABLED: bool = True
    QUIET_HOURS_START: str = "23:00"
    QUIET_HOURS_END: str = "07:00"
    NOTIFICATION_FREQUENCY: Literal["normal", "important_only", "off"] = "normal"

    # ── Avatar ───────────────────────────────────────────
    AVATAR_DEFAULT_EXPRESSION: str = "idle"
    AVATAR_FPS: int = 30

    # ── Personality ──────────────────────────────────────
    PERSONALITY_STYLE: Literal[
        "friendly", "professional", "playful", "calm", "motivational"
    ] = "friendly"

    # ── Camera / Vision (off by default) ─────────────────
    CAMERA_ENABLED: bool = False


settings = Settings()
