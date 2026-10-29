# CareerPilot AI — Light UI Redesign (October 2026)

This version updates the **existing code**, not a screenshot or a separate demo application.

## What's changed

- **New colors:** light gray page (#F8FAFC), white cards (#FFFFFF), blue primary actions (#2563EB), indigo highlights, readable slate text.
- **Header:** compact responsive navigation: ATS Match, Resume Tailor, Mock Interview, Live Jobs, Upload Resume.
- **ATS:** extracted skills retained; recent matches, comparison details, relevance estimate, matching skills and gaps are more compact.
- **Resume Tailor:** original vs improved verified bullets retained; STAR explanation collapsible; preview sections clearer; copy and download unchanged.
- **Mock Interview:** shorter section labels, a simpler control row, compact status and feedback.
- **Live Jobs:** shorter header and job cards, compact status statistics, application-email field moved into the expandable job information section. Full job descriptions remain available under **Full job details**.
- **Navigation:** active tab now includes `aria-current` and keyboard-visible focus rings.

## Features intentionally preserved

Resume upload (PDF/DOCX/TXT), automatic skills extraction, backend `/api/` endpoints, live job feed retrieval, posting filters, job selection, ATS relevance comparison, original employer application links, email drafts, manual applied tracking, resume notes copy/download, HR interview planning and feedback, microphone and text answers.

**Clarifications:** Job relevance scores are heuristic, not employer ATS scores or hiring probabilities. A click on an application link opens the original website: CareerPilot does not automatically submit applications. The public job APIs require an Internet connection and can be temporarily unavailable.

## Run locally

```powershell
python -m pip install -r requirements-interview.txt
python run_server.py
```

Open `http://127.0.0.1:8080`. Hard-refresh with `Ctrl+Shift+R` if your browser caches the previous layout.

## Deploy on Render

- **Root Directory:** leave blank when `src/`, `frontend/`, and `requirements-interview.txt` are in repository root.
- **Build Command:** `pip install -r requirements-interview.txt`
- **Start Command:** `uvicorn src.voice_agent:app --host 0.0.0.0 --port $PORT`
- **Environment:** configure `GROQ_API_KEY` privately (optional for advanced interview feedback).

## Quality checks

```powershell
python -m pytest tests/ -q
```

The frontend uses the pre-existing Tailwind CDN and Lucide icons. The page still needs the CSS CDN for its full responsive utility styles; a self-hosted production CSS build would be a useful future improvement.

## Main files changed

- `frontend/index.html` — colors, layout, labels, responsive navigation and dynamically rendered cards.
- `tests/test_light_dashboard.py` — checks for core UI elements and preserved bindings.
- `UI_REDESIGN_EN.md` — this guide.
