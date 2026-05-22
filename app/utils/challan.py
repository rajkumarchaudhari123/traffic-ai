"""
E-Challan Generator
Produces realistic government-style e-challans for traffic violations.
"""

import random
import string
import textwrap
from datetime import datetime
from pathlib import Path


COURT_LOCATIONS = [
    "Metropolitan Magistrate Court, New Delhi",
    "Traffic Court, Bengaluru City",
    "Judicial Magistrate, Mumbai",
    "District Court, Chennai",
    "Civil Court, Hyderabad",
]

OFFICER_NAMES = [
    "Inspector Rajesh Kumar (Badge #TR-1042)",
    "Sub-Inspector Priya Sharma (Badge #TR-2017)",
    "Inspector Anil Verma (Badge #TR-3055)",
    "Head Constable Meena Joshi (Badge #TR-4088)",
]

FINE_MAP = {
    "No Helmet": 1000,
    "No Seatbelt": 1000,
    "No Helmet & No Seatbelt": 2000,
    "Rash Driving": 5000,
    "Signal Jump": 500,
}


def _challan_id() -> str:
    letters = "".join(random.choices(string.ascii_uppercase, k=2))
    digits = "".join(random.choices(string.digits, k=8))
    return f"ECH{letters}{digits}"


class ChallanGenerator:
    def __init__(self, output_dir: str = "violations"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate(self, violation: dict) -> dict:
        """Generate challan data dict and save .txt file."""
        challan_id = _challan_id()
        fine = violation.get("fine", 1000)
        vtype = violation.get("violation_type", "Unknown Violation")
        plate = violation.get("plate", "UNKNOWN")
        location = violation.get("location", "N/A")
        timestamp = violation.get("timestamp", datetime.now().isoformat())

        due_date = datetime.now().replace(day=min(28, datetime.now().day + 15)).strftime("%d-%m-%Y")

        challan = {
            "challan_id": challan_id,
            "vehicle_number": plate,
            "violation_type": vtype,
            "fine_amount": fine,
            "status": "Pending",
            "issued_at": timestamp,
            "location": location,
            "officer": random.choice(OFFICER_NAMES),
            "court": random.choice(COURT_LOCATIONS),
            "due_date": due_date,
            "message": violation.get("message", "Traffic violation recorded."),
            "proof_image": violation.get("image", ""),
        }

        self._save_txt(challan)
        return challan

    def _save_txt(self, challan: dict):
        """Save challan as human-readable .txt file."""
        ts_safe = challan["issued_at"].replace(":", "-").replace(".", "-")
        filename = self.output_dir / f"CHALLAN_{challan['challan_id']}_{ts_safe}.txt"

        lines = textwrap.dedent(f"""
        ╔══════════════════════════════════════════════════════════════╗
        ║         GOVERNMENT OF INDIA – TRAFFIC DEPARTMENT            ║
        ║              E-CHALLAN NOTIFICATION SYSTEM                  ║
        ╚══════════════════════════════════════════════════════════════╝

        CHALLAN ID    : {challan['challan_id']}
        ISSUED ON     : {challan['issued_at']}
        DUE DATE      : {challan['due_date']}

        ──────────────────────────────────────────────────────────────
        VEHICLE DETAILS
        ──────────────────────────────────────────────────────────────
        Vehicle Number : {challan['vehicle_number']}
        Location       : {challan['location']}

        ──────────────────────────────────────────────────────────────
        VIOLATION DETAILS
        ──────────────────────────────────────────────────────────────
        Violation Type : {challan['violation_type']}
        Description    : {challan['message']}

        ──────────────────────────────────────────────────────────────
        FINE DETAILS
        ──────────────────────────────────────────────────────────────
        Fine Amount    : ₹{challan['fine_amount']}
        Payment Status : {challan['status']}
        Pay By         : {challan['due_date']}

        ──────────────────────────────────────────────────────────────
        ISSUING AUTHORITY
        ──────────────────────────────────────────────────────────────
        Issued By      : {challan['officer']}
        Court          : {challan['court']}

        ──────────────────────────────────────────────────────────────
        Proof Image    : {challan['proof_image']}
        ──────────────────────────────────────────────────────────────

        NOTE: Failure to pay within due date may result in additional
        penalties and legal proceedings.

        Pay online at: https://echallan.parivahan.gov.in

        ══════════════════════════════════════════════════════════════
        """).strip()

        filename.write_text(lines, encoding="utf-8")
