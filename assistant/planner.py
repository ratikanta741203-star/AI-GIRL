"""
Daily Planner & Schedule helper.
"""

from __future__ import annotations

from datetime import datetime, time, timedelta
from typing import Dict, List, Optional

from assistant.memory import MemoryManager


class Planner:
    def __init__(self, memory: Optional[MemoryManager] = None):
        self.memory = memory or MemoryManager()

    def plan_day(
        self,
        wake_time: str = "08:00",
        sleep_time: str = "23:00",
        fixed_events: Optional[List[Dict]] = None,
        tasks: Optional[List[Dict]] = None,
    ) -> List[Dict]:
        """
        Create a simple optimized daily schedule.
        fixed_events: [{"time": "10:00", "title": "Class", "duration_min": 60}, ...]
        tasks: pending tasks from memory
        """
        if tasks is None:
            tasks = self.memory.list_tasks(status="pending")

        schedule = []
        current = datetime.strptime(wake_time, "%H:%M")
        end = datetime.strptime(sleep_time, "%H:%M")
        if end <= current:
            end += timedelta(days=1)

        # Add wake-up
        schedule.append({"time": wake_time, "title": "Wake up", "type": "routine"})

        # Insert fixed events first
        fixed = sorted(fixed_events or [], key=lambda x: x.get("time", "00:00"))
        for ev in fixed:
            schedule.append(
                {
                    "time": ev["time"],
                    "title": ev["title"],
                    "type": "event",
                    "duration_min": ev.get("duration_min", 60),
                }
            )

        # Simple task placement in free slots (very basic heuristic)
        used_times = {s["time"] for s in schedule}
        task_idx = 0
        slot = current + timedelta(hours=1)

        while slot < end and task_idx < len(tasks):
            tstr = slot.strftime("%H:%M")
            if tstr not in used_times:
                # lunch break around 13:00
                if 12 <= slot.hour < 14:
                    schedule.append({"time": tstr, "title": "Lunch / Break", "type": "break"})
                else:
                    task = tasks[task_idx]
                    schedule.append(
                        {
                            "time": tstr,
                            "title": task["title"],
                            "type": "task",
                            "task_id": task["id"],
                        }
                    )
                    task_idx += 1
            slot += timedelta(hours=1)

        schedule.append({"time": sleep_time, "title": "Wind down / Sleep", "type": "routine"})
        schedule.sort(key=lambda x: x["time"])
        return schedule

    def format_schedule(self, schedule: List[Dict]) -> str:
        lines = ["Here's a suggested plan for your day:\n"]
        for item in schedule:
            lines.append(f"{item['time']} — {item['title']}")
        lines.append("\nYou can change any part of this. Just tell me what to adjust.")
        return "\n".join(lines)
