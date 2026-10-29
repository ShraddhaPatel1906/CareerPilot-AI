# Module Deep-Dive: Multi-Agent Orchestrator (`src/orchestrator.py`)

## 1. Technical Concepts & Design Patterns

The `orchestrator.py` module coordinates the multi-agent execution pipeline in CareerPilot AI. Built upon **LangGraph State Graph** and **Mediator Design Patterns**, it manages the cyclic lifecycle from job discovery to application preparation.

### Key Architectural Concepts

#### 1. Threshold-Gated Resource Conservation
In high-throughput job application pipelines, invoking Large Language Models (LLMs) or browser automation on every scraped job is prohibitively expensive and slow.
The orchestrator implements a **Conditional Gate**:
```
Scout -> XGBoost Scoring (1.5ms) -> Match Score >= 70%?
                                       |
                                       +--> NO  -> Discard immediately (0 LLM tokens, 0 browser cycles)
                                       +--> YES -> Tailor STAR Resume -> Playwright Air-Gap (HITL)
```
Only candidate-job pairs achieving a calibrated match score $\ge 70.0\%$ advance to the tailoring and browser stages. This filters out 60–80% of low-probability listings, saving compute and tokens.

#### 2. Isolated Agent Boundaries
Each agent operates as an isolated worker with explicit dependencies:
- Failures in external web scraping (`ScoutAgent`) do not halt evaluation of cached jobs.
- Failures in browser rendering (`ApplicatorAgent`) do not corrupt generated resumes or ML score reports.
- All state updates pass through typed Pydantic payloads (`AgentWorkflowState`).

---

## 2. Core Classes & Methods

### `CareerPilotOrchestrator`
* **Location:** `src/orchestrator.py`
* **Purpose:** Central coordinator orchestrating the multi-agent pipeline.

#### Methods & API

##### `__init__(match_threshold: float = 70.0)`
* **Inputs:** `match_threshold` (`float`, default `70.0`).
* **Sub-Agents Instantiated:**
  * `self.scout`: `ScoutAgent` for ATS ingestion.
  * `self.scorer`: `ATSPredictiveEngine` for XGBoost inference and TreeSHAP explainability.
  * `self.tailor`: `ResumeTailorAgent` for STAR tailoring and Typst compilation.
  * `self.applicator`: `ApplicatorAgent(headless=True)` for browser automation.

##### `async run_pipeline(candidate: CandidateProfile, sample_jobs: List[JobPosting]) -> List[Dict[str, Any]]`
* **Inputs:** Parsed candidate profile and a list of target job postings.
* **Outputs:** List of status dictionaries detailing match percentages, SHAP feature drivers, tailoring results, and browser submission states.
* **Step-by-Step Execution Sequence:**
  1. **Inference & Attribution:** Invokes `scorer.evaluate_and_explain(candidate, job, threshold)`.
  2. **Threshold Gate Check:** If `is_shortlist_recommended` is `False`, appends `DISCARDED_BELOW_THRESHOLD` and advances to next job.
  3. **Resume Synthesis:** If passed, invokes `tailor.tailor_experience_local(candidate, job)` and `tailor.export_to_typst(...)`.
  4. **Browser Automation:** Invokes `applicator.fill_application(...)` with the compiled PDF, halting at the pre-submission air-gap.

---

## 3. Concrete Example & Usage

```python
import asyncio
from src.schemas import CandidateProfile, JobPosting
from src.orchestrator import CareerPilotOrchestrator

async def demo_orchestrator():
    orchestrator = CareerPilotOrchestrator(match_threshold=70.0)

    # 1. Provide candidate and jobs
    candidate = CandidateProfile(
        candidate_id="c_1",
        full_name="Alex Mercer",
        email="alex@example.com",
        phone="555-0199",
        total_experience_years=3.0,
        seniority_level=2,
        education=[],
        experiences=[],
        verified_skills=["Python", "SQL", "Pandas", "Scikit-Learn"],
        raw_resume_text="..."
    )

    high_match_job = JobPosting(
        id="j_high",
        external_id="101",
        ats_platform="greenhouse",
        company_name="Zepto",
        title="Data Scientist",
        location="Bengaluru",
        description_text="Python, SQL, Pandas, Scikit-Learn required.",
        required_skills=["Python", "SQL", "Pandas", "Scikit-Learn"],
        required_experience_years=2.0,
        apply_url="https://example.com/apply",
        source_url="https://example.com/apply"
    )

    low_match_job = JobPosting(
        id="j_low",
        external_id="102",
        ats_platform="workday",
        company_name="GlobalBank",
        title="Principal Java Architect",
        location="New York",
        description_text="Java, Spring Boot, Microservices. 10+ years exp.",
        required_skills=["Java", "Spring Boot", "Kubernetes"],
        required_experience_years=10.0,
        apply_url="https://example.com/apply2",
        source_url="https://example.com/apply2"
    )

    # 2. Execute end-to-end pipeline
    results = await orchestrator.run_pipeline(candidate, [high_match_job, low_match_job])

    # 3. Verify gate execution
    for r in results:
        print(f"Job: {r['title']} at {r['company']}")
        print(f"  Score: {r['score']}% | Status: {r['status']}")
    # Output:
    # Job: Data Scientist at Zepto -> Score: 88.5% | Status: READY_FOR_HITL_REVIEW
    # Job: Principal Java Architect at GlobalBank -> Score: 12.0% | Status: DISCARDED_BELOW_THRESHOLD

if __name__ == "__main__":
    asyncio.run(demo_orchestrator())
```
