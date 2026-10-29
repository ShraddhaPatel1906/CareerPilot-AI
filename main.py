import asyncio
import json
import os
import sys

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

try:
    from loguru import logger
except ImportError:
    import logging
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    logger = logging.getLogger("CareerPilot")
    logger.success = logger.info
from src.schemas import CandidateProfile, JobPosting
from src.orchestrator import CareerPilotOrchestrator

async def main():
    logger.info("Initializing CareerPilot AI Autonomous Execution Pipeline...")
    
    base_dir = os.path.dirname(os.path.abspath(__file__))

    # 1. Load Candidate Profile
    resume_path = os.path.join(base_dir, "data", "sample_resume.json")
    with open(resume_path, "r", encoding="utf-8") as f:
        candidate_data = json.load(f)
    candidate = CandidateProfile(**candidate_data)
    logger.success(f"Loaded Candidate: {candidate.full_name} ({candidate.total_experience_years} yrs exp)")

    # 2. Load Sample Scraped Jobs
    jobs_path = os.path.join(base_dir, "data", "sample_job.json")
    with open(jobs_path, "r", encoding="utf-8") as f:
        jobs_data = json.load(f)
    jobs = [JobPosting(**j) for j in jobs_data]
    logger.success(f"Loaded {len(jobs)} Target Job Postings for Evaluation.")

    # 3. Instantiate and Execute Orchestrator
    orchestrator = CareerPilotOrchestrator(match_threshold=70.0)
    results = await orchestrator.run_pipeline(candidate=candidate, sample_jobs=jobs)

    # 4. Print Pipeline Execution Summary
    print("\n" + "="*70)
    print("CAREERPILOT AI: PIPELINE EXECUTION SUMMARY")
    print("="*70)
    for res in results:
        status_tag = "[APPROVED & HITL READY]" if "READY" in res.get("status", "") else "[DISCARDED]"
        print(f"\nRole: {res['title']} at {res['company']}")
        print(f"Match Score: {res['score']}% {status_tag}")
        print(f"Status: {res['status']}")
        if "hitl_message" in res and res["hitl_message"]:
            print(f"Safety Gate: {res['hitl_message']}")
        if "tailored_summary" in res and res["tailored_summary"]:
            print(f"Generated Summary: {res['tailored_summary']}")
    print("="*70 + "\n")

if __name__ == "__main__":
    asyncio.run(main())
