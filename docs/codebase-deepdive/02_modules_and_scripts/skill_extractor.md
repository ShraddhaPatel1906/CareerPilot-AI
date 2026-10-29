# Module Deep-Dive: Skill & Entity Extractor (`src/skill_extractor.py`)

## 1. Technical Concepts & Design Patterns

The `skill_extractor.py` module handles natural language entity recognition and semantic taxonomy grounding. It extracts hard technical skills, experience requirements, and academic qualifications from unstructured text, mapping them into standardized representations.

### Key Architectural Concepts
1. **Deterministic Fast-Path vs. Dense Semantic Embedding:** Heavy transformer models (e.g. BERT/RoBERTa) incur notable latency (50–200 ms per text chunk) and GPU dependency. CareerPilot AI employs a **two-tier extraction strategy**:
   - **Tier 1 (Fast-Path Regex):** Evaluates compiled regular expression word-boundary anchors (`\b`) over a curated 35+ core tech ontology in under **0.5 ms**.
   - **Tier 2 (Vector Grounding):** When resolving non-standard mentions (e.g., *"k8s"*, *"Postgres"*, *"scikit"*), the module projects text into a high-dimensional vector space using `BAAI/bge-large-en-v1.5` and computes Cosine similarity against canonical taxonomy concepts.
2. **Canonical Taxonomy Grounding (Entity Linking):** Real-world job listings and resumes contain extreme typographical and lexical variance. By linking terms to standardized dictionaries (such as ESCO or O*NET), downstream matching operates on unified identifiers rather than brittle literal string comparisons.
3. **Ordinal Academic Hierarchy Mapping:** Maps qualitative degree strings into a continuous ordinal integer scale:
   $$0 = \text{None} < 1 = \text{Associate} < 2 = \text{Bachelors} < 3 = \text{Masters} < 4 = \text{PhD}$$
   This transformation enables mathematical subtraction in feature space ($\Delta_{\text{degree}} = \text{Candidate} - \text{Job}$).

---

## 2. Core Classes & Methods

### `SkillAndEntityExtractor`
* **Location:** `src/skill_extractor.py`
* **Purpose:** Multi-tier entity extraction and taxonomy normalization engine.

#### Methods & API

##### `__init__(use_gpu: bool = False)`
* **Inputs:** `use_gpu` (`bool`, default `False`).
* **Side Effects:** Triggers `_init_encoder()` which attempts to load `SentenceTransformer("BAAI/bge-large-en-v1.5")` from Hugging Face Hub using `settings.huggingface_api_key`. Falls back gracefully to regex mode if dependencies are unavailable.

##### `extract_skills_regex(text: str) -> List[str]`
* **Inputs:** `text` (`str`) — Raw unstructured job description or resume section.
* **Outputs:** `List[str]` — Alphabetically sorted list of detected canonical skill names (e.g. `["Fastapi", "Python", "Xgboost"]`).
* **Performance:** Executes in $<0.5\text{ ms}$ on standard modern CPUs.
* **Why it exists:** Provides instantaneous zero-cost skill detection without incurring neural network latency.

##### `extract_experience_years(text: str) -> float`
* **Inputs:** `text` (`str`) — Candidate or job description requirement text.
* **Outputs:** `float` — Extracted minimum numerical years of experience.
* **Parsing Mechanics:** Evaluates regex expressions capturing patterns such as `"5+ years"`, `"3-5 years"` (extracts lower bound `3.0`), and `"at least 2 years"`. Returns `0.0` if no explicit duration pattern matches.

##### `extract_degree_level(text: str) -> int`
* **Inputs:** `text` (`str`) — Educational requirement or candidate degree text.
* **Outputs:** `int` — Standardized ordinal level: `0` (None), `1` (Associate), `2` (Bachelors), `3` (Masters), `4` (PhD).
* **Why it exists:** Normalizes varied expressions (e.g. `"B.S."`, `"Bachelor of Engineering"`, `"B.Tech"`) into a single numerical index.

##### `ground_skill_to_esco(raw_mention: str, canonical_taxonomies: List[str]) -> Tuple[str, float]`
* **Inputs:** 
  * `raw_mention` (`str`) — Raw text mention (e.g. `"k8s"`).
  * `canonical_taxonomies` (`List[str]`) — Target vocabulary list (e.g. `["Kubernetes", "Docker", "Linux"]`).
* **Outputs:** `Tuple[str, float]` — Best matching canonical label and its Cosine similarity score.
* **Why it exists:** Resolves abbreviations, acronyms, and aliases to their authoritative canonical parent entities.

---

## 3. Concrete Example & Usage

```python
from src.skill_extractor import SkillAndEntityExtractor

extractor = SkillAndEntityExtractor()

sample_job_description = """
Senior Data Scientist - Machine Learning
Innovate Analytics Inc.
Requirements:
- 4+ years of professional experience building predictive models.
- Deep expertise in Python, PyTorch, Scikit-Learn, and Docker.
- Master's degree in Computer Science, Statistics, or related technical field.
- Familiarity with SQL and CI/CD pipelines.
"""

# 1. Deterministic Skill Extraction
skills = extractor.extract_skills_regex(sample_job_description)
print(f"Detected Skills: {skills}")
# Output: ['Ci/Cd', 'Docker', 'Pytorch', 'Python', 'Scikit-Learn', 'Sql']

# 2. Required Experience Extraction
required_years = extractor.extract_experience_years(sample_job_description)
print(f"Required Experience: {required_years} years")
# Output: 4.0 years

# 3. Degree Level Parsing
degree_tier = extractor.extract_degree_level(sample_job_description)
degree_names = {0: "None", 1: "Associate", 2: "Bachelors", 3: "Masters", 4: "PhD"}
print(f"Degree Requirement: Tier {degree_tier} ({degree_names[degree_tier]})")
# Output: Tier 3 (Masters)

# 4. Semantic Taxonomy Grounding
canonical_labels = ["Kubernetes", "Docker Containerization", "PostgreSQL", "Apache Kafka"]
best_match, score = extractor.ground_skill_to_esco("k8s orchestration", canonical_labels)
print(f"Semantic Grounding: 'k8s orchestration' -> '{best_match}' (Similarity: {score:.3f})")
```
