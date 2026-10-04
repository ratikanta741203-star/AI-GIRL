"""
Tool Manager - computer control, web search, weather, etc.
Destructive actions require explicit confirmation.
"""

from __future__ import annotations

import subprocess
import platform
from typing import Any, Dict, Optional

from config import settings


class ToolManager:
    def __init__(self):
        self.pending_confirmation: Optional[Dict[str, Any]] = None

    def open_application(self, name: str) -> str:
        """Open a common application. Platform-aware."""
        name_lower = name.lower().strip()
        system = platform.system()

        # Common mappings
        apps = {
            "vscode": "code",
            "vs code": "code",
            "chrome": "google-chrome" if system == "Linux" else "chrome",
            "firefox": "firefox",
            "terminal": "gnome-terminal" if system == "Linux" else "Terminal",
            "notes": "notepad" if system == "Windows" else "gedit",
            "spotify": "spotify",
        }

        cmd = apps.get(name_lower, name_lower)

        try:
            if system == "Windows":
                subprocess.Popen(["start", cmd], shell=True)
            elif system == "Darwin":
                subprocess.Popen(["open", "-a", cmd])
            else:
                subprocess.Popen([cmd])
            return f"Opening {name}..."
        except Exception as e:
            return f"I couldn't open {name}. Error: {e}"

    def create_folder(self, path: str) -> str:
        from pathlib import Path

        try:
            Path(path).mkdir(parents=True, exist_ok=True)
            return f"Folder created at {path}"
        except Exception as e:
            return f"Failed to create folder: {e}"

    def request_destructive(self, action: str, details: str) -> str:
        """Queue a destructive action for user confirmation."""
        self.pending_confirmation = {"action": action, "details": details}
        return (
            f"This will {details}. Should I continue? "
            "Say 'yes' to confirm or 'no' to cancel."
        )

    def confirm_pending(self, confirmed: bool) -> str:
        if not self.pending_confirmation:
            return "There is nothing pending confirmation."
        action = self.pending_confirmation
        self.pending_confirmation = None
        if not confirmed:
            return "Okay, I cancelled that action."
        # Execute only after confirmation
        if action["action"] == "delete":
            # Placeholder – real implementation would use the stored path
            return f"Executed: {action['details']}"
        return f"Confirmed and executed: {action['details']}"

    def get_weather_stub(self, location: str = "local") -> str:
        if settings.LOCAL_MODE or not settings.ONLINE_SEARCH_ENABLED:
            return (
                "Weather requires online mode. "
                "Enable ONLINE_SEARCH_ENABLED and provide a weather API key to use this."
            )
        return f"Weather lookup for {location} is not yet configured with a real API."

    def web_search_stub(self, query: str) -> str:
        if settings.LOCAL_MODE or not settings.ONLINE_SEARCH_ENABLED:
            return (
                "Web search is disabled in local mode. "
                "Turn on ONLINE_SEARCH_ENABLED in settings to enable it."
            )
        return f"Search results for '{query}' would appear here when online search is configured."
