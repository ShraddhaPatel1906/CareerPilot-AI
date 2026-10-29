# 01 High-Level Overview: CareerPilot AI

## 1. Purpose & Core Value
In the contemporary technology employment ecosystem, the job application process is characterized by extreme friction, asymmetry, and opaque filtering mechanisms. Candidates spend dozens of hours per week manually re-formatting resumes, navigating repetitive application portals, and facing automated Applicant Tracking Systems (ATS) whose scoring criteria are entirely concealed.

**CareerPilot AI: Predictive ATS Optimization & Interactive AI Technical Interview Co-Pilot** is an autonomous, production-grade intelligence and execution platform designed to solve these fundamental asymmetries:
1. **Asymmetric Parsing & Black-Box ATS:** Replaces guesswork with calibrated Machine Learning (XGBoost) and native C++ TreeSHAP explainability, providing candidates with exact mathematical match probabilities and feature attribution drivers before applying.
2. **LLM Hallucination in Resume Tailoring:** Enforces programmatic regex AST metric-conservation guardrails that strictly prohibit the language model from fabricating metrics, unearned skills, or unverified employers during STAR resume tailoring.
3. **High Compilation Latency:** Replaces heavy, multi-gigabyte LaTeX distributions with a sub-50ms native Typst compiler producing high-aesthetic, ATS-parsable PDFs instantly.
4. **Repetitive Form Navigation with Safety:** Employs Playwright browser automation to handle custom multi-page portal forms and hidden file uploads while enforcing a strict **Pre-Submission Air-Gap (Human-in-the-Loop)** to ensure zero unauthorized submissions.
5. **Interview Unpreparedness:** Delivers a 60-minute, resume-driven technical mock interview co-pilot that dynamically derives questions from the candidate's exact projects, degrees, and skills, providing real-time HR conversational follow-ups and strict rubric evaluation.

---

## 2. Main Features

- **Multi-Platform ATS Scouting:** High-throughput extraction across Greenhouse, Lever, and Workday APIs without spawning resource-intensive headless browsers.
- **Fingerprint-Based Deduplication:** Computes deterministic SHA-256 hashes from normalized `company:external_id` tuples to prevent duplicate processing.
- **Dual-Stage NLP Grounding:** Fuses regex word-boundary pattern matching with dense sentence transformer vector embeddings (`BAAI/bge-large-en-v1.5`) mapped onto the canonical ESCO taxonomy.
- **Predictive Tabular ML Scoring:** Executes sub-millisecond inference via XGBoost decision trees over a 10-dimensional feature vector, bypassing the high latency, token costs, and prompt-injection risks of pure LLM-as-a-judge scorers.
- **Native C++ TreeSHAP Explainability:** Extracts exact Shapley values directly from XGBoost's C++ core in under 0.3 ms (`pred_contribs=True`), detailing positive scoring drivers and critical gaps.
- **Anti-Hallucination STAR Tailoring:** Decomposes candidate accomplishments into Situation, Task, Action, and Result (STAR), guaranteeing 100% metric conservation.
- **Instant Typst PDF Generation:** Compiles tailored resumes into publication-quality PDFs in under 50 ms.
- **Autonomous Playwright Applicator:** Automates complex portal forms, dropdown selections, and hidden `input[type="file"]` elements.
- **Pre-Submission Air-Gap (HITL):** Enforces a mandatory manual review gate prior to final application dispatch, preventing unintended submissions.
- **60-Minute Dynamic Technical Mock Interview:** Generates interview questions dynamically from the candidate's uploaded resume (all projects, bullets, skills, education) with conversational HR follow-up probing and strict rubric scoring.
- **Real-Time Jobs Discovery Hub:** Interactive interface featuring 12+ live tech job opportunities categorized across AI/ML Engineering, Data Science, and Analytics with posting recency badges.

---

## 3. High-Level Tech Stack

| Architectural Domain | Technologies & Libraries | Production Role & Key Responsibility |
| :--- | :--- | :--- |
| **Agentic Framework** | **LangGraph**, **Pydantic v2**, **Loguru** | State-graph coordination, strict schema contracts, and unified asynchronous logging. |
| **Data Ingestion & Scraping** | **HTTPX**, **`curl_cffi`**, **`python-jobspy`** | Non-blocking HTTP extraction and TLS fingerprint evasion for ATS REST endpoints. |
| **Machine Learning & NLP** | **XGBoost**, **LightGBM**, **TreeSHAP** | 10D feature vector inference and native C++ sub-millisecond Shapley feature attribution. |
| **Semantic Embeddings** | **Sentence-Transformers** (`bge-large-en-v1.5`), **FAISS** | Dual-encoder semantic text representation and ESCO taxonomy vector grounding. |
| **GenAI & Document Engine** | **Groq LPU** (Llama-3.3-70B), **Typst** | Ultra-fast STAR bullet rephrasing and sub-50ms PDF compilation. |
| **Browser Automation** | **Playwright** (Async Chromium) | Multi-page form automation, DOM locator targeting, and pre-submission safety halts. |
| **Web Service & Interview** | **FastAPI**, **Uvicorn**, **WebSockets** | Asynchronous REST and real-time WebSocket communication for live rubric scoring. |
| **Frontend Dashboard** | **HTML5**, **Tailwind CSS**, **Lucide Icons**, **PDF.js** | Single-page reactive application with native Web Speech synthesis and recognition. |

---

## 4. Directory Tree & Module Descriptions

```text
D:\Project\
├── docs/                           # Documentation suites and specifications
│   └── codebase-deepdive/          # Comprehensive bottom-up architectural deep-dive
│       ├── 01_high_level_overview.md
│       ├── 02_modules_and_scripts/ # Granular breakdowns of each script and module
│       │   ├── config.md           # Pydantic BaseSettings environment manager
│       │   ├── schemas.md          # Canonical DTO contracts and state definitions
│       │   ├── skill_extractor.md  # NLP entity extraction & ESCO taxonomy grounder
│       │   ├── ats_scorer.md       # XGBoost predictive engine & C++ TreeSHAP
│       │   ├── tailor_agent.md     # STAR synthesizer & Typst resume compiler
│       │   ├── scout_agent.md      # Direct ATS scraper (Greenhouse, Lever, Workday)
│       │   ├── applicator_agent.md # Playwright browser automation & HITL air-gap
│       │   ├── voice_agent.md      # Real-time mock interview engine & FastAPI service
│       │   ├── orchestrator.md     # LangGraph multi-agent workflow controller
│       │   ├── main_cli.md         # CLI entrypoint and pipeline execution script
│       │   └── frontend_dashboard.md # Single-page reactive dashboard interface
│       └── 03_architecture_and_workflows.md # Structural diagrams, connectivity matrix & workflows
├── src/                            # Core backend production source code
│   ├── __init__.py                 # Package declaration and version export
│   ├── config.py                   # Centralized runtime configuration and settings
│   ├── schemas.py                  # Single source of truth for Pydantic models
│   ├── scout_agent.py              # Autonomous multi-platform job scraper
│   ├── skill_extractor.py          # NER entity extractor and vector similarity mapper
│   ├── ats_scorer.py               # Tabular ML scoring engine with TreeSHAP explainability
│   ├── tailor_agent.py             # Resume tailoring engine with metric conservation guardrails
│   ├── applicator_agent.py         # Browser automation with Human-in-the-Loop verification
│   ├── voice_agent.py              # Technical interview server with strict rubric scoring
│   └── orchestrator.py             # Multi-agent coordination state machine
├── frontend/                       # Client presentation layer
│   └── index.html                  # Responsive single-page application dashboard (135+ KB)
├── data/                           # Canonical test fixtures and datasets
│   ├── sample_resume.json          # Standardized candidate profile fixture
│   └── sample_job.json             # 12 real-world tech job opportunities across domains
├── tests/                          # Automated test suites
│   └── test_ats_scorer.py          # Pytest unit tests for predictive ATS scoring and SHAP
├── .env.example                    # Template for required environment variables and API keys
├── .gitignore                      # Git exclusion rules for environments, caches, and builds
├── main.py                         # Standalone executable Python pipeline script
├── run_server.py                   # Uvicorn launcher for the FastAPI backend service
├── run.bat                         # Windows batch script for automated startup
├── requirements.txt                # Pinned production Python dependencies
└── README.md                       # High-level repository orientation and quickstart guide
```
