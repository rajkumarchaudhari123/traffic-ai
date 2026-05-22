# Smart Traffic AI 🚦
### Real-Time Helmet & Seatbelt Detection System

> A production-grade AI traffic monitoring system that detects helmet and seatbelt violations, reads number plates via OCR, and instantly generates e-challans — all in real-time from webcam, CCTV, or video files.

---

## ✨ Features

| Feature | Details |
|---|---|
| 🪖 Helmet Detection | YOLOv8 detects motorcyclists without helmets |
| 🪢 Seatbelt Detection | YOLOv8 detects drivers without seatbelt |
| 🔢 Plate Recognition | EasyOCR / Tesseract reads number plates |
| 📄 E-Challan Generator | Instant realistic challan with fine details |
| 📷 Multi-source Input | Webcam, CCTV/IP camera, video files |
| 🖥️ Live Dashboard | Futuristic government-style monitoring UI |
| 🎬 Demo Mode | Works without any camera |
| 🔔 Real-time Alerts | WebSocket push + audio beep on violation |
| 📁 Evidence Gallery | Auto-saves proof images with violation stamps |
| ⚡ FastAPI + WebSocket | Low-latency streaming at ~30 FPS |

---

## 🗂️ Project Structure

```
smart-traffic-ai/
├── run.py                        # ← Start here
├── requirements.txt
├── README.md
│
├── app/
│   ├── main.py                   # FastAPI server, WebSocket, camera loop
│   ├── detection/
│   │   ├── detector.py           # YOLOv8 + OpenCV detection engine
│   │   └── run_detector.py       # Standalone detector (no server needed)
│   ├── ocr/
│   │   └── plate_reader.py       # EasyOCR / Tesseract plate recognition
│   └── utils/
│       ├── challan.py            # E-challan generator
│       └── state.py              # In-memory system state
│
├── models/
│   └── tf_classifier.py          # TensorFlow secondary classifier
│
├── templates/
│   └── dashboard.html            # Live monitoring dashboard UI
│
├── static/
│   └── css/extra.css
│
└── violations/                   # Auto-created: proof images + challan TXTs
```

---

## 🚀 Installation

### 1. Clone / Download the project

```bash
git clone https://github.com/your-username/smart-traffic-ai.git
cd smart-traffic-ai
```

### 2. Create a virtual environment (recommended)

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS / Linux
python3 -m venv venv
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

> **GPU users:** Install the CUDA-enabled PyTorch first:
> ```bash
> pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121
> ```

### 4. (Optional) Install Tesseract OCR

- **Windows:** Download installer from https://github.com/UB-Mannheim/tesseract/wiki
- **Ubuntu/Debian:** `sudo apt install tesseract-ocr`
- **macOS:** `brew install tesseract`

---

## ▶️ Running the System

### Option A – Full Web Dashboard (recommended)

```bash
python run.py
```

Then open **http://127.0.0.1:8000** in your browser.

```bash
# Custom host/port
python run.py --host 0.0.0.0 --port 8080

# Development mode with auto-reload
python run.py --reload
```

### Option B – Standalone Detector (no browser needed)

```bash
# Demo mode (no camera required)
python app/detection/run_detector.py --demo

# Use webcam
python app/detection/run_detector.py --source 0

# Use video file
python app/detection/run_detector.py --source traffic_video.mp4
```

### Option C – Test OCR only

```bash
# Demo synthetic plate
python app/ocr/plate_reader.py --demo

# Test on a real image
python app/ocr/plate_reader.py --image path/to/plate.jpg
```

---

## 🎮 Dashboard Usage

Once running, open **http://127.0.0.1:8000**

| Button | Action |
|---|---|
| **▶ WEBCAM** | Start live webcam detection |
| **⬡ DEMO MODE** | Start simulated traffic (no camera) |
| **■ STOP** | Stop camera feed |
| **🪖 HELMET** | Manually trigger a helmet violation demo |
| **🪢 SEATBELT** | Manually trigger a seatbelt violation demo |
| **⚠ BOTH** | Trigger both violation types at once |

---

## 🌐 API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/` | Dashboard UI |
| GET | `/api/stats` | Live system statistics |
| GET | `/api/violations` | Captured violation images |
| GET | `/api/challans` | Recent e-challans |
| POST | `/api/camera/start?source=0` | Start camera (0=webcam) |
| POST | `/api/camera/stop` | Stop camera |
| POST | `/api/demo/trigger/{type}` | Trigger demo violation |
| WS  | `/ws` | WebSocket live feed |
| GET | `/docs` | FastAPI interactive docs |

---

## 📄 E-Challan Example

```
╔══════════════════════════════════════════════════════════════╗
║         GOVERNMENT OF INDIA – TRAFFIC DEPARTMENT            ║
║              E-CHALLAN NOTIFICATION SYSTEM                  ║
╚══════════════════════════════════════════════════════════════╝

CHALLAN ID    : ECHAB12345678
ISSUED ON     : 2024-07-15T14:32:17.123456
DUE DATE      : 30-07-2024

VEHICLE NUMBER : MH12CD5678
VIOLATION TYPE : No Helmet
DESCRIPTION    : Motorcyclist riding without helmet – safety violation.

FINE AMOUNT    : ₹1000
PAYMENT STATUS : Pending

ISSUED BY      : Inspector Rajesh Kumar (Badge #TR-1042)
COURT          : Metropolitan Magistrate Court, New Delhi
```

---

## 🔧 Configuration

Edit `.env` (create if needed) to override defaults:

```env
CAMERA_SOURCE=0
VIOLATION_DIR=violations
HOST=127.0.0.1
PORT=8000
```

---

## 🧠 AI Stack

| Component | Technology |
|---|---|
| Object Detection | YOLOv8n (Ultralytics) |
| Deep Learning | PyTorch 2.3 |
| Secondary Classifier | TensorFlow 2.x / MobileNetV2 |
| OCR | EasyOCR + Tesseract |
| Video Processing | OpenCV 4.9 |
| Web Framework | FastAPI + Uvicorn |
| Real-time Comms | WebSockets |

---

## 📸 Violation Evidence

Proof images are automatically saved to `/violations/` with:
- Red border overlay
- Violation type stamped on image
- Date/time watermark
- Number plate text
- Corresponding `.txt` challan file

---

## 🏗️ Production Deployment

```bash
# Run with multiple workers
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 2

# With HTTPS (requires SSL certificate)
uvicorn app.main:app --host 0.0.0.0 --port 443 \
  --ssl-keyfile key.pem --ssl-certfile cert.pem
```

---

## 📋 Interview Talking Points

- **Real-time pipeline:** OpenCV captures frames → YOLOv8 detects objects → OCR reads plates → Challan generated → WebSocket pushes to browser — all under 50ms per frame
- **Graceful degradation:** System runs in demo mode when no camera/model available — perfect for offline interviews
- **Clean architecture:** Detector, state, challan generation are fully decoupled modules
- **WebSocket streaming:** Base64-encoded JPEG frames pushed over WS — no polling required
- **No database:** Entire state held in Python dicts + local files — zero infra overhead
- **TF integration:** Shows ability to chain multiple ML frameworks (YOLOv8 + TF classifier)

---

## 📜 License

MIT License – Free for personal, educational, and interview use.
