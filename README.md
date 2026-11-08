# Suraksha Live

Suraksha Live is a small project I built to experiment with detecting common phone-scam patterns in Hindi, English and Hinglish speech.

The flow is:

1. Record a short sample in the browser, or choose an audio file.
2. The frontend sends the audio to the FastAPI backend.
3. The backend sends it to Gnani Prisma STT and gets a transcript.
4. A rule-based detector checks the transcript for known warning signs.
5. The app shows the matched phrases, a risk level and a suggested next step.

You can also paste a transcript and run the detector without calling Gnani. That is useful for testing and does not use STT credits.

**This is a prototype, not a bank or police product.** A high-risk result is a warning to stop and verify; it is not proof that a call is a scam. A low-risk result does not guarantee that a call is safe.

## What is implemented

- Browser audio recording and file upload.
- Audio conversion in the frontend before upload.
- Batch transcription through the Gnani Prisma REST API.
- Transcript analysis using explicit pattern rules.
- Evidence for each matched rule, including the original transcript line.
- Text-only analysis that works without an STT key.
- Sample transcripts for digital-arrest, fake-KYC, UPI-refund and legitimate-call scenarios.

## What is not implemented

- Continuous live transcription or streaming detection. The app waits until recording stops, then uploads the audio.
- Text-to-speech alerts.
- A trained machine-learning classifier. The current detector uses regular-expression rules and a weighted score.
- Guaranteed scam detection. Rules can miss new wording and can also flag legitimate conversations.

The audio request is limited to 30 seconds by the current integration. The upload-size limit is configurable, up to 25 MB.

## Stack

- Frontend: React, JavaScript and Vite
- Backend: Python and FastAPI
- Speech-to-text: Gnani Prisma v3.0
- Tests: Python `unittest` and Node's built-in test runner

## Run it on Windows

### Backend

Python 3.13 is recommended.

```powershell
cd backend
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Open `backend/.env` and add your own key:

```env
GNANI_API_KEY=your_gnani_api_key
GNANI_STT_MODEL=prisma-v3.0
MAX_UPLOAD_MB=25
```

Keep this key private. Do not commit the `.env` file or paste the key into an issue or chat.

Start the backend from the `backend` folder:

```powershell
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

The health endpoint is http://127.0.0.1:8000/api/health.

### Frontend

Open another terminal:

```powershell
cd frontend
npm ci
npm run dev
```

Open the local URL printed by Vite (usually http://localhost:5173).

If your backend is running somewhere other than the default deployment, set `VITE_API_URL` to its base URL in the frontend environment. For example:

```env
VITE_API_URL=http://127.0.0.1:8000
```

## Tests

Run backend tests from the `backend` folder:

```powershell
python -m unittest discover -s tests -v
```

Run frontend tests and make a production build from the `frontend` folder:

```powershell
npm test
npm run build
```

The STT client tests use a fake transport. They check request construction and error handling; they do not contact Gnani or prove that the account key has live STT permission.

## Deployment notes

### Backend (Render)

Use `backend` as the service root directory.

- Build command: `pip install -r requirements.txt`
- Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`

Add these environment variables in the Render service settings:

- `GNANI_API_KEY`: your private Gnani key
- `GNANI_STT_MODEL`: `prisma-v3.0`
- `MAX_UPLOAD_MB`: `25`

If `MAX_UPLOAD_MB` is already set to a different value in Render, that value overrides the code default.

### Frontend (Vercel)

Use `frontend` as the project root directory.

- Build command: `npm run build`
- Output directory: `dist`
- Set `VITE_API_URL` to the backend URL if you are not using the default configured backend.

## API routes

| Method | Route | Purpose |
|---|---|---|
| GET | `/` | Basic backend status |
| GET | `/api/health` | Backend and configuration status |
| POST | `/api/analyze` | Analyze a transcript |
| POST | `/api/transcribe` | Transcribe an audio file |
| POST | `/api/analyze-audio` | Transcribe audio, then analyze the transcript |

One detail about the health check: `gnani_configured: true` only means that a key is present in the backend environment. It does not confirm that Gnani has enabled Prisma STT for that key. A real audio request is needed to check access.

## Sample transcripts

The `sample-scripts/` folder contains short, fictional examples used by the detector tests. They are not recordings of real people.
