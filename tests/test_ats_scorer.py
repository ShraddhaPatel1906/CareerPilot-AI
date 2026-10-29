import pytest
from src.schemas import CandidateProfile, JobPosting, EducationEntry, WorkExperience
from src.ats_scorer import ATSPredictiveEngine

def test_ats_scorer_evaluation():
    engine = ATSPredictiveEngine()
    
    candidate = CandidateProfile(
        candidate_id="c_test",
        full_name="Test Candidate",
        email="test@example.com",
        phone="1234567890",
        total_experience_years=4.0,
        seniority_level=2,
        education=[
            EducationEntry(
                institution="State University",
                degree="B.Tech",
                degree_level=2,
                field_of_study="Computer Science",
                graduation_year=2021
            )
        ],
        experiences=[
            WorkExperience(
                id="e1",
                company="Tech Corp",
                role="Software Engineer",
                start_date="2021-01",
                end_date="Present",
                responsibilities=["Developed FastAPI microservices and XGBoost models."],
                skills_used=["Python", "FastAPI", "XGBoost"]
            )
        ],
        verified_skills=["Python", "FastAPI", "XGBoost", "Docker"],
        raw_resume_text="Software Engineer with Python, FastAPI, and XGBoost experience."
    )

    matching_job = JobPosting(
        id="j_match",
        external_id="101",
        ats_platform="greenhouse",
        company_name="Innovate Ltd",
        title="Python Engineer",
        location="Remote",
        description_text="Looking for a Python Engineer with FastAPI and XGBoost experience. 2+ years exp.",
        required_skills=["Python", "FastAPI", "XGBoost"],
        required_experience_years=2.0,
        required_degree_level=2,
        required_seniority_level=2,
        apply_url="https://example.com/apply",
        source_url="https://example.com/apply"
    )

    report = engine.evaluate_and_explain(candidate, matching_job, threshold=70.0)
    
    assert report.match_percentage > 50.0
    assert len(report.positive_drivers) > 0
    assert report.candidate_id == "c_test"
    assert report.job_id == "j_match"
