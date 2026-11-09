# Suraksha Live

**Detect the threat before you trust the voice.**

Suraksha Live is a speech-based scam-call screening demo. It transcribes a short audio clip with Gnani Prisma STT, then checks the transcript for suspicious patterns such as digital-arrest threats, fake KYC requests, OTP or UPI PIN requests, and pressure to transfer money.

The app is a decision-support demo. Its rule-based score is not proof that a call is fraudulent and must not replace independent verification.

## What works

- Record a short clip in the browser or upload an audio file.
- Convert browser recordings to 16 kHz mono WAV before upload.
- Send audio to the configured Gnani Prisma STT endpoint.
- Analyze the returned transcript with an explainable, rule-based detector.
- Show risk level, matched indicators, evidence lines, and safety guidance.
- Analyze pasted text without using Gnani credits.
- Keep recent results in browser memory for the current session only.

## Current limitations

- **Batch processing only:** audio is analyzed after recording stops. Continuous live streaming is not implemented.
- The REST audio request is limited to 30 seconds by the current integration.
- Speech recognition requires a valid Gnani API key with Prisma STT access and available account quota.
- No Gnani TTS voice alerts are implemented yet.
- Detection is rule-based and can miss scams or flag unusual but legitimate wording. Always verify using official contact details.
- Use synthetic or consented audio only. Do not upload private calls without permission.

## Technology

- Frontend: React, JavaScript, Vite
- Backend: Python, FastAPI, Pydantic
- Speech-to-text: Gnani Prisma STT (configured model: `prisma-v2.5`)
- Tests: Python unittest, Node.js built-in test runner

## Run locally

### 1. Backend

Python 3.13 is recommended.

~~~powershell
cd backend
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
~~~

Open backend/.env and set your own Gnani key:

~~~env
GNANI_API_KEY=your_gnani_api_key
GNANI_STT_MODEL=prisma-v2.5
MAX_UPLOAD_MB=10
~~~

Never commit .env or share the key. Start the API:

~~~powershell
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
~~~

Health check: http://127.0.0.1:8000/api/health

### 2. Frontend

Open a second terminal:

~~~powershell
cd frontend
npm ci
npm run dev
~~~

Open the local Vite URL shown in the terminal (normally http://localhost:5173).

For a deployed backend, set VITE_API_URL in the Vercel project to the backend origin, for example https://your-backend.onrender.com. If it is not set, the frontend uses https://surakshalive.onrender.com.

## Run tests

Backend:

~~~powershell
cd backend
python -m unittest discover -s tests -v
~~~

Frontend tests and production build:

~~~powershell
cd frontend
npm ci
npm test
npm run build
~~~

The backend STT tests use mocked transports. They do not call Gnani and do not consume API credits. A real audio test is separate and requires a working API key.

## Deploy

### Backend on Render

- Create a Python Web Service from this repository.
- Set the root directory to backend.
- Build command: pip install -r requirements.txt
- Start command: uvicorn app.main:app --host 0.0.0.0 --port $PORT
- Set environment variables in Render: GNANI_API_KEY, GNANI_STT_MODEL=prisma-v2.5, and MAX_UPLOAD_MB=10.
- Do not upload .env to GitHub or Render as a file.

### Frontend on Vercel

- Import the same repository.
- Set the root directory to frontend.
- Build command: npm run build
- Output directory: dist
- Set VITE_API_URL to the deployed backend origin if it differs from the default.

## API routes

| Method | Route | Purpose |
|---|---|---|
| GET | / | Basic API status |
| GET | /api/health | Health and configuration status |
| POST | /api/analyze | Analyze pasted transcript |
| POST | /api/transcribe | Transcribe audio only |
| POST | /api/analyze-audio | Transcribe audio and analyze it |

## Sample scenarios

The sample-scripts/ folder contains synthetic examples for digital arrest, fake KYC, UPI refund, and a legitimate call. These are test examples, not real customer conversations.
