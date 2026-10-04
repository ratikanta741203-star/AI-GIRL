"""
Simple animation controller.
In a full 3D implementation this would drive Three.js / Unity / Unreal.
Here we expose state that the frontend uses for CSS / canvas animation.
"""

from avatar.expressions import ExpressionManager


class AnimationController:
    def __init__(self):
        self.expressions = ExpressionManager()
        self.is_blinking = False
        self.is_breathing = True
        self.gaze = "center"  # left | center | right | user

    def update(self, state: str | None = None) -> dict:
        if state:
            self.expressions.set_state(state)
        return {
            "expression": self.expressions.get_state(),
            "blinking": self.is_blinking,
            "breathing": self.is_breathing,
            "gaze": self.gaze,
        }

    def look_at_user(self):
        self.gaze = "user"
        self.expressions.set_state("listening")

    def go_idle(self):
        self.gaze = "center"
        self.expressions.set_state("idle")

    def speak(self):
        self.expressions.set_state("speaking")
