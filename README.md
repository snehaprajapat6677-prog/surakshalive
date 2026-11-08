# surakshalive
# Suraksha Live

### Detect the threat before you trust the voice.

Suraksha Live is a speech-based scam detection project
that helps identify suspicious patterns in phone
conversations.

The idea behind this project is simple: many scams
start with a phone call. A caller may pretend to be
from a bank, police department or government office
to create fear and pressure someone into sending money
or sharing personal information.

Suraksha Live analyzes a conversation transcript and
looks for common scam-related warning signs.

## What it does

- Records audio through the browser.
- Converts recorded audio into a supported format.
- Uses Gnani AI speech-to-text for transcription.
- Analyzes transcripts for suspicious conversation patterns.
- Assigns a risk level based on detected indicators.
- Highlights suspicious statements and evidence.
- Allows users to paste a transcript for analysis.
- Shows results in a simple dashboard.

## Current Features

- Audio recording and upload.
- Batch audio transcription.
- Hindi and English language options supported
  by the configured STT model.
- Text-based scam analysis.
- Risk scoring and category detection.
- Session-based result history.
- Sample scam conversation scripts.

**Note:** Audio is analyzed after recording stops.
Real-time streaming detection is not implemented yet.

## Technology Stack

### Frontend
- React
- JavaScript
- Vite
- CSS

### Backend
- Python
- FastAPI
- Pydantic

### AI Integration
- Gnani AI Speech-to-Text API
- Prisma STT model


