"""
Global in-memory state manager for the Smart Traffic AI system.
No database required – all state held in Python objects.
"""

import time
from datetime import datetime
from typing import Optional


class SystemState:
    def __init__(self):
        self.start_time = time.time()
        self.camera_active: bool = False
        self.camera_source: str = "0"

        self.total_violations: int = 0
        self.helmet_violations: int = 0
        self.seatbelt_violations: int = 0
        self.challans_generated: int = 0

        self.recent_violations: list = []
        self.challans: list = []
        self.logs: list = []

    def record_violation(self, violation: dict, challan: dict):
        """Record a violation and its challan in memory."""
        vtype = violation.get("violation_type", "")
        self.total_violations += 1

        if "Helmet" in vtype:
            self.helmet_violations += 1
        if "Seatbelt" in vtype:
            self.seatbelt_violations += 1

        self.challans_generated += 1

        entry = {
            **violation,
            "challan_id": challan.get("challan_id"),
            "fine": challan.get("fine_amount"),
        }
        self.recent_violations.append(entry)
        if len(self.recent_violations) > 100:
            self.recent_violations.pop(0)

        self.challans.append(challan)
        if len(self.challans) > 100:
            self.challans.pop(0)

    def get_uptime(self) -> str:
        elapsed = int(time.time() - self.start_time)
        h = elapsed // 3600
        m = (elapsed % 3600) // 60
        s = elapsed % 60
        return f"{h:02d}:{m:02d}:{s:02d}"
