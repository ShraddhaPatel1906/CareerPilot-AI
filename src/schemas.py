from datetime import datetime
from enum import Enum
from typing import List, Dict, Any, Optional
import numpy as np
from pydantic import BaseModel, Field, HttpUrl

# =====================================================================
# 1. Candidate & Resume Schemas
# =====================================================================

class EducationEntry(BaseModel):
    institution: str
    degree: str
    degree_level: int = Field(description="0=HighSchool, 1=Associate, 2=Bachelors, 3=Masters, 4=PhD")
    field_of_study: str
    graduation_year: int

class WorkExperience(BaseModel):
    id: str = Field(description="Unique identifier for experience chunk")
    company: str
    role: str
    start_date: str # YYYY-MM
    end_date: str   # YYYY-MM or 'Present'
    responsibilities: List[str]
    skills_used: List[str] = []

class CandidateProfile(BaseModel):
    candidate_id: str
    full_name: str
    email: str
    phone: str
    linkedin_url: Optional[str] = None
    github_url: Optional[str] = None
    total_experience_years: float
    seniority_level: int = Field(description="1=Junior, 2=Mid, 3=Senior, 4=Lead, 5=Director")
    education: List[EducationEntry]
    experiences: List[WorkExperience]
    verified_skills: List[str]
    raw_resume_text: str

# =====================================================================
# 2. Job Ingestion Schemas
# =====================================================================

class ATSPlatform(str, Enum):
    GREENHOUSE = "greenhouse"
    LEVER = "lever"
    WORKDAY = "workday"
    LINKEDIN = "linkedin"
    INDEED = "indeed"
    GOOGLE = "google_careers"
    MICROSOFT = "microsoft_careers"
    AMAZON = "amazon_jobs"
    CUSTOM = "custom"

class WorkplaceType(str, Enum):
    REMOTE = "remote"
    HYBRID = "hybrid"
    ONSITE = "onsite"

class Compensation(BaseModel):
    currency: str = "USD"
    min_amount: Optional[float] = None
    max_amount: Optional[float] = None
    interval: str = "yearly"

class JobPosting(BaseModel):
    id: str = Field(description="Unique hash of company + external_id")
    external_id: str
    ats_platform: ATSPlatform
    company_name: str
    title: str
    location: str
    workplace_type: WorkplaceType = WorkplaceType.ONSITE
    description_text: str
    required_skills: List[str] = []
    required_experience_years: float = 0.0
    required_degree_level: int = 2 # Default: Bachelors
    required_seniority_level: int = 2 # Default: Mid
    apply_url: str
    source_url: str = ""
    scraped_at: datetime = Field(default_factory=datetime.now)

# =====================================================================
# 3. Machine Learning & ATS Scoring Schemas
# =====================================================================

class FeatureVector(BaseModel):
    cross_encoder_score: float = Field(description="Logit output from cross-encoder")
    bi_encoder_full_sim: float = Field(description="Cosine similarity of dense full embeddings")
    hard_skill_jaccard: float = Field(description="|CandidateSkills ∩ JobSkills| / |JobSkills|")
    missing_mandatory_count: int = Field(description="Count of mandatory skills absent")
    exp_delta_years: float = Field(description="Candidate experience minus required experience")
    is_min_exp_satisfied: float = Field(description="1.0 if exp_delta >= 0 else 0.0")
    seniority_level_delta: float = Field(description="Candidate seniority minus job seniority")
    degree_level_delta: float = Field(description="Candidate degree level minus required degree level")
    degree_requirement_met: float = Field(description="1.0 if degree_level_delta >= 0 else 0.0")
    latest_job_title_sim: float = Field(description="Cosine similarity between latest title and job title")

    def to_numpy(self) -> np.ndarray:
        return np.array([[
            self.cross_encoder_score,
            self.bi_encoder_full_sim,
            self.hard_skill_jaccard,
            float(self.missing_mandatory_count),
            self.exp_delta_years,
            self.is_min_exp_satisfied,
            self.seniority_level_delta,
            self.degree_level_delta,
            self.degree_requirement_met,
            self.latest_job_title_sim
        ]], dtype=np.float32)

    @classmethod
    def feature_names(cls) -> List[str]:
        return [
            "cross_encoder_score",
            "bi_encoder_full_sim",
            "hard_skill_jaccard",
            "missing_mandatory_count",
            "exp_delta_years",
            "is_min_exp_satisfied",
            "seniority_level_delta",
            "degree_level_delta",
            "degree_requirement_met",
            "latest_job_title_sim"
        ]

class FeatureImpact(BaseModel):
    feature_name: str
    feature_value: float
    shap_impact: float
    human_explanation: str

class ATSScoreReport(BaseModel):
    candidate_id: str
    job_id: str
    match_percentage: float
    decision_threshold: float
    is_shortlist_recommended: bool
    base_population_score: float
    positive_drivers: List[FeatureImpact]
    negative_risks: List[FeatureImpact]

# =====================================================================
# 4. Resume Tailoring & STAR Schemas
# =====================================================================

class STARBullet(BaseModel):
    situation_and_task: str
    action: str
    result: str
    final_bullet: str

class TailoredExperience(BaseModel):
    company: str
    role: str
    source_bullets: List[str]
    tailored_bullets: List[STARBullet]

class TailoredResumePayload(BaseModel):
    candidate_name: str
    target_job_title: str
    summary: str
    experiences: List[TailoredExperience]
    aligned_skills: List[str]

# =====================================================================
# 5. LangGraph Agent State
# =====================================================================

class AgentWorkflowState(BaseModel):
    candidate: CandidateProfile
    scouted_jobs: List[JobPosting] = []
    current_job: Optional[JobPosting] = None
    feature_vector: Optional[FeatureVector] = None
    ats_report: Optional[ATSScoreReport] = None
    tailored_resume: Optional[TailoredResumePayload] = None
    application_status: str = "IDLE" # IDLE, EVALUATING, TAILORING, READY_FOR_HITL, SUBMITTED, REJECTED
    error_message: Optional[str] = None
