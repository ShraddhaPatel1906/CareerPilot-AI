# Module Deep-Dive: Autonomous Applicator & HITL Safety (`src/applicator_agent.py`)

## 1. Technical Concepts & Design Patterns

The `applicator_agent.py` module automates candidate interaction with complex enterprise job application portals using **Playwright**. It pairs autonomous form filling with a mandatory **Pre-Submission Air-Gap (Human-in-the-Loop)**.

### Key Architectural Concepts

#### 1. DOM Target Discovery & Hidden File Uploads
Modern frontend frameworks (React, Vue, Angular) frequently style file upload elements with custom drag-and-drop divs while setting the underlying `<input type="file">` to `display: none` or opacity zero. Standard naive clicking fails on these hidden nodes.
The Applicator Agent resolves this by using Playwright's locator API directly on the DOM node:
```python
file_input = page.locator('input[type="file"]').first
await file_input.set_input_files(file_path)
```
This directly binds the compiled PDF buffer into the browser's native file transfer list, bypassing styled CSS wrappers and anti-interaction overlays.

#### 2. Anti-Bot Evasion & Stealth Flags
Modern job portals are frequently protected by Cloudflare, DataDome, or PerimeterX bot management software. When launching Chromium, the agent strips automated telemetry flags:
```python
browser = await p.chromium.launch(
    headless=self.headless,
    args=["--disable-blink-features=AutomationControlled"]
)
```
This prevents the browser runtime from setting `navigator.webdriver = true`.

#### 3. Pre-Submission Air-Gap (Human-in-the-Loop Safeguard)
Fully autonomous application submission introduces immense real-world risk (accidental duplicate submissions, outdated candidate details, misaligned salary expectations).
The agent implements an architectural **Air-Gap**:
* Navigates the application wizard.
* Fills all demographic, identity, work history, and URL fields.
* Attaches the tailored resume PDF.
* Detects the presence of final submission triggers (`"Submit Application"`, `"Apply Now"`).
* **Strictly halts execution before clicking the trigger**, capturing the form state and emitting an operator review notice.

---

## 2. Core Classes & Methods

### `ApplicatorAgent`
* **Location:** `src/applicator_agent.py`
* **Purpose:** Browser automation controller and pre-submission safety guardian.

#### Methods & API

##### `__init__(headless: bool = True, hitl_webhook: Optional[str] = None)`
* **Inputs:** 
  * `headless` (`bool`): Determines whether Chromium runs headlessly or with a visible window.
  * `hitl_webhook` (`Optional[str]`): Optional Slack/Discord webhook URL for dispatching review cards.

##### `async fill_application(candidate: CandidateProfile, job: JobPosting, resume_pdf_path: str) -> Dict[str, Any]`
* **Inputs:** Candidate identity data, target job listing, and absolute file path to the compiled resume PDF.
* **Outputs:** Structured status dictionary (e.g. `{"status": "READY_FOR_HITL_REVIEW", ...}`).
* **Side Effects:** Launches Chromium, executes page navigation, fills input locators, attaches resume, and halts at the air-gap.

##### `async _fill_text_input(page, target_names: list, value: str)`
* **Inputs:** Active Playwright page context, list of candidate field identifiers (e.g. `["first_name", "firstname"]`), and input text value.
* **Mechanism:** Queries selectors matching `input[name*="..."]`, `input[id*="..."]`, and `input[placeholder*="..."]`. Fills the first visible matching element.

##### `async _handle_file_upload(page, file_path: str)`
* **Inputs:** Active page and local PDF file path.
* **Mechanism:** Locates `input[type="file"]` elements and uploads the binary payload.

##### `async _pre_submission_airgap(page, job: JobPosting) -> Dict[str, Any]`
* **Inputs:** Active page and target job posting.
* **Outputs:** Review report indicating successful field population and submission halt.

---

## 3. Concrete Example & Usage

```python
import asyncio
from src.schemas import CandidateProfile, JobPosting
from src.applicator_agent import ApplicatorAgent

async def run_applicator_demo():
    agent = ApplicatorAgent(headless=True)

    candidate = CandidateProfile(
        candidate_id="c_1",
        full_name="Alex Mercer",
        email="alex@example.com",
        phone="+91-9876543210",
        linkedin_url="https://linkedin.com/in/alexmercer",
        github_url="https://github.com/alexmercer",
        total_experience_years=3.0,
        seniority_level=2,
        education=[],
        experiences=[],
        verified_skills=["Python", "SQL"],
        raw_resume_text="..."
    )

    job = JobPosting(
        id="job_gh_12",
        external_id="12",
        ats_platform="greenhouse",
        company_name="Zepto",
        title="Data Scientist",
        location="Bengaluru, India",
        description_text="...",
        apply_url="https://boards.greenhouse.io/zepto/jobs/12",
        source_url="https://boards.greenhouse.io/zepto/jobs/12"
    )

    # Execute automated form-filling with pre-submission air-gap
    result = await agent.fill_application(
        candidate=candidate,
        job=job,
        resume_pdf_path="sample_resume.pdf"
    )

    print(f"Application Status: {result['status']}")
    print(f"Company: {result['company']} | Role: {result['role']}")
    print(f"Safety Gate Message: {result['message']}")
    # Output: Form successfully filled. Final submission blocked pending operator approval.

if __name__ == "__main__":
    asyncio.run(run_applicator_demo())
```
