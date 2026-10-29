# CareerPilot AI — Resume-Based Mock Interview (Fixed)

This update focuses on the **mock interview** section of the existing dashboard. The other job-scoring/application modules are left as they were.

## Quick start on Windows (PowerShell)

1. Extract this ZIP to a folder, open a terminal inside the **Project** directory.
2. Create an environment (once):

   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   pip install -r requirements-interview.txt
   ```

   If PowerShell blocks activation, use Command Prompt instead (`.venv\Scripts\activate.bat`), or install without activation using `.venv\Scripts\python.exe -m pip install -r requirements-interview.txt`.
3. Run:

   ```powershell
   python run_server.py
   ```

   Or double-click `run.bat` after installing dependencies. The dashboard opens at **http://127.0.0.1:8080**.
4. Open the **Mock Interview** tab → **Upload Resume File** (text-based PDF/DOCX/TXT), or **Paste Resume Text Directly**. The extracted profile is editable through the **Upload / Change Resume** modal.
5. Click **Start Interview**. Listen to the interviewer, speak via mic or type the answer, then click **Submit Answer for Evaluation**. Answer the follow-up to move on. Use **Next Question** to skip.
6. Use **Pause Interview**, **Restart Session**, or **End & Summary** as required.

## What changed?

- Proper **server-side** text extraction for PDF, DOCX and TXT instead of treating DOCX as plain text.
- Resume **projects, skills, education and experience** are parsed from each uploaded file; no fixed candidate/project is injected into uploaded data.
- Roughly **24–28 main questions**, plus an answer-based follow-up after each. The plan begins with self-introduction, then projects, technical skills, education/experience, behavioral HR questions, and closing.
- Interview target **45 minutes** (40–50 minutes). Actual duration depends on how long the candidate speaks; timer shows real elapsed time and ends at 50 minutes.
- An optional **Groq** integration produces more natural, context-aware feedback and follow-ups. Without an API key the system still works, but feedback is clearly marked as a **practice heuristic**, not a reliable judgement of technical correctness.
- Fix for microphone transcript overwriting when the browser sends successive speech recognition results.
- The script no longer uses a fixed `D:\Project` path.

## Optional: smarter HR-style response evaluation with Groq

Copy `.env.example` to `.env` and set your **own** `GROQ_API_KEY`. Do not put the key in HTML/JavaScript, share it in public ZIPs, or commit it to Git. When enabled, the app sends each submitted answer and a **limited resume profile** to Groq for evaluation and a tailored follow-up; leave it blank if you prefer local practice. This is an optional external service and requires network connectivity.

## Important limitations

- PDF resumes that are scanned pictures, heavily formatted/2-column layouts, password-protected, or without selectable text may need OCR or manually pasted text. Review parsed skills/projects before starting.
- Voice-to-text relies on browser speech recognition. Chrome/Edge and microphone permissions are recommended; typed answers always work.
- A real 40–50 minute interview **cannot be guaranteed solely by a question count**; time varies with answers and pauses.
- Older built-in demo candidates are examples only. Uploading another candidate's resume replaces the active interview profile. An API key is not required to generate the main questions.
- Feedback is coaching, not a certified HR hiring decision. The dashboard's separate ATS/job application demo is unchanged and may contain simulated data.

**Security note:** The original uploaded `.env.example` included key-like values. The sample file in this ZIP has been cleaned. If those values were real active credentials, revoke/rotate them in the respective provider dashboards before sharing your repository.
