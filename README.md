# AI Reflection Bracelet

Hackathon-ready monorepo for a voice-first mental wellness bracelet product aimed at college students. The hardware does not need to exist yet: the backend accepts bracelet-shaped uploads, the mobile app supports fake pairing and simulated sessions, and the whole stack runs with deterministic mock analysis when Supabase, OpenAI, or real hardware are not available.

## Monorepo

```text
apps/
  api/         FastAPI backend with modular processing pipeline and local JSON persistence fallback
  mobile/      Expo Router + TypeScript mobile app for onboarding, recap, entries, patterns, and simulation
packages/
  shared-types Shared domain types used by the mobile app
  ui-tokens    Centralized theme tokens for the warm dark UI
scripts/
  seed_demo_data.py
  simulate_bracelet_upload.py
```

## Run Locally

### Backend

```bash
cd apps/api
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

API defaults to local mocked mode and persists data to `apps/api/data/local_store.json`.

### Mobile

```bash
npm install
npm run dev:mobile
```

This launches the Expo app from `apps/mobile`. It is Expo Go compatible and expects a backend at `EXPO_PUBLIC_API_URL`, defaulting to `http://127.0.0.1:8000`.

## Demo Data

Seed a compelling demo day:

```bash
python scripts/seed_demo_data.py
```

Simulate additional bracelet uploads:

```bash
python scripts/simulate_bracelet_upload.py
```

You can also use the in-app `Simulate Bracelet Session` screen to create uploads without hardware.

## Environment Variables

Optional variables:

- `EXPO_PUBLIC_API_URL`
- `SUPABASE_URL`
- `SUPABASE_ANON_KEY`
- `OPENAI_API_KEY`
- `OPENAI_MODEL`
- `OPENAI_TRANSCRIPTION_MODEL`
- `DATABASE_URL`
- `API_BASE_URL`

If these are missing, the project still runs in local mocked mode.

For API credentials, use `apps/api/.env`. A starter template is included at `apps/api/.env.example`.

## Current Mock Strategy

- Auth is mocked through a lightweight onboarding flow and local persisted user identity.
- Device pairing is a fake scan that creates a device record through the backend.
- Audio transcription, tone analysis, heart analysis, text understanding, and GPT synthesis all use deterministic mock fallbacks unless real services are wired in.
- Daily and weekly summaries are rebuilt from stored session evaluations after each upload.

## Hardware And ML Integration

Target payload already matches the future bracelet upload contract:

```json
{
  "device_id": "bracelet-123",
  "user_id": "user-123",
  "timestamp": "2026-03-20T18:30:00Z",
  "audio_file_url": "https://...",
  "hr_summary": {
    "avg_hr": 88,
    "peak_hr": 111,
    "baseline_delta": 14
  },
  "optional_raw_ppg": [],
  "battery_status": 76
}
```

Key TODO markers in the codebase show where to:

- replace local persistence with Supabase tables and auth
- add real bracelet transport and firmware upload hooks
- plug in Whisper/OpenAI STT
- plug in SER / wav2vec2 tone modeling
- upgrade heuristic text analysis with stronger models
- enable real OpenAI structured outputs in synthesis
