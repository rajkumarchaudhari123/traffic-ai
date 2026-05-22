"""
detection/run_detector.py
Standalone script to test the detector on webcam or video file.
Runs without the FastAPI server.

Usage:
  python app/detection/run_detector.py                      # webcam
  python app/detection/run_detector.py --source video.mp4   # video file
  python app/detection/run_detector.py --demo               # demo mode (no camera)
"""

import argparse
import sys
import time
from pathlib import Path

import cv2
import numpy as np

# Allow running from project root
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.detection.detector import TrafficViolationDetector
from app.utils.challan import ChallanGenerator


def run(source, demo_mode=False):
    violations_dir = Path("violations")
    violations_dir.mkdir(exist_ok=True)

    detector = TrafficViolationDetector(str(violations_dir))
    challan_gen = ChallanGenerator(str(violations_dir))

    total_violations = 0
    start_time = time.time()

    if demo_mode:
        print("\n🎬  Running in DEMO mode (no camera required)")
        print("     Press Q to quit\n")
        frame_idx = 0
        violation_frames = {20, 55, 90, 130, 170}

        while True:
            frame = detector.generate_demo_frame(frame_idx)

            if frame_idx in violation_frames:
                vtypes = ["helmet", "seatbelt", "helmet", "both", "seatbelt"]
                vtype = vtypes[list(violation_frames).index(frame_idx) % len(vtypes)]
                result = detector.simulate_violation(vtype)
                challan = challan_gen.generate(result)
                total_violations += 1
                _print_challan(challan)

            elapsed = int(time.time() - start_time)
            _draw_hud(frame, total_violations, elapsed)
            cv2.imshow("Smart Traffic AI – Demo", frame)

            frame_idx = (frame_idx + 1) % 200
            if cv2.waitKey(50) & 0xFF == ord('q'):
                break
    else:
        try:
            cap_src = int(source) if str(source).isdigit() else source
        except Exception:
            cap_src = 0

        cap = cv2.VideoCapture(cap_src)
        if not cap.isOpened():
            print(f"❌  Cannot open source: {source}")
            print("   Try --demo for no-camera demo mode")
            sys.exit(1)

        print(f"\n📷  Camera opened: {source}")
        print("     Press Q to quit\n")

        while True:
            ret, frame = cap.read()
            if not ret:
                print("⚠️  End of stream")
                break

            annotated, violations = detector.process_frame(frame)
            for v in violations:
                challan = challan_gen.generate(v)
                total_violations += 1
                _print_challan(challan)

            elapsed = int(time.time() - start_time)
            _draw_hud(annotated, total_violations, elapsed)
            cv2.imshow("Smart Traffic AI – Live Detection", annotated)

            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

        cap.release()

    cv2.destroyAllWindows()
    print(f"\n✅  Session ended.  Total violations: {total_violations}")


def _draw_hud(frame, total, elapsed):
    h, w = frame.shape[:2]
    h_str = str(elapsed // 3600).zfill(2)
    m_str = str((elapsed % 3600) // 60).zfill(2)
    s_str = str(elapsed % 60).zfill(2)
    cv2.rectangle(frame, (0, 0), (w, 28), (0, 0, 0), -1)
    cv2.putText(frame, f"SMART TRAFFIC AI  |  Violations: {total}  |  Uptime: {h_str}:{m_str}:{s_str}",
                (8, 18), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 200, 255), 1)


def _print_challan(c):
    print(f"""
  ┌─────────────────────────────────────────────┐
  │  🚨  TRAFFIC VIOLATION DETECTED             │
  ├─────────────────────────────────────────────┤
  │  Challan ID    : {c['challan_id']:<26} │
  │  Vehicle No.   : {c['vehicle_number']:<26} │
  │  Violation     : {c['violation_type']:<26} │
  │  Fine Amount   : ₹{str(c['fine_amount']):<25} │
  │  Status        : {c['status']:<26} │
  │  Location      : {str(c.get('location',''))[:26]:<26} │
  └─────────────────────────────────────────────┘
  {c['message']}
""")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Smart Traffic AI – Standalone Detector")
    parser.add_argument("--source", default="0", help="Camera index or video file path")
    parser.add_argument("--demo", action="store_true", help="Run in demo mode (no camera)")
    args = parser.parse_args()
    run(args.source, demo_mode=args.demo)
