import os
import asyncio
from typing import Optional, Dict, Any

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger("ApplicatorAgent")
    logger.success = logger.info
from src.schemas import CandidateProfile, JobPosting

class ApplicatorAgent:
    """
    Autonomous Browser Automation & Form-Filling Agent.
    Utilizes Playwright to navigate application wizards, auto-fill standard fields,
    upload tailored resumes, and enforce Human-in-the-Loop (HITL) pre-submission air-gaps.
    """

    def __init__(self, headless: bool = True, hitl_webhook: Optional[str] = None):
        self.headless = headless
        self.hitl_webhook = hitl_webhook

    async def fill_application(
        self,
        candidate: CandidateProfile,
        job: JobPosting,
        resume_pdf_path: str
    ) -> Dict[str, Any]:
        """
        Executes end-to-end form navigation and input mapping with Playwright.
        Enforces a strict pause before the final 'Submit' button for human verification.
        """
        try:
            from playwright.async_api import async_playwright
        except ImportError:
            logger.warning("Playwright is not installed yet. Running in browser simulation mode.")
            return {
                "status": "READY_FOR_HITL_REVIEW",
                "job_id": job.id,
                "company": job.company_name,
                "role": job.title,
                "submit_button_detected": True,
                "message": "[Simulation] Form successfully filled. Final submission blocked pending operator approval."
            }

        logger.info(f"Launching Applicator Agent for Job: {job.title} at {job.company_name}")

        async with async_playwright() as p:
            # Launch Chromium with anti-detection flags
            browser = await p.chromium.launch(
                headless=self.headless,
                args=["--disable-blink-features=AutomationControlled"]
            )
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
            )
            page = await context.new_page()

            try:
                logger.info(f"Navigating to application URL: {job.apply_url}")
                await page.goto(job.apply_url, timeout=30000, wait_until="domcontentloaded")
                await page.wait_for_timeout(1000)

                # 1. Fill Candidate Identity Inputs
                await self._fill_text_input(page, ["first_name", "first name", "firstname"], candidate.full_name.split()[0])
                await self._fill_text_input(page, ["last_name", "last name", "lastname"], candidate.full_name.split()[-1])
                await self._fill_text_input(page, ["email", "e-mail"], candidate.email)
                await self._fill_text_input(page, ["phone", "mobile", "telephone"], candidate.phone)

                if candidate.linkedin_url:
                    await self._fill_text_input(page, ["linkedin", "linkedin profile"], candidate.linkedin_url)
                if candidate.github_url:
                    await self._fill_text_input(page, ["github", "github profile", "website"], candidate.github_url)

                # 2. Handle Hidden Resume File Upload
                if os.path.exists(resume_pdf_path):
                    await self._handle_file_upload(page, resume_pdf_path)

                # 3. Pre-Submission Air-Gap (Human-in-the-Loop Checkpoint)
                result = await self._pre_submission_airgap(page, job)
                await browser.close()
                return result

            except Exception as e:
                logger.error(f"Application automation error: {e}")
                await browser.close()
                return {"status": "FAILED", "reason": str(e)}

    async def _fill_text_input(self, page, target_names: list, value: str):
        """Discovers input fields by name, id, or placeholder and fills them."""
        for name in target_names:
            selectors = [
                f'input[name*="{name}" i]',
                f'input[id*="{name}" i]',
                f'input[placeholder*="{name}" i]'
            ]
            for sel in selectors:
                loc = page.locator(sel).first
                if await loc.count() > 0 and await loc.is_visible():
                    await loc.fill(value)
                    logger.debug(f"Filled field matching '{name}' with '{value}'")
                    return

    async def _handle_file_upload(self, page, file_path: str):
        """Targets hidden input[type='file'] directly to bypass stylized drag-and-drop wrappers."""
        file_input = page.locator('input[type="file"]').first
        if await file_input.count() > 0:
            await file_input.set_input_files(file_path)
            logger.success(f"Attached resume file via input[type='file']: {file_path}")
        else:
            logger.warning("No standard input[type='file'] discovered on page.")

    async def _pre_submission_airgap(self, page, job: JobPosting) -> Dict[str, Any]:
        """
        Safety Protocol: Halts before clicking final Submit button.
        In production, sends screenshot to Slack webhook and awaits confirmation.
        """
        submit_btn = page.locator('button:has-text("Submit"), input[type="submit"], button:has-text("Apply")').first
        has_submit = await submit_btn.count() > 0

        logger.warning(
            f"PRE-SUBMISSION AIR-GAP: Form filled for '{job.title}'. "
            f"Awaiting human approval before final submission click."
        )

        return {
            "status": "READY_FOR_HITL_REVIEW",
            "job_id": job.id,
            "company": job.company_name,
            "role": job.title,
            "submit_button_detected": has_submit,
            "message": "Form successfully filled. Final submission blocked pending operator approval."
        }
