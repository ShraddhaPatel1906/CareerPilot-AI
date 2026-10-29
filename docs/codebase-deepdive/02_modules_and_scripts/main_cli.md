# Module Deep-Dive: Command-Line Interface (`main.py`)

## 1. Technical Concepts & Design Patterns

The `main.py` script serves as the standalone Command-Line Interface (CLI) and end-to-end integration test harness for CareerPilot AI.

### Key Architectural Concepts
1. **Asynchronous Runtime Bootstrap:** Uses Python's native `asyncio.run(main())` to bootstrap asynchronous coroutines across the orchestrator, scraping agents, and browser automation drivers.
2. **Cross-Platform UTF-8 Console Safety:** Windows consoles often default to legacy code pages (e.g. `cp1252`), which fail on Unicode glyphs (such as checkmarks `✓`, emoji `🚀`, or arrows `➔`). The script reconfigures standard I/O streams dynamically:
   ```python
   if sys.platform == "win32":
       sys.stdout.reconfigure(encoding="utf-8")
       sys.stderr.reconfigure(encoding="utf-8")
   ```
3. **Fixture Ingestion & Pipeline Driving:** Deserializes sample JSON records from `data/sample_resume.json` and `data/sample_job.json` into typed `CandidateProfile` and `JobPosting` objects before delegating execution to `CareerPilotOrchestrator`.

---

## 2. Core Functions & Execution Logic

### `main() -> None`
* **Location:** `main.py`
* **Purpose:** Primary execution function for CLI-based pipeline runs.
* **Control Flow:**
  1. **Console Reconfiguration:** Enforces UTF-8 standard output and error encoding.
  2. **Candidate Ingestion:** Reads `data/sample_resume.json`, validates fields via `CandidateProfile(**candidate_data)`.
  3. **Job Batch Loading:** Reads `data/sample_job.json`, instantiates an array of `JobPosting` objects.
  4. **Orchestrator Execution:** Instantiates `CareerPilotOrchestrator(match_threshold=70.0)` and triggers `orchestrator.run_pipeline(candidate, jobs)`.
  5. **Terminal Report Rendering:** Prints an ASCII summary table detailing job titles, match percentages, qualification verdicts, and safety air-gap messages.

---

## 3. Concrete Example & Usage

```bash
# Execute the full multi-agent pipeline via command line
python main.py
```

### Sample Terminal Execution Output

```text
2026-10-27 15:30:10 [INFO] Initializing CareerPilot AI Autonomous Execution Pipeline...
2026-10-27 15:30:10 [SUCCESS] Loaded Candidate: Shraddha (1.0 yrs exp)
2026-10-27 15:30:10 [SUCCESS] Loaded 12 Target Job Postings for Evaluation.
2026-10-27 15:30:10 [INFO] Starting CareerPilot AI pipeline for: Shraddha

--- Processing Job: Data Scientist at Zepto ---
2026-10-27 15:30:10 [INFO] ATS Match Score: 88.5% (Threshold: 70.0%)
2026-10-27 15:30:10 [INFO]   [+] Strength: Direct technical skill coverage matches 85% of requirements. (Impact: +0.28)
2026-10-27 15:30:10 [INFO] Match passed threshold! Generating tailored STAR resume...
2026-10-27 15:30:11 [INFO] Executing browser applicator with Pre-Submission Air-Gap...

======================================================================
CAREERPILOT AI: PIPELINE EXECUTION SUMMARY
======================================================================

Role: Data Scientist at Zepto
Match Score: 88.5% [APPROVED & HITL READY]
Status: READY_FOR_HITL_REVIEW
Safety Gate: [Simulation] Form successfully filled. Final submission blocked pending operator approval.

Role: Senior AI Platform Architect at Google Cloud
Match Score: 32.0% [DISCARDED]
Status: DISCARDED_BELOW_THRESHOLD
======================================================================
```
