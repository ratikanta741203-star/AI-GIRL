"""
Lip-sync placeholder.
Full phoneme-based lip sync requires audio analysis + blend shapes.
This module provides a simple open/close timing model the frontend can use.
"""


class LipSync:
    def __init__(self):
        self.is_speaking = False
        self.mouth_open = 0.0  # 0.0 – 1.0

    def start(self):
        self.is_speaking = True

    def stop(self):
        self.is_speaking = False
        self.mouth_open = 0.0

    def tick(self, time_ms: float) -> float:
        """Simple sine-based mouth movement while speaking."""
        if not self.is_speaking:
            self.mouth_open = 0.0
            return 0.0
        import math
        # Rough open/close cycle ~ 5 Hz
        self.mouth_open = 0.4 + 0.4 * abs(math.sin(time_ms * 0.01))
        return self.mouth_open

    def status(self) -> dict:
        return {
            "speaking": self.is_speaking,
            "mouth_open": round(self.mouth_open, 2),
            "note": "Replace with phoneme analysis for production quality.",
        }
