# TZI Trenér

Offline-first quiz and exam trainer for the KI/TIN university course with local SQLite progress tracking.

## Key Features
- **Question Banks:** Loads structured theory, calculation, and fill-in-the-blank sets from `banky/*.json`.
- **Practice Modes:** Supports batching, wrong-answers-only, timed mock exam, sudden death, and study mode.
- **Local Persistence:** Saves user progress via `/api/progress` into SQLite WAL (`db.py`).
- **Dual UI:** Provides both a PWA/WebAssembly interface and a legacy HTML/JS frontend.

## Tech Stack
- **Backend:** Python 3, FastAPI
- **Database:** SQLite (WAL mode)
- **Frontend:** HTML, JavaScript, PWA, WebAssembly
