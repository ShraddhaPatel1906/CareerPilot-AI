# CareerPilot AI — ATS Matching and Resume Tailoring Update

This update improves the **ATS Match & Analysis** and **Resume Tailoring (STAR)** dashboard sections without replacing the existing resume upload, mock interview, Live Jobs Hub, job-description formatting, apply links, or email-draft features.

## ATS Match & Analysis

- **Your Extracted Skills** keeps the existing resume-derived skills list.
- **Recent Jobs Matching Your Resume** replaces the previous static target-job options. It uses the same recent-job API data as Live Jobs Hub.
- Select a posting-age filter of **2, 3, 7, 14, or 30 days** and refresh the results as needed.
- Select an opening to see its company, title, location, posting date, required skills, overlapping skills, match explanation, and original listing/application link.
- **Resume–Job Fit** is a heuristic relevance estimate based on available resume and job-description information. It is **not** an employer ATS result or hiring probability.
- If no verifiable recent openings are returned, the dashboard does not invent jobs or match scores. You can optionally compare a pasted job description, which is marked as a manual comparison rather than a live opening.

## Resume Tailoring (STAR)

- The selected job from ATS Match & Analysis is carried over to this tab.
- **Original Resume vs Tailored STAR Bullets** stays in place, with the original text shown alongside clearer wording grounded in the resume.
- The right panel, **Improved Resume Notes**, presents a professional-summary draft, verified matching skills, existing project details, and a review checklist.
- Users can copy text, download editable **.txt** notes, or open the selected job's application page.
- The application does not invent unsupported experience, skills, results, or numerical metrics. The preview is a set of notes—not a finished, verified DOCX or PDF resume.

## Run locally with VS Code (Windows)

1. Extract the project ZIP and open its `Project` folder in VS Code.
2. Open the integrated terminal and run:

```powershell
python -m pip install -r requirements-interview.txt
python run_server.py
```

3. Visit **http://127.0.0.1:8080**.
4. Upload your resume, open **ATS Match & Analysis**, and select **3 days**. If no listings are available, try **7, 14, or 30 days**.
5. Open **Resume Tailoring (STAR)** to review notes based on the same selected job.

## Render deployment

- **Build command:** `pip install -r requirements-interview.txt`
- **Start command:** `uvicorn src.voice_agent:app --host 0.0.0.0 --port $PORT`
- **Optional:** `GROQ_API_KEY` improves AI interview functionality; it is not required for the default public job feeds.

## Testing and limitations

- The Python test suite was run in the previous release workflow.
- Frontend job selection and tailoring flows were exercised using **mocked job-feed responses**. Actual live job-provider availability could not be verified from the offline test environment.
- Some feeds may have limited India-focused results. Optional employer ATS boards can be configured as described in the README.
- Neither the dashboard nor its email-draft feature automatically submits applications.
