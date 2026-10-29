import asyncio
from typing import Dict, Any, List

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger("Orchestrator")
    logger.success = logger.info
from src.schemas import (
    CandidateProfile, JobPosting, AgentWorkflowState,
    ATSScoreReport, FeatureVector
)
from src.scout_agent import ScoutAgent
from src.ats_scorer import ATSPredictiveEngine
from src.tailor_agent import ResumeTailorAgent
from src.applicator_agent import ApplicatorAgent

class CareerPilotOrchestrator:
    """
    Multi-Agent LangGraph Workflow Orchestrator for CareerPilot AI.
    Coordinates the cyclic progression:
    Scout -> Evaluate (XGBoost) -> Conditional Gate (>=70%?) -> Tailor (STAR) -> Applicator (HITL).
    """

    def __init__(self, match_threshold: float = 70.0):
        self.match_threshold = match_threshold
        self.scout = ScoutAgent()
        self.scorer = ATSPredictiveEngine()
        self.tailor = ResumeTailorAgent()
        self.applicator = ApplicatorAgent(headless=True)

    async def run_pipeline(
        self,
        candidate: CandidateProfile,
        sample_jobs: List[JobPosting]
    ) -> List[Dict[str, Any]]:
        """
        Executes the autonomous career pipeline across the candidate and a batch of scouted jobs.
        """
        logger.info(f"Starting CareerPilot AI pipeline for: {candidate.full_name}")
        pipeline_results = []

        for job in sample_jobs:
            logger.info(f"\n--- Processing Job: {job.title} at {job.company_name} ---")
            
            # Step 1: Evaluate Match via XGBoost & TreeSHAP
            report: ATSScoreReport = self.scorer.evaluate_and_explain(
                candidate=candidate,
                job=job,
                threshold=self.match_threshold
            )
            
            logger.info(f"ATS Match Score: {report.match_percentage}% (Threshold: {self.match_threshold}%)")
            for driver in report.positive_drivers:
                logger.info(f"  [+] Strength: {driver.human_explanation} (Impact: {driver.shap_impact:+.2f})")
            for risk in report.negative_risks:
                logger.warning(f"  [-] Gap: {driver.human_explanation} (Impact: {risk.shap_impact:+.2f})")

            # Step 2: Conditional Gate
            if not report.is_shortlist_recommended:
                logger.warning(f"Discarding job '{job.title}': Score below threshold. No tokens wasted.")
                pipeline_results.append({
                    "job_id": job.id,
                    "title": job.title,
                    "company": job.company_name,
                    "score": report.match_percentage,
                    "status": "DISCARDED_BELOW_THRESHOLD"
                })
                continue

            # Step 3: GenAI Tailoring & STAR Synthesis
            logger.info("Match passed threshold! Generating tailored STAR resume...")
            tailored_payload = self.tailor.tailor_experience_local(candidate, job)
            typst_doc = self.tailor.export_to_typst(tailored_payload)
            
            # Step 4: Autonomous Applicator with HITL Air-Gap
            logger.info("Executing browser applicator with Pre-Submission Air-Gap...")
            application_result = await self.applicator.fill_application(
                candidate=candidate,
                job=job,
                resume_pdf_path="sample_resume.pdf" # Mock path
            )

            pipeline_results.append({
                "job_id": job.id,
                "title": job.title,
                "company": job.company_name,
                "score": report.match_percentage,
                "status": application_result.get("status"),
                "hitl_message": application_result.get("message"),
                "tailored_summary": tailored_payload.summary
            })

        logger.success(f"Pipeline completed. Processed {len(sample_jobs)} jobs.")
        return pipeline_results
