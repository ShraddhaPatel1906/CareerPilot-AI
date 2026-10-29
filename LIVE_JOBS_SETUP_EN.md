# CareerPilot AI — Recent Live Jobs and Applying

## 1. Start the app in VS Code

1. Extract the ZIP and open the `Project` folder in VS Code.
2. Open the integrated terminal:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-interview.txt
python run_server.py
```

3. Go to **http://127.0.0.1:8080** in your browser.
4. Use **Upload / Change Resume** to upload a PDF, DOCX, or TXT resume. The parser may extract an email address if one is present.
5. Open **Live Jobs Hub**. The default window shows jobs published within the last **3 days**, matched against your resume's skills and target role.
6. Change the window to **2, 3, 7, 14, or 30 days** and choose an available location filter such as **India**, **Remote**, or **All**.

## 2. How to apply to a real job

- **Apply on Employer ATS:** Opens an official Lever or Greenhouse application URL when supported by the listing.
- **Open Listing / Apply:** Opens the actual source listing from Remotive, Arbeitnow, or Jobicy. You may need to follow a further link to the employer's site.
- **Draft Email (listed contact):** Available only when a listing explicitly provides an application email address. It opens a draft in your configured mail app; you must attach the resume and send the email yourself.
- **Mark Applied After Sending:** Lets you track an application you completed. It does **not** prove that the app submitted a form automatically.

**Important:** An email address written on a resume is not authorization to send messages from that inbox. Automatic Gmail sending would require a secure OAuth integration and user consent; it is not part of this release.

## 3. Job feeds and optional ATS boards

The default public feeds are **Remotive**, **Arbeitnow**, and **Jobicy**. They do not require an API key, but they depend on external network access and the provider's availability. The app does not create fake fallback listings. Listings must have a usable posting date for recent-date filtering.

If you want to add known employer boards, configure valid board slugs in `.env` or your Render environment:

```env
CAREERPILOT_LEVER_BOARDS=your-valid-lever-board-slug
CAREERPILOT_GREENHOUSE_BOARDS=your-valid-greenhouse-board-slug
```

Validate board slugs before adding them. A Greenhouse `updated_at` timestamp is not treated as a publication date.

Backend endpoint: `POST /api/jobs/recent`.

## 4. Render deployment

Connect your GitHub repository to a Render Web Service. Set the **Root Directory** to the directory containing `requirements-interview.txt` and `src`.

**Build command:**

```bash
pip install -r requirements-interview.txt
```

**Start command:**

```bash
uvicorn src.voice_agent:app --host 0.0.0.0 --port $PORT
```

A Groq key is optional for interview-related AI responses, not necessary for basic job-feed retrieval.

## 5. Privacy and limitations

- Resume content is parsed in server memory; public job-feed requests retrieve public listings and do not intentionally send candidate resume data to those job sources.
- Candidate email addresses are personal information. Before public multi-user deployment, add authentication, rate limiting, privacy disclosures, and appropriate data controls.
- Employer links can expire or have regional restrictions; successful applications are never guaranteed.
- A relevance score is only a heuristic estimate—not a probability of selection.
- Browser and backend behavior were tested with sample/mocked provider responses; actual provider availability requires testing in an environment with internet access.
