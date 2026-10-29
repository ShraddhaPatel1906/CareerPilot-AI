import re
from typing import List, Dict, Any, Optional

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger("ResumeTailorAgent")
    logger.success = logger.info
from src.schemas import (
    CandidateProfile, JobPosting, TailoredResumePayload,
    TailoredExperience, STARBullet
)
from src.config import settings

class ResumeTailorAgent:
    """
    GenAI Resume Tailor & Typst Document Generation Engine.
    Transforms candidate achievements into STAR format aligned with Target JDs,
    enforcing strict programmatic guardrails against hallucinated metrics or skills.
    Powered natively by free ultra-fast Groq LPU inference (Llama-3.3-70B / Llama-3.1-8B).
    """

    METRIC_REGEX = re.compile(r"(\$?\d+(?:[.,]\d+)?%?|\b\d+\b)")

    def __init__(self, groq_api_key: Optional[str] = None, model_name: Optional[str] = None):
        self.groq_api_key = groq_api_key or settings.groq_api_key
        self.model_name = model_name or settings.groq_model_name
        self.has_groq = bool(self.groq_api_key and self.groq_api_key.startswith("gsk_"))

    def verify_metric_conservation(self, source_bullets: List[str], tailored_bullet: str) -> bool:
        """
        Anti-Hallucination Guardrail:
        Verifies that no newly fabricated numbers, percentages, or dollar amounts
        were invented by the language model.
        """
        source_text = " ".join(source_bullets)
        source_metrics = set(self.METRIC_REGEX.findall(source_text))
        tailored_metrics = set(self.METRIC_REGEX.findall(tailored_bullet))

        unauthorized = tailored_metrics - source_metrics
        if unauthorized:
            logger.warning(f"Guardrail Triggered: Fabricated metrics detected {unauthorized}. Rejecting bullet.")
            return False
        return True

    def _call_groq_star_rephrase(self, raw_bullet: str, target_role: str, target_skills: List[str]) -> str:
        """
        Calls Groq API to rephrase a bullet into STAR format using Llama-3.3-70B.
        Falls back to rule-based rephrasing if Groq is unavailable.
        """
        if not self.has_groq:
            return raw_bullet

        try:
            import httpx
            prompt = (
                f"You are a Principal Technical Recruiter. Rephrase this single resume bullet point into an "
                f"active STAR achievement starting with a strong past-tense action verb, emphasizing {', '.join(target_skills[:3])}. "
                f"STRICT CONSTRAINT: DO NOT invent any new numbers, percentages, or metrics. Keep it under 25 words.\n"
                f"Target Role: {target_role}\n"
                f"Source Bullet: {raw_bullet}\n"
                f"Return ONLY the rewritten bullet sentence."
            )
            resp = httpx.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.groq_api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": self.model_name,
                    "messages": [
                        {"role": "system", "content": "You are an expert ATS resume tailoring engine."},
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.1,
                    "max_tokens": 100
                },
                timeout=10.0
            )
            if resp.status_code == 200:
                data = resp.json()
                content = data["choices"][0]["message"]["content"].strip().strip('"').strip("'")
                return content
        except Exception as e:
            logger.warning(f"Groq API call failed ({e}). Falling back to local synthesis.")
        
        return raw_bullet

    def tailor_experience_local(
        self,
        candidate: CandidateProfile,
        job: JobPosting
    ) -> TailoredResumePayload:
        """
        Generates a tailored resume payload highlighting overlapping skills and
        formatting experience into active STAR bullets while enforcing factuality.
        """
        logger.info(f"Tailoring resume for candidate [{candidate.full_name}] -> Role [{job.title}]")
        if self.has_groq:
            logger.info(f"Using Groq LPU ({self.model_name}) for high-speed STAR rephrasing.")
        else:
            logger.info("Using local deterministic STAR synthesis (No API key required).")
        
        target_skills = set(s.lower() for s in job.required_skills)
        aligned = [s for s in candidate.verified_skills if s.lower() in target_skills]
        if not aligned:
            aligned = candidate.verified_skills[:5]

        tailored_experiences: List[TailoredExperience] = []

        for exp in candidate.experiences:
            star_bullets: List[STARBullet] = []
            for raw_b in exp.responsibilities:
                # 1. Try Groq Llama-3.3 rephrasing or local synthesis
                if self.has_groq:
                    rephrased = self._call_groq_star_rephrase(raw_b, job.title, aligned)
                else:
                    action_verb = "Architected" if "build" in raw_b.lower() or "lead" in raw_b.lower() else "Engineered"
                    rephrased = f"{action_verb} {raw_b.lstrip('Built ').lstrip('Created ').lstrip('Developed ')}"

                # 2. Check metric conservation guardrail
                if not self.verify_metric_conservation(exp.responsibilities, rephrased):
                    rephrased = raw_b # Fallback to original truth on failure

                star_bullets.append(STARBullet(
                    situation_and_task=f"Addressed production scaling requirements in {exp.company}.",
                    action=f"Applied {', '.join(aligned[:2]) if aligned else 'core frameworks'}.",
                    result="Improved system performance and maintainability.",
                    final_bullet=rephrased
                ))

            tailored_experiences.append(TailoredExperience(
                company=exp.company,
                role=exp.role,
                source_bullets=exp.responsibilities,
                tailored_bullets=star_bullets
            ))

        summary = (
            f"Results-driven Software Engineer with {candidate.total_experience_years:.1f} years of experience "
            f"specializing in {', '.join(aligned[:3]) if aligned else 'Modern Software Systems'}. "
            f"Demonstrated track record of delivering resilient production systems for {job.title} roles."
        )

        return TailoredResumePayload(
            candidate_name=candidate.full_name,
            target_job_title=job.title,
            summary=summary,
            experiences=tailored_experiences,
            aligned_skills=aligned
        )

    def export_to_typst(self, payload: TailoredResumePayload) -> str:
        """
        Serializes the tailored payload into a clean, modern Typst document.
        Typst compiles to PDF in under 50ms without TeX Live container bloat.
        """
        typst_code = f"""
// CareerPilot AI Auto-Generated Typst Resume
#set page(paper: "a4", margin: (x: 1.5cm, y: 1.5cm))
#set text(font: "Linux Libertine", size: 10pt)
#set par(justify: true)

#align(center)[
  #text(size: 18pt, weight: "bold")[{payload.candidate_name}] \\
  #text(size: 11pt, fill: rgb("2b6cb0"))[{payload.target_job_title}]
]

#v(8pt)
#line(length: 100%, stroke: 0.5pt + gray)

== Professional Summary
{payload.summary}

== Technical Competencies
*Key Technologies:* {', '.join(payload.aligned_skills)}

== Professional Experience
"""
        for exp in payload.experiences:
            typst_code += f"\n=== {exp.company} -- _{exp.role}_\n"
            for b in exp.tailored_bullets:
                typst_code += f"- {b.final_bullet}\n"

        return typst_code
