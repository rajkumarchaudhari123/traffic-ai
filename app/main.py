"""
Smart Traffic AI – Real-Time Helmet & Seatbelt Detection System
FastAPI Main Application
"""

import asyncio
import base64
import json
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

import cv2
import numpy as np
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi import Request

from detection.detector import TrafficViolationDetector
from utils.challan import ChallanGenerator
from utils.state import SystemState

# ─── App Setup ────────────────────────────────────────────────────────────────

BASE_DIR = Path(__file__).parent.parent

app = FastAPI(
    title="Smart Traffic AI",
    description="Real-Time Helmet & Seatbelt Detection System",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
app.mount("/violations", StaticFiles(directory=str(BASE_DIR / "violations")), name="violations")

templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

# ─── Global State ─────────────────────────────────────────────────────────────

state = SystemState()
detector = TrafficViolationDetector(violations_dir=str(BASE_DIR / "violations"))
challan_gen = ChallanGenerator(output_dir=str(BASE_DIR / "violations"))
active_connections: list[WebSocket] = []

# ─── WebSocket Manager ────────────────────────────────────────────────────────

async def broadcast(message: dict):
    """Broadcast message to all connected WebSocket clients."""
    dead = []
    for ws in active_connections:
        try:
            await ws.send_json(message)
        except Exception:
            dead.append(ws)
    for ws in dead:
        try:
            active_connections.remove(ws)
        except ValueError:
            pass


# ─── Routes ───────────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request})


@app.get("/api/stats")
async def get_stats():
    return {
        "total_violations": state.total_violations,
        "helmet_violations": state.helmet_violations,
        "seatbelt_violations": state.seatbelt_violations,
        "challans_generated": state.challans_generated,
        "system_uptime": state.get_uptime(),
        "camera_status": state.camera_active,
        "recent_violations": state.recent_violations[-10:],
    }


@app.get("/api/violations")
async def get_violations():
    violations_dir = BASE_DIR / "violations"
    images = []
    for ext in ("*.jpg", "*.png"):
        images.extend(violations_dir.glob(ext))
    images.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return {
        "images": [f"/violations/{p.name}" for p in images[:20]],
        "total": len(images),
    }


@app.get("/api/challans")
async def get_challans():
    return {"challans": state.challans[-20:]}


@app.post("/api/demo/trigger/{violation_type}")
async def trigger_demo_violation(violation_type: str):
    """Manually trigger a demo violation for showcase."""
    valid = {"helmet", "seatbelt", "both"}
    if violation_type not in valid:
        raise HTTPException(400, f"violation_type must be one of {valid}")

    result = detector.simulate_violation(violation_type)
    challan = challan_gen.generate(result)
    state.record_violation(result, challan)

    await broadcast({
        "type": "violation",
        "data": {**result, "challan": challan},
    })
    return {"status": "triggered", "violation": result, "challan": challan}


@app.post("/api/camera/start")
async def start_camera(source: Optional[str] = "0"):
    if state.camera_active:
        return {"status": "already_running"}
    state.camera_active = True
    state.camera_source = source
    asyncio.create_task(camera_loop())
    return {"status": "started", "source": source}


@app.post("/api/camera/stop")
async def stop_camera():
    state.camera_active = False
    return {"status": "stopped"}


# ─── WebSocket ────────────────────────────────────────────────────────────────

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    active_connections.append(websocket)
    try:
        # Send current stats on connect
        await websocket.send_json({"type": "connected", "stats": {
            "total_violations": state.total_violations,
            "helmet_violations": state.helmet_violations,
            "seatbelt_violations": state.seatbelt_violations,
            "challans_generated": state.challans_generated,
            "camera_active": state.camera_active,
            "camera_source": state.camera_source,
        }})
        while True:
            await websocket.receive_text()  # keep alive
    except WebSocketDisconnect:
        try:
            active_connections.remove(websocket)
        except ValueError:
            pass


# ─── Camera Loop ──────────────────────────────────────────────────────────────

async def camera_loop():
    """Main camera processing loop running in background."""
    source = state.camera_source
    is_helmet_demo = (source == "helmet_demo")
    actual_source = "0" if is_helmet_demo else source
    
    try:
        cap_source = int(actual_source) if actual_source.isdigit() else actual_source
    except Exception:
        cap_source = 0

    cap = cv2.VideoCapture(cap_source)
    if not cap.isOpened():
        # Fall back to demo mode
        await broadcast({"type": "log", "message": "⚠️  Camera not found – switching to DEMO mode", "level": "warn"})
        state.camera_active = False
        asyncio.create_task(demo_loop())
        return

    await broadcast({"type": "log", "message": "📷  Camera started successfully", "level": "info"})
    frame_count = 0

    try:
        while state.camera_active:
            ret, frame = cap.read()
            if not ret:
                break

            frame_count += 1
            result_frame, violations = detector.process_frame(frame, helmet_demo=is_helmet_demo)

            # Encode frame for streaming
            _, buffer = cv2.imencode(".jpg", result_frame, [cv2.IMWRITE_JPEG_QUALITY, 75])
            frame_b64 = base64.b64encode(buffer).decode()

            # Broadcast frame every 3rd frame to reduce bandwidth
            if frame_count % 3 == 0:
                await broadcast({"type": "frame", "data": frame_b64})

            # Handle violations
            for v in violations:
                challan = challan_gen.generate(v)
                state.record_violation(v, challan)
                await broadcast({"type": "violation", "data": {**v, "challan": challan}})
                await broadcast({"type": "log",
                                 "message": f"🚨 {v['violation_type']} violation – {v.get('plate', 'Unknown')}",
                                 "level": "alert"})

            await asyncio.sleep(0.033)  # ~30 FPS
    finally:
        cap.release()
        state.camera_active = False


async def demo_loop():
    """Simulated demo mode – generates fake violations periodically."""
    state.camera_active = True
    await broadcast({"type": "log", "message": "🎬  Demo mode active – simulating traffic feed", "level": "info"})

    # Generate a synthetic video frame
    frame_idx = 0
    violation_schedule = [30, 80, 130, 180]  # frames at which violations fire

    while state.camera_active:
        frame = detector.generate_demo_frame(frame_idx)
        _, buffer = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 75])
        frame_b64 = base64.b64encode(buffer).decode()

        if frame_idx % 3 == 0:
            await broadcast({"type": "frame", "data": frame_b64})

        if frame_idx in violation_schedule:
            vtype = ["helmet", "seatbelt", "helmet", "both"][violation_schedule.index(frame_idx)]
            result = detector.simulate_violation(vtype)
            challan = challan_gen.generate(result)
            state.record_violation(result, challan)
            await broadcast({"type": "violation", "data": {**result, "challan": challan}})
            await broadcast({"type": "log",
                             "message": f"🚨 DEMO – {result['violation_type']} – {result.get('plate', 'N/A')}",
                             "level": "alert"})

        frame_idx += 1
        if frame_idx > 200:
            frame_idx = 0

        await asyncio.sleep(0.05)


# ─── Startup ──────────────────────────────────────────────────────────────────

@app.on_event("startup")
async def startup_event():
    os.makedirs(str(BASE_DIR / "violations"), exist_ok=True)
    asyncio.create_task(demo_loop())
    print("✅  Smart Traffic AI server started")
    print("📊  Dashboard: http://localhost:8000")
