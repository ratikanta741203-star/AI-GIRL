"""
Avatar expression / state machine.
"""

from typing import Dict


VALID_STATES = {
    "idle",
    "listening",
    "thinking",
    "speaking",
    "happy",
    "sad",
    "confused",
    "excited",
    "concerned",
    "sleeping",
    "error",
}


class ExpressionManager:
    def __init__(self, initial: str = "idle"):
        self.current = initial if initial in VALID_STATES else "idle"
        self.history = [self.current]

    def set_state(self, state: str) -> str:
        state = state.lower().strip()
        if state not in VALID_STATES:
            state = "idle"
        self.current = state
        self.history.append(state)
        if len(self.history) > 20:
            self.history = self.history[-20:]
        return self.current

    def get_state(self) -> str:
        return self.current

    def to_dict(self) -> Dict:
        return {
            "current": self.current,
            "valid_states": sorted(VALID_STATES),
        }

    def infer_from_text(self, text: str, role: str = "assistant") -> str:
        """Very simple emotion heuristic from text."""
        lower = text.lower()
        if any(w in lower for w in ["great", "awesome", "finished", "congrats", "yay"]):
            return self.set_state("happy")
        if any(w in lower for w in ["worried", "anxious", "stressed", "exam", "deadline"]):
            return self.set_state("concerned")
        if any(w in lower for w in ["sad", "tired", "exhausted", "depressed"]):
            return self.set_state("sad")
        if "?" in text and role == "assistant":
            return self.set_state("thinking")
        if role == "user":
            return self.set_state("listening")
        return self.set_state("speaking" if role == "assistant" else "idle")
