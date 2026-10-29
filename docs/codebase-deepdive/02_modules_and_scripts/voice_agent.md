# Module Deep-Dive: Real-Time Voice Interview Agent & Service (`src/voice_agent.py`)

## 1. Technical Concepts & Design Patterns

The `voice_agent.py` module delivers real-time conversational mock technical interviews and hosts the FastAPI backend microservice for CareerPilot AI.

### Key Architectural Concepts

#### 1. Sub-500ms Real-Time Voice Pipeline
Traditional speech-to-speech AI architectures suffer from severe multi-second latency spikes (1.5s ASR + 2.0s LLM + 1.5s TTS = 5.0 seconds). A conversation with 5-second pauses feels unnatural.
The voice agent design utilizes a pipelined cascade:
* **Voice Activity Detection (VAD):** **Silero VAD (ONNX)** identifies speech boundaries with $<10\text{ ms}$ processing latency.
* **Low-Latency Speech-to-Text (ASR):** **`faster-whisper`** with CTranslate2 INT8 quantization transcribes candidate speech in $<180\text{ ms}$.
* **Ultra-Fast LLM Reasoning:** **Groq LPU** (Llama-3.3-70B) streams reasoning tokens at 300+ tokens/sec (time-to-first-token $<150\text{ ms}$).
* **Streaming Text-to-Speech (TTS):** **Cartesia Sonic** generates natural conversational speech audio in $<100\text{ ms}$.
* **Total Turnaround Time:** $\sim 440\text{ ms}$, delivering real-time conversational flow.

#### 2. Strict Rubric Scoring (Anti-Inflation & Refusal Detection)
Unlike generic AI interview tools that award superficial scores regardless of answer validity, CareerPilot AI implements an uncompromising evaluation standard:
* **Refusal & Gibberish Detection:** Short answers ($<4$ words) or phrases indicating lack of knowledge (*"don't know"*, *"no idea"*, *"can't answer"*, *"skip"*, *"asdf"*) are awarded **$0/5$ across accuracy and depth**, resulting in an explicit **`0.0%` score**.
* **Concept Match Gating:** Identifies mandatory technical terms. Answers lacking core engineering keywords are capped at partial or off-topic ratings.
* **Locked Model Answers:** Staff-level reference answers remain locked in the DOM until the candidate submits their response, preventing premature answer leakage.

---

## 2. Core Classes, Methods & REST Endpoints

### 2.1 Domain Schemas
* **`RubricScore(BaseModel)`**: Numerical criterion score (0 to 5), strengths, critique points, and model answer summary.
* **`InterviewEvaluationReport(BaseModel)`**: Aggregate evaluation report containing overall score percentage, recommendation (`"Strong Hire"`, `"Hire"`, `"Needs Practice"`, `"Incorrect / Wrong Answer"`), and sub-scores for Technical Accuracy, Architectural Depth & Trade-offs, and Communication Clarity.
* **`EvaluateRequest(BaseModel)`**: REST request payload encapsulating `question_id`, `candidate_answer`, and `role`.

### 2.2 `VoiceInterviewEngine`
* **Location:** `src/voice_agent.py`
* **Purpose:** Manages question banks and deterministic rubric evaluations.

#### Methods & API

##### `get_questions_for_role(role: str) -> List[Dict[str, Any]]`
* **Inputs:** `role` (`str`) — Target job title (e.g. `"Data Scientist"`, `"AI/ML Engineer"`).
* **Outputs:** 15-question structured question bank organized into 5 progressive stages.

##### `evaluate_answer_local(question_id: str, candidate_answer: str, role: str = "Data Scientist") -> InterviewEvaluationReport`
* **Inputs:** Question identifier, candidate transcript, and target role.
* **Outputs:** `InterviewEvaluationReport` with scored criteria and feedback.
* **Scoring Rules:**
  * Refusal / Gibberish / Empty: `0/5` Accuracy, `0/5` Depth $\implies$ `0%` score (`Incorrect / Wrong Answer`).
  * Off-topic ($>15$ words but zero key concepts): `1/5` Accuracy $\implies$ `26.7%` score.
  * Partial (1–2 key concepts): `2/5` Accuracy $\implies$ `46.7%` score (`Partially Accurate`).
  * Strong (3–4 key concepts): `4/5` Accuracy $\implies$ `80.0%` score (`Strong Technical Answer`).
  * Staff-Level ($\ge 5$ concepts + depth): `5/5` Accuracy $\implies$ `100.0%` score (`Staff-Level Mastery`).

---

### 2.3 REST Endpoints & WebSockets

| Route | Protocol & Method | Summary | Purpose |
| :--- | :--- | :--- | :--- |
| `/` | `GET` (HTTP) | Web Dashboard | Serves the interactive `frontend/index.html` application. |
| `/api/health` | `GET` (HTTP) | Health Status | Verifies API key and provider configurations (Groq, Hugging Face). |
| `/api/candidate` | `GET` (HTTP) | Candidate Record | Serves the active candidate JSON profile. |
| `/api/jobs` | `GET` (HTTP) | Job Openings | Returns 12+ live scouted job listings with recency badges. |
| `/api/interview/questions` | `GET` (HTTP) | Question Bank | Fetches structured interview questions for a specified role. |
| `/api/interview/evaluate` | `POST` (HTTP) | Rubric Evaluator | Evaluates a submitted candidate answer against strict rubrics. |
| `/api/resume/parse` | `POST` (HTTP) | Fast Resume Parser | Extracts skills, experience, and degree level from raw text. |
| `/ws/mock-interview` | `WebSocket` | Live Voice Session | Bidirectional event stream for prompts and evaluations. |

---

## 3. Concrete Example & Usage

```python
from src.voice_agent import VoiceInterviewEngine

# 1. Evaluate a Staff-Level Technical Answer
sample_answer = """
To prevent data leakage in predictive pipelines, I encapsulate all preprocessing
(imputation, standard scaling, and one-hot encoding) inside Scikit-Learn Pipelines.
The pipeline fits strictly on training folds and only transforms validation/test folds.
For temporal datasets, I enforce strict chronological time-series splits rather than
random cross-validation shuffling to ensure no future information leaks into the past.
"""

report = VoiceInterviewEngine.evaluate_answer_local(
    question_id="ds_q5",
    candidate_answer=sample_answer,
    role="Data Scientist"
)

print(f"Overall Score: {report.overall_score_percentage}%")
print(f"Recommendation: {report.recommendation}")
print(f"Technical Accuracy: {report.technical_accuracy.score}/5")
print(f"Strengths: {report.technical_accuracy.strengths}")

# 2. Evaluate an Incorrect / Refusal Answer (Anti-Inflation Verification)
refusal_answer = "I don't know, can you ask me another question?"
refusal_report = VoiceInterviewEngine.evaluate_answer_local(
    question_id="ds_q5",
    candidate_answer=refusal_answer,
    role="Data Scientist"
)

print(f"\nRefusal Score: {refusal_report.overall_score_percentage}%")
print(f"Refusal Recommendation: {refusal_report.recommendation}")
print(f"Is Correct? {refusal_report.is_correct}")
# Output: Score: 0.0% | Recommendation: ❌ INCORRECT / WRONG ANSWER (0%) | Is Correct: False
```
