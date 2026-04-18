# Auru — Biomechanical Running Analysis

Auru is a full-stack web application that analyses running videos using computer vision and returns detailed biomechanical metrics, charts, and personalised coaching insights — no wearables required.

## Features

| Metric | How it's computed |
|---|---|
| **Cadence** | Foot-strike detection via ankle Y-axis peaks (MediaPipe + SciPy) |
| **Stride length** | Body-height normalisation × peak ankle separation |
| **Vertical oscillation** | Hip-centre peak-to-trough amplitude across gait cycles |
| **L/R Symmetry** | Ratio of left-to-right foot-strike counts |
| **Overstriding** | Ankle-vs-hip horizontal position at foot contact |
| **Fatigue onset** | Sliding-window cadence drop > 5 % below baseline |
| **Coaching insights** | Rule-based tips keyed to the metrics above |

### System Architecture

```
Video upload (Next.js)
       │
       ▼
POST /upload  →  VideoStore (data/videos/{id}.mp4)
       │
POST /process →  Pipeline (background thread)
       │           ├── pose.py      — MediaPipe landmark extraction
       │           ├── metrics.py   — cadence, VO, symmetry, overstriding
       │           ├── fatigue.py   — sliding-window cadence analysis
       │           └── coaching.py  — rule-based insights
       │         OutputStore (data/outputs/{id}.json)
       │
GET /run/{id} →  JSON result (polled by the UI until completed)
GET /video/{id} → Range-request video stream
```

---

## Running Locally

### Prerequisites

- **Python 3.11, 3.12, or 3.13** — do not use 3.14, it is not yet supported by `pydantic-core`
- **Node.js 20+** and **npm 10+**

Check your versions:
```bash
python3 --version
node --version
npm --version
```

---

### Step 1 — Backend

Open a terminal and run:

```bash
# From the project root, create a virtual environment using Python 3.11
python3.11 -m venv venv311
source venv311/bin/activate        # Windows: venv311\Scripts\activate

# Install backend dependencies
cd backend
pip install -r requirements.txt
```

> **Note:** On first install, pip will compile several packages — this is normal and takes a minute.

Then start the API server using the **venv's uvicorn directly** (important — avoids picking up a system-level uvicorn):

```bash
# Still inside backend/, with venv311 active
../venv311/bin/uvicorn main:app --reload --port 8000
```

You should see:
```
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     Started reloader process [...] using WatchFiles
```

Confirm it's healthy:
```bash
curl http://localhost:8000/health
# → {"status":"ok"}
```

Interactive API docs: `http://localhost:8000/docs`

> **First analysis only:** The CV pipeline will automatically download the MediaPipe pose model (~25 MB) from Google and cache it at `data/models/pose_landmarker_full.task`. Subsequent runs are instant.

---

### Step 2 — Frontend

Open a **second terminal** (leave the backend running) and run:

```bash
# From the project root
cd frontend
npm install        # only needed once
npm run dev
```

You should see:
```
▲ Next.js 16.x.x
- Local: http://localhost:3000
```

Open `http://localhost:3000` in your browser.

---

### Step 3 — Analyse a run

1. Go to `http://localhost:3000`
2. Drag and drop a running video onto the upload zone (MP4, MOV, AVI, or WebM)
3. Enter your height in cm
4. Click **Analyse Run**
5. You'll be redirected to the results page — it polls automatically until processing completes (~30 s–2 min depending on video length)
6. Review your cadence, stride length, symmetry, fatigue onset, charts, and coaching insights

> **Best results:** Side-view treadmill footage with the full body in frame. Avoid head-on angles.

---

### Troubleshooting

| Problem | Fix |
|---|---|
| `ModuleNotFoundError: No module named 'mediapipe'` | You're running the system uvicorn, not the venv one. Use `../venv311/bin/uvicorn` explicitly. |
| `Failed to build pydantic-core` during pip install | Your Python is 3.14+, which isn't supported yet. Use Python 3.11–3.13. |
| `Network error during upload` in the browser | The backend isn't running, or `.env.local` is missing. Check `curl http://localhost:8000/health`. |
| Analysis stuck on "processing" | Check the backend terminal for a stack trace. The most common cause is a video where MediaPipe can't detect a person (bad angle, low light, partial body). |

---

## Project Structure

```
auru/
├── backend/
│   ├── main.py                # FastAPI app + CORS
│   ├── requirements.txt
│   ├── models/
│   │   └── schemas.py         # Pydantic request/response models
│   ├── routes/
│   │   ├── upload.py          # POST /upload
│   │   ├── process.py         # POST /process/{run_id}
│   │   ├── runs.py            # GET /run/{run_id}
│   │   └── video.py           # GET /video/{run_id}
│   └── services/
│       ├── pose.py            # MediaPipe landmark extraction
│       ├── metrics.py         # Cadence, VO, symmetry, overstriding, time series
│       ├── fatigue.py         # Sliding-window fatigue detection
│       ├── coaching.py        # Rule-based insights
│       ├── pipeline.py        # End-to-end orchestrator
│       └── storage.py         # Local disk abstraction (swap for S3 later)
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   │   ├── layout.tsx
│   │   │   ├── page.tsx               # Upload / home page
│   │   │   └── run/[id]/page.tsx      # Dashboard / results
│   │   ├── components/
│   │   │   ├── VideoUpload.tsx        # Drag-and-drop uploader
│   │   │   ├── VideoPlayer.tsx        # Custom video player
│   │   │   ├── MetricCard.tsx         # Individual metric display
│   │   │   ├── RunChart.tsx           # Recharts area chart wrapper
│   │   │   ├── InsightCard.tsx        # Coaching insights list
│   │   │   └── ProcessingStatus.tsx   # Loading / error state
│   │   └── lib/
│   │       ├── api.ts                 # API client (upload, process, poll)
│   │       └── types.ts               # Shared TypeScript types
│   └── .env.local                     # NEXT_PUBLIC_API_URL
└── data/
    ├── videos/                        # Raw uploaded videos
    └── outputs/                       # Analysis results (JSON)
```

---

## API Reference

| Method | Path | Description |
|---|---|---|
| `POST` | `/upload` | Upload a video file. Returns `{ run_id }`. |
| `POST` | `/process/{run_id}` | Trigger analysis. Body: `{ runner_height_m }`. |
| `GET` | `/run/{run_id}` | Poll status + retrieve results. |
| `GET` | `/video/{run_id}` | Stream video (supports `Range` requests). |
| `GET` | `/health` | Health check. |

### Example result payload

```json
{
  "run_id": "abc123",
  "status": "completed",
  "metadata": { "fps": 30, "total_frames": 3600, "duration_sec": 120 },
  "metrics": {
    "cadence": 172.4,
    "stride_length": 1.18,
    "vertical_oscillation": 0.031,
    "symmetry_score": 0.94,
    "fatigue_frame": 2700,
    "fatigue_time_sec": 90.0,
    "overstriding_count": 3,
    "events": [
      { "type": "fatigue", "frame": 2700, "time_sec": 90.0 },
      { "type": "overstride", "frame": 480, "time_sec": 16.0 }
    ]
  },
  "insights": [
    "Your cadence of 172 spm is excellent...",
    "Vertical oscillation looks efficient...",
    "Fatigue onset detected around 1:30 into the run..."
  ],
  "cadence_over_time": [{ "frame": 450, "time_sec": 15.0, "value": 174.0 }],
  "hip_y_over_time": [...]
}
```

---

## Tips for best results

- **Side-view footage** is required — the runner should be visible from the side, not head-on
- **Treadmill videos** work best (stable camera, consistent framing)
- Ensure the **full body is in frame** (ankles to head) throughout the clip
- Good **lighting** significantly improves MediaPipe landmark accuracy
- Update `runner_height_m` in the upload form for accurate stride-length estimation

---

## Extending for drone / external camera input

The `services/storage.py` abstraction is designed for easy replacement:

1. Swap `VideoStore.save` / `VideoStore.path` to pull from an S3 bucket or drone stream URL
2. The `pose.py` `extract_landmarks` function accepts any local file path — feed it a downloaded chunk or a temp file from the drone feed
3. Add a `POST /ingest` route that accepts a drone session ID and triggers the same pipeline

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Next.js 16 (App Router), TypeScript, Tailwind CSS, Recharts |
| Backend | Python 3.11+, FastAPI, Uvicorn |
| CV / ML | MediaPipe Pose, OpenCV |
| Signal processing | NumPy, SciPy |
| Storage | Local filesystem (MVP) |
