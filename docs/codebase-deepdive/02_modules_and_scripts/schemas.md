# Module Deep-Dive: Canonical Schemas & Data Contracts (`src/schemas.py`)

## 1. Technical Concepts & Design Patterns

The `schemas.py` module defines the structural foundation and boundary contracts for all agents and modules in CareerPilot AI. Built upon **Pydantic v2**, it implements the **Contract-First Design Pattern** and **Data Transfer Object (DTO) Pattern**.

### Foundational Design Principles
1. **Contract-First Agent Isolation:** Rather than passing unstructured dictionaries or dynamic JSON objects between agents, all inter-agent communication must satisfy strict Pydantic schemas. This prevents schema drift between the scraping layer, the ML prediction engine, and the document synthesis engine.
2. **Immutable Historical Ground Truth vs. Mutable Projections:** 
   - A candidate's verified career history (`CandidateProfile`) is treated as immutable ground truth.
   - Tailored resumes (`TailoredResumePayload`) are generated projections representing specific target viewpoints without altering the original verified records.
3. **Tabular ML Interface Contract:** Machine Learning pipelines typically require dense multidimensional arrays. The `FeatureVector` schema bridges the gap between semantic domain models and low-level C++ arrays via its optimized `.to_numpy()` method.

---

## 2. Core Classes & Models

### 2.1 Candidate Domain Models
* **`EducationEntry(BaseModel)`**: Represents an accredited academic degree.
  * `institution` (`str`): Name of the granting university or college.
  * `degree` (`str`): Degree title (e.g. `"B.Tech Computer Science"`).
  * `degree_level` (`int`): Standardized ordinal ranking: `0`=High School, `1`=Associate, `2`=Bachelors, `3`=Masters, `4`=PhD.
  * `field_of_study` (`str`): Academic discipline or major.
  * `graduation_year` (`int`): Year of completion.
* **`WorkExperience(BaseModel)`**: Represents a discrete professional employment record.
  * `id` (`str`): Unique hash identifier.
  * `company` (`str`): Employer name.
  * `role` (`str`): Job title held.
  * `start_date` (`str`) & `end_date` (`str`): Period format (`"YYYY-MM"` or `"Present"`).
  * `responsibilities` (`List[str]`): Raw bullet points describing accomplishments.
  * `skills_used` (`List[str]`): Specific tools applied.
* **`CandidateProfile(BaseModel)`**: Canonical aggregate root of candidate data.
  * Fields: `candidate_id`, `full_name`, `email`, `phone`, `total_experience_years`, `seniority_level` (1=Junior to 5=Director), `education`, `experiences`, `verified_skills`, `raw_resume_text`.

### 2.2 Job Ingestion Domain Models
* **`ATSPlatform(str, Enum)`**: Enumeration of supported application portals (`greenhouse`, `lever`, `workday`, `linkedin`, `indeed`, `custom`).
* **`WorkplaceType(str, Enum)`**: Work arrangement classification (`remote`, `hybrid`, `onsite`).
* **`JobPosting(BaseModel)`**: Normalized representation of a scraped opportunity.
  * Fields: `id` (deterministic SHA-256 hash), `external_id`, `ats_platform`, `company_name`, `title`, `location`, `workplace_type`, `description_text`, `required_skills`, `required_experience_years`, `required_degree_level`, `required_seniority_level`, `apply_url`, `source_url`, `scraped_at`.

### 2.3 Machine Learning Feature & Explainability Contracts
* **`FeatureVector(BaseModel)`**: Encapsulates the 10-dimensional tabular representation evaluated by the XGBoost scoring model.
  * `cross_encoder_score` (`float`): Deep contextual alignment logit.
  * `bi_encoder_full_sim` (`float`): Cosine similarity between dense embedding vectors.
  * `hard_skill_jaccard` (`float`): Set overlap ratio: $\frac{|\text{CandSkills} \cap \text{JobSkills}|}{|\text{JobSkills}|}$.
  * `missing_mandatory_count` (`int`): Quantity of critical required skills not present.
  * `exp_delta_years` (`float`): Candidate years minus required years.
  * `is_min_exp_satisfied` (`float`): Binary indicator (`1.0` if candidate experience $\ge$ required experience).
  * `seniority_level_delta` (`float`): Numerical seniority gap.
  * `degree_level_delta` (`float`): Degree ordinal difference.
  * `degree_requirement_met` (`float`): Binary indicator (`1.0` if candidate degree $\ge$ job requirement).
  * `latest_job_title_sim` (`float`): Title token similarity proxy.
  * **Method `to_numpy() -> np.ndarray`**: Returns a 2D `float32` array of shape `(1, 10)` ready for direct ingestion by `xgb.DMatrix`.
  * **Class Method `feature_names() -> List[str]`**: Returns the canonical ordered list of feature names matching model training headers.
* **`FeatureImpact(BaseModel)`**: Represents a single feature's Shapley contribution.
  * Fields: `feature_name`, `feature_value`, `shap_impact`, `human_explanation`.
* **`ATSScoreReport(BaseModel)`**: Output of the predictive engine.
  * Fields: `candidate_id`, `job_id`, `match_percentage`, `decision_threshold`, `is_shortlist_recommended`, `base_population_score`, `positive_drivers`, `negative_risks`.

### 2.4 Resume Tailoring & Workflow State
* **`STARBullet(BaseModel)`**: Decomposed achievement into `situation_and_task`, `action`, `result`, and `final_bullet`.
* **`TailoredResumePayload(BaseModel)`**: Tailored projection featuring aligned skills and STAR experiences.
* **`AgentWorkflowState(BaseModel)`**: Canonical LangGraph workflow state container tracking pipeline progression across stages.

---

## 3. Concrete Example & Usage

```python
import numpy as np
from src.schemas import FeatureVector, ATSScoreReport, FeatureImpact

# 1. Instantiate the 10-dimensional feature vector
fv = FeatureVector(
    cross_encoder_score=2.45,
    bi_encoder_full_sim=0.88,
    hard_skill_jaccard=0.75,
    missing_mandatory_count=1,
    exp_delta_years=1.0,
    is_min_exp_satisfied=1.0,
    seniority_level_delta=0.0,
    degree_level_delta=0.0,
    degree_requirement_met=1.0,
    latest_job_title_sim=0.92
)

# 2. Convert to optimized NumPy array for inference
np_features = fv.to_numpy()
print(f"NumPy Shape: {np_features.shape}") # (1, 10)
print(f"NumPy Dtype: {np_features.dtype}") # float32

# 3. Construct a structured score report with TreeSHAP explainability drivers
report = ATSScoreReport(
    candidate_id="c_101",
    job_id="j_202",
    match_percentage=84.5,
    decision_threshold=70.0,
    is_shortlist_recommended=True,
    base_population_score=50.0,
    positive_drivers=[
        FeatureImpact(
            feature_name="hard_skill_jaccard",
            feature_value=0.75,
            shap_impact=0.312,
            human_explanation="Direct technical skill coverage matches 75% of requirements."
        )
    ],
    negative_risks=[
        FeatureImpact(
            feature_name="missing_mandatory_count",
            feature_value=1.0,
            shap_impact=-0.145,
            human_explanation="Candidate is missing 1 required core skill (Docker)."
        )
    ]
)

print(f"Recommendation: {'SHORTLIST' if report.is_shortlist_recommended else 'REJECT'}")
print(f"Top Positive Driver: {report.positive_drivers[0].human_explanation}")
```
