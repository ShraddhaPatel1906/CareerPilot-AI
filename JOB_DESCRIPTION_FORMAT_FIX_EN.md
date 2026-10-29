# CareerPilot AI — Clean Job Description Formatting

## What was fixed

- HTML markup received from job feeds (for example, `<h3>`, `<strong>`, `<p>`, `&lt;h3&gt;`, or `&amp;lt;h3&amp;gt;`) is decoded and converted to readable text.
- Job cards present company, role, location, posting age, source, matching information, and relevant skills more clearly.
- Long job descriptions show a short overview, followed by **Read more job details** to expand available paragraphs and bullet points.
- **View job & apply** opens the original listing or application page. It does **not** automatically submit an application.
- An email-draft option appears only if the job listing explicitly contains an application contact email. You must attach your resume and send the message yourself.

## Run in VS Code

1. Extract the ZIP and open the `Project` folder.
2. Open the integrated terminal and run:

```powershell
python -m pip install -r requirements-interview.txt
python run_server.py
```

3. Visit **http://127.0.0.1:8080**, upload a resume, and navigate to **Live Jobs Hub** → **Find Real Openings**.
4. If an old UI is cached, press **Ctrl+Shift+R** to perform a hard refresh.

## Publish changes to Render

When updating an existing repository, commit and push your changes to `frontend/index.html`, `src/live_jobs.py`, and related tests:

```powershell
git add frontend/index.html src/live_jobs.py tests/test_live_jobs.py
git commit -m "Improve live job description display"
git push origin main
```

If Render Auto Deploy is enabled, it should pick up the commit. Otherwise, manually deploy from the Render dashboard.

## Verification and limits

- The earlier release reported **15 passing Python tests** for its job-description fix.
- A browser test with a sample double-encoded, Artefact-style job description passed.
- External live job APIs were not verified from the offline testing environment.
