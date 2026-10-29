import os
import json
from typing import Dict, Any, List, Optional
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query, UploadFile, File, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from pydantic import BaseModel, Field

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger("VoiceAgent")
    logger.success = logger.info

from src.config import settings
from src.interview_service import extract_file_text, parse_resume, build_interview_plan, evaluate_answer
from src.live_jobs import load_public_jobs, query_jobs

app = FastAPI(title="CareerPilot AI: Technical Mock Interview & Autonomous Career Co-Pilot")

class RubricScore(BaseModel):
    criterion: str
    score: int = Field(ge=0, le=5, description="0 to 5 numerical rating")
    strengths: str
    critique_and_missing_points: str
    model_answer_summary: str

class InterviewEvaluationReport(BaseModel):
    role_evaluated: str
    question_id: str
    overall_score_percentage: float
    recommendation: str  # Strong Hire, Hire, Needs Practice, Incorrect / Wrong Answer
    is_correct: bool
    technical_accuracy: RubricScore
    system_depth_and_tradeoffs: RubricScore
    communication_clarity: RubricScore

class EvaluateRequest(BaseModel):
    question_id: str
    candidate_answer: str
    role: Optional[str] = "Data Scientist"

class VoiceInterviewEngine:
    """
    Comprehensive 30-50 Minute Technical Interview Engine.
    Dynamically generates and assesses 15+ structured technical questions categorized across:
    1. Candidate Introduction & Career Trajectory
    2. Deep-Dive into Candidate's Specific Resume Projects & Past Achievements
    3. Core Technical Competency & Library Mastery (Python, Pandas, SQL, Scikit-Learn)
    4. System Architecture, Scalability & Model Serving (FastAPI, Docker, Latency)
    5. High-Impact Behavioral & Scenario Problem-Solving
    """

    ROLE_QUESTION_BANKS = {
        "data_science": [
            # Stage 1: Candidate Introduction & Career Trajectory
            {
                "id": "ds_q1",
                "stage": "Stage 1: Candidate Introduction",
                "category": "Career Overview & Technical Trajectory",
                "question": "Could you please introduce yourself, walk me through your background in Data Science and Machine Learning, and highlight what motivated you to pursue this career path?",
                "key_concepts": ["background", "data science", "machine learning", "python", "projects", "passion", "education", "analytics", "experience", "iiit"],
                "model_answer": "Structure your answer in 3 parts: 1) Educational foundation in M.Sc Data Science at IIIT Lucknow; 2) Hands-on experience developing multi-agent systems and RAG knowledge assistants; 3) Core strengths in GenAI, LangGraph, and full-stack AI deployment."
            },
            {
                "id": "ds_q2",
                "stage": "Stage 1: Candidate Introduction",
                "category": "Engineering Workflow & Problem Formulation",
                "question": "When designing an end-to-end multi-agent or predictive solution, what is your standard engineering workflow from data curation and vector indexing to agent orchestration and production deployment?",
                "key_concepts": ["problem formulation", "kpi", "eda", "data cleaning", "vector indexing", "baseline", "orchestration", "validation", "monitoring"],
                "model_answer": "1) Define clear business KPIs and domain constraints; 2) Curate and chunk source documents with overlap; 3) Index into vector stores (ChromaDB); 4) Orchestrate specialized agents using LangGraph with cyclic validation; 5) Validate outputs against ground truth before containerized deployment."
            },
            # Stage 2: Resume Project Deep-Dive
            {
                "id": "ds_q3",
                "stage": "Stage 2: Resume Project Deep-Dive",
                "category": "KhetiLens AI – Multi-Agent Smart Farming Platform",
                "question": "Looking at your resume, you built 'KhetiLens AI', a multi-agent agricultural decision platform using LangGraph, LangChain, Groq, and FastAPI. Can you explain your multi-agent architecture: how do the specialized agents coordinate for crop and fertilizer guidance, and how did you manage state persistence?",
                "key_concepts": ["khetilens", "langgraph", "langchain", "multi-agent", "groq", "fastapi", "redis", "postgresql", "state", "orchestration"],
                "model_answer": "Detail your multi-agent StateGraph architecture: specialized sub-agents (crop advisor, fertilizer recommender, market analyst) coordinate through a shared state dictionary. State persistence is managed in Redis and PostgreSQL, while Groq accelerates LLM tool-calling inference with sub-second latency."
            },
            {
                "id": "ds_q4",
                "stage": "Stage 2: Resume Project Deep-Dive",
                "category": "Multi-Source AI Knowledge Assistant (RAG Pipeline)",
                "question": "In your 'Multi-Source AI Knowledge Assistant', you built a RAG pipeline retrieving from PDF, DOCX, TXT, and YouTube sources into ChromaDB. How did you design your document chunking and Hugging Face embedding strategy to prevent lost context across diverse formats?",
                "key_concepts": ["rag", "chromadb", "embeddings", "chunking", "hugging face", "groq", "llama", "streamlit", "semantic retrieval"],
                "model_answer": "Explain using recursive character text splitters with 15% token overlap, generating dense vector embeddings via Hugging Face models, indexing into ChromaDB collections, and passing retrieved top-k chunks into Groq LLaMA 3.3 for grounded, hallucination-free Q&A."
            },
            {
                "id": "ds_q5",
                "stage": "Stage 2: Resume Project Deep-Dive",
                "category": "Atlas Intelligence – Multi-Agent Decision Platform",
                "question": "In 'Atlas Intelligence', you implemented Human-in-the-Loop (HITL) workflows and task tracing in LangGraph. How did you architect the state machine to safely interrupt agent execution for human approval before executing high-risk actions?",
                "key_concepts": ["atlas", "hitl", "human-in-the-loop", "langgraph", "stategraph", "interrupt", "checkpoint", "task tracing", "fastapi"],
                "model_answer": "Configure interrupt_before or interrupt_after directives on high-risk decision nodes in LangGraph. State is checkpointed to persistent storage, exposing approval endpoints in FastAPI where human feedback is injected before resuming graph execution."
            },
            {
                "id": "ds_q6",
                "stage": "Stage 2: Resume Project Deep-Dive",
                "category": "RAG Evaluation & Hallucination Mitigation",
                "question": "How do you systematically benchmark your RAG pipelines and multi-agent systems for faithfulness, answer relevancy, and context recall, and how do you prevent LLM hallucinations?",
                "key_concepts": ["faithfulness", "relevancy", "context recall", "ragas", "evals", "hallucination", "guardrails", "grounding"],
                "model_answer": "Evaluate with Ragas or TruLens metrics (context precision, context recall, faithfulness). Enforce system prompt guardrails requiring citations strictly from retrieved contexts, and reject queries with low semantic similarity scores."
            },
            # Stage 3: Core Technical Competency & Tooling
            {
                "id": "ds_q7",
                "stage": "Stage 3: Core Technical Competency",
                "category": "LangGraph Cyclic State vs Linear Chains",
                "question": "What fundamental architectural advantages does LangGraph provide over traditional linear LangChain chains, and how do checkpointers enable state rollbacks?",
                "key_concepts": ["langgraph", "cyclic", "stategraph", "checkpoint", "rollback", "linear", "dag", "typeddict", "pydantic"],
                "model_answer": "LangGraph supports cyclic execution graphs necessary for agentic loops, self-correction, and reflection, whereas standard chains are strictly acyclic DAGs. Checkpointers save execution snapshots per turn, enabling seamless time-travel debugging and rollback."
            },
            {
                "id": "ds_q8",
                "stage": "Stage 3: Core Technical Competency",
                "category": "LoRA & QLoRA Parameter-Efficient Fine-Tuning",
                "question": "In your resume, you highlighted LoRA and QLoRA. How does Low-Rank Adaptation (LoRA) decompose weight updates, and how does 4-bit NormalFloat (NF4) quantization enable training large models on consumer GPUs?",
                "key_concepts": ["lora", "qlora", "low-rank", "decomposition", "nf4", "quantization", "bitsandbytes", "vram", "adapter"],
                "model_answer": "LoRA freezes pre-trained weights W and injects trainable low-rank matrices A and B (delta W = B * A, rank r << d), reducing trainable parameters by 99%+. QLoRA quantizes the base model to 4-bit NF4 with double quantization and paged optimizers, drastically reducing VRAM footprint."
            },
            {
                "id": "ds_q9",
                "stage": "Stage 3: Core Technical Competency",
                "category": "Vector Databases & Hybrid Search",
                "question": "When querying vector stores like ChromaDB or FAISS, what are the trade-offs between exact nearest neighbors (Flat) vs approximate indexing (HNSW / IVF), and how does hybrid BM25 search improve retrieval?",
                "key_concepts": ["hnsw", "ivf", "chromadb", "faiss", "approximate", "bm25", "hybrid search", "cosine similarity", "recall"],
                "model_answer": "Flat index calculates exact L2/cosine distances with O(N) complexity; HNSW creates multi-layer geometric graphs providing sub-linear approximate nearest neighbor search at high recall. Hybrid search combines HNSW dense embeddings with BM25 keyword matching for both semantic and exact keyword coverage."
            },
            {
                "id": "ds_q10",
                "stage": "Stage 3: Core Technical Competency",
                "category": "Advanced SQL: Window Functions",
                "question": "In SQL, what is the exact difference between RANK(), DENSE_RANK(), and ROW_NUMBER(), and how would you use them with PARTITION BY to find the top 2 purchases per customer?",
                "key_concepts": ["rank", "dense_rank", "row_number", "partition by", "order by", "ties", "gaps", "window function", "cte"],
                "model_answer": "ROW_NUMBER assigns distinct sequential integers regardless of ties. RANK assigns equal numbers to ties and skips subsequent ranks (e.g. 1, 2, 2, 4). DENSE_RANK assigns equal numbers to ties without skipping (e.g. 1, 2, 2, 3). Use: WITH Ranked AS (SELECT *, DENSE_RANK() OVER (PARTITION BY customer_id ORDER BY amount DESC) as rk FROM orders) SELECT * FROM Ranked WHERE rk <= 2;"
            },
            # Stage 4: Architecture, Latency & Model Serving
            {
                "id": "ds_q11",
                "stage": "Stage 4: Architecture & Serving",
                "category": "Real-Time Model Serving & FastAPI",
                "question": "How would you package a trained Scikit-Learn or XGBoost model into an asynchronous FastAPI microservice containerized with Docker for real-time sub-50ms inference?",
                "key_concepts": ["fastapi", "docker", "pydantic", "async", "uvicorn", "joblib", "onnx", "latency", "health check", "serialization"],
                "model_answer": "Serialize the model using joblib or ONNX. Load the artifact once during FastAPI startup lifespans. Define strictly typed request/response schemas with Pydantic. Containerize with a slim multi-stage Python Docker image and deploy behind Uvicorn workers."
            },
            {
                "id": "ds_q12",
                "stage": "Stage 4: Architecture & Serving",
                "category": "CI/CD & Version Control for ML",
                "question": "How do you use Git branching, code reviews, and CI/CD pipelines to ensure reproducible ML code and prevent broken production models?",
                "key_concepts": ["git", "branching", "pull request", "ci/cd", "pytest", "unit test", "linting", "reproducibility", "github actions"],
                "model_answer": "Use feature-branch workflows with branch protection on main. Automate unit tests (pytest for preprocessing functions), static analysis (flake8/black), and integration tests via GitHub Actions. Track model artifacts and dataset hashes with DVC or MLflow."
            },
            {
                "id": "ds_q13",
                "stage": "Stage 4: Architecture & Serving",
                "category": "Tree Ensembles vs Deep Learning Trade-offs",
                "question": "When working with tabular business datasets, under what conditions would you choose an ensemble like XGBoost/LightGBM over Deep Neural Networks, and vice versa?",
                "key_concepts": ["tabular", "xgboost", "lightgbm", "neural network", "deep learning", "unstructured", "interpretability", "training time", "hyperparameter"],
                "model_answer": "Tree ensembles consistently outperform deep learning on tabular data with heterogeneous numerical/categorical features, requiring less tuning, no feature scaling, and providing sub-millisecond inference and SHAP explainability. Neural networks excel when fusing tabular data with text embeddings, images, or audio."
            },
            # Stage 5: High-Impact Behavioral & Scenario Wrap-up
            {
                "id": "ds_q14",
                "stage": "Stage 5: Scenario & Communication",
                "category": "Stakeholder Alignment & Expectation Management",
                "question": "Describe a scenario where a non-technical product manager requested 99% accuracy on an unfeasible prediction task. How did you explain the trade-offs and align on practical business metrics?",
                "key_concepts": ["stakeholder", "trade-off", "communication", "precision-recall", "cost-benefit", "false positive", "business impact", "expectation"],
                "model_answer": "Translate technical concepts into economic trade-offs: explain that pushing accuracy arbitrarily high incurs extreme false-positive costs. Use confusion matrix cost-benefit analysis to demonstrate how a model with 85% precision and 80% recall maximizes net revenue."
            },
            {
                "id": "ds_q15",
                "stage": "Stage 5: Scenario & Communication",
                "category": "Candidate Inquiries & Technical Culture",
                "question": "To wrap up our technical interview: what questions do you have for our engineering team regarding our ML infrastructure, data pipelines, or modeling culture?",
                "key_concepts": ["infrastructure", "mlops", "deployment", "data pipeline", "culture", "collaboration", "architecture", "tooling"],
                "model_answer": "Ask high-signal engineering questions: 1) What does your deployment lifecycle look like from Jupyter notebook prototype to production service? 2) How do you handle feature store synchronization and offline/online feature parity? 3) What are the team's key MLOps priorities for the next quarter?"
            }
        ]
    }

    @classmethod
    def get_questions_for_role(cls, role: str) -> List[Dict[str, Any]]:
        return cls.ROLE_QUESTION_BANKS["data_science"]

    @classmethod
    def evaluate_answer_local(cls, question_id: str, candidate_answer: str, role: str = "Data Scientist") -> InterviewEvaluationReport:
        lower = candidate_answer.lower().strip()
        words = lower.split()
        word_count = len(words)
        
        # Locate target question
        target = None
        for q in cls.ROLE_QUESTION_BANKS["data_science"]:
            if q["id"] == question_id:
                target = q
                break
        
        if not target:
            target = cls.ROLE_QUESTION_BANKS["data_science"][0]

        # Explicit detection of non-answers, gibberish, or invalid responses
        negative_signals = [
            "don't know", "dont know", "no idea", "not sure", "cant answer", "can't answer",
            "wrong", "ask me question", "you can ask", "skip", "pass", "nothing", "asdf",
            "test", "qwerty", "hello", "hi"
        ]
        
        is_explicitly_empty_or_refusal = (
            word_count < 4 or 
            any(sig in lower for sig in negative_signals and word_count < 10)
        )

        # Match concepts
        matched_concepts = []
        for concept in target["key_concepts"]:
            if concept in lower:
                matched_concepts.append(concept)

        concept_count = len(matched_concepts)

        # STRICT SCORING: No free points!
        if is_explicitly_empty_or_refusal or (concept_count == 0 and word_count < 15):
            # INCORRECT / WRONG ANSWER
            accuracy_score = 0
            depth_score = 0
            clarity_score = 0 if word_count < 4 else 1
            overall_pct = 0.0
            recommendation = "❌ INCORRECT / WRONG ANSWER"
            is_correct = False
            strengths_msg = "No valid technical explanation or concepts identified."
            critique_msg = f"Your answer is incorrect or off-topic. A correct technical answer for this question must address: {', '.join(target['key_concepts'][:4])}."
        elif concept_count == 0 and word_count >= 15:
            # VAGUE / OFF-TOPIC ANSWER
            accuracy_score = 1
            depth_score = 1
            clarity_score = 2
            overall_pct = 26.7
            recommendation = "❌ INCORRECT (OFF-TOPIC)"
            is_correct = False
            strengths_msg = f"Provided fluent phrasing ({word_count} words), but missed core concepts."
            critique_msg = f"Missing core technical terminology: {', '.join(target['key_concepts'][:4])}."
        elif concept_count >= 1 and concept_count <= 2:
            # PARTIALLY ACCURATE
            accuracy_score = 2
            depth_score = 2
            clarity_score = 3
            overall_pct = 46.7
            recommendation = "⚠️ PARTIALLY ACCURATE"
            is_correct = True
            strengths_msg = f"Mentioned foundational concepts: {', '.join(matched_concepts)}."
            missing = [c for c in target['key_concepts'] if c not in matched_concepts]
            critique_msg = f"To reach Senior-level depth, also explain: {', '.join(missing[:3])}."
        elif concept_count >= 3 and concept_count <= 4:
            # GOOD HIRE
            accuracy_score = 4
            depth_score = 4
            clarity_score = 4
            overall_pct = 80.0
            recommendation = "✅ STRONG TECHNICAL ANSWER"
            is_correct = True
            strengths_msg = f"Solid technical explanation addressing {', '.join(matched_concepts)}."
            critique_msg = "Comprehensive answer. Mention production trade-offs to achieve maximum rating."
        else:
            # STAFF / STRONG HIRE
            accuracy_score = 5
            depth_score = 5
            clarity_score = 5
            overall_pct = 100.0
            recommendation = "🌟 STAFF-LEVEL MASTERY"
            is_correct = True
            strengths_msg = f"Exemplary answer thoroughly covering {', '.join(matched_concepts)} with engineering rigor."
            critique_msg = "Zero critical flaws detected. Ideal response."

        return InterviewEvaluationReport(
            role_evaluated=role,
            question_id=target["id"],
            overall_score_percentage=overall_pct,
            recommendation=recommendation,
            is_correct=is_correct,
            technical_accuracy=RubricScore(
                criterion="Technical Accuracy & Knowledge",
                score=accuracy_score,
                strengths=strengths_msg,
                critique_and_missing_points=critique_msg,
                model_answer_summary=target["model_answer"]
            ),
            system_depth_and_tradeoffs=RubricScore(
                criterion="Engineering Depth & Trade-offs",
                score=depth_score,
                strengths="Assessed against production engineering considerations.",
                critique_and_missing_points="Discuss edge cases and performance impacts." if depth_score < 4 else "Strong depth on trade-offs.",
                model_answer_summary=target["model_answer"]
            ),
            communication_clarity=RubricScore(
                criterion="Communication & Structure",
                score=clarity_score,
                strengths=f"Response length: {word_count} words.",
                critique_and_missing_points="Provide a structured definition followed by real examples." if clarity_score < 4 else "Clear, concise communication.",
                model_answer_summary=target["model_answer"]
            )
        )

# =====================================================================
# REST Endpoints
# =====================================================================

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

@app.get("/", response_class=HTMLResponse, summary="CareerPilot Web Dashboard")
async def serve_frontend():
    frontend_path = os.path.join(PROJECT_ROOT, "frontend", "index.html")
    if os.path.exists(frontend_path):
        with open(frontend_path, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse("<h2>Frontend index.html not found. Check frontend/ folder.</h2>")

@app.get("/api/health", summary="Health Check")
async def health_check():
    return {
        "status": "healthy",
        "app": "CareerPilot AI",
        "groq_configured": bool(settings.groq_api_key and settings.groq_api_key.startswith("gsk_")),
        "huggingface_configured": bool(settings.huggingface_api_key and settings.huggingface_api_key.startswith("hf_"))
    }

@app.get("/api/candidate", summary="Get Candidate Profile")
async def get_candidate_profile():
    path = os.path.join(PROJECT_ROOT, "data", "sample_resume.json")
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"error": "sample_resume.json not found"}

@app.get("/api/jobs", summary="Get demonstration job fixture (not live)")
async def get_scouted_jobs():
    path = os.path.join(PROJECT_ROOT, "data", "sample_job.json")
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"error": "sample_job.json not found"}

class RecentJobsRequest(BaseModel):
    candidate: Dict[str, Any]
    days: int = Field(default=3, ge=2, le=30)
    location: str = Field(default='all', pattern='^(all|india|remote)$')


@app.post('/api/jobs/recent', summary='Verified-date live postings matched with current resume')
async def get_recent_live_jobs(request: RecentJobsRequest):
    # No candidate data is sent to third-party sources or stored in a server cache.
    jobs, sources_ok, errors = await load_public_jobs()
    if not sources_ok:
        raise HTTPException(503, 'Live job feeds unavailable. Please retry shortly. No demo jobs have been substituted.')
    return {
        'jobs': query_jobs(jobs, request.candidate, days=request.days, location=request.location),
        'days': request.days,
        'sources_ok': sources_ok,
        'source_errors': errors,
        'fetched_at': __import__('datetime').datetime.now(__import__('datetime').timezone.utc).isoformat(),
        'note': 'Live listings with known publication dates only. Check location eligibility and active status on the employer site. Match is a heuristic, not hiring probability.'
    }


class ResumeTextRequest(BaseModel):
    text: str = Field(min_length=25, max_length=100000)
    filename: str = "Pasted_Resume.txt"


class PlanRequest(BaseModel):
    candidate: Dict[str, Any]


class AnswerRequest(BaseModel):
    candidate: Dict[str, Any]
    question: Dict[str, Any]
    answer: str = Field(min_length=1, max_length=10000)
    is_follow_up: bool = False


@app.post("/api/resume/upload", summary="Extract PDF DOCX or TXT resume")
async def upload_resume(file: UploadFile = File(...)):
    allowed = ('.pdf', '.docx', '.txt')
    if not file.filename or not file.filename.lower().endswith(allowed):
        raise HTTPException(400, "Upload a PDF, DOCX or TXT resume.")
    # Bound memory consumed even when Content-Length is missing.
    content = await file.read(10 * 1024 * 1024 + 1)
    text = extract_file_text(file.filename, content)
    return {'candidate': parse_resume(text, file.filename), 'extracted_characters': len(text)}


@app.post("/api/resume/parse", summary="Extract a pasted resume")
async def parse_custom_resume(payload: ResumeTextRequest):
    return {'candidate': parse_resume(payload.text, payload.filename),
            'extracted_characters': len(payload.text)}


@app.post("/api/interview/plan", summary="Create a 45-minute resume-specific interview plan")
async def interview_plan(payload: PlanRequest):
    return build_interview_plan(payload.candidate)


@app.post("/api/interview/feedback", summary="Contextual evaluation and HR follow-up")
async def interview_feedback(payload: AnswerRequest):
    return await evaluate_answer(payload.question, payload.answer, payload.candidate, payload.is_follow_up)


@app.get("/api/interview/questions", summary="Legacy sample interview questions")
async def get_interview_questions(role: str = Query("Data Scientist")):
    # For uploaded resumes, use POST /api/interview/plan with candidate data.
    questions = VoiceInterviewEngine.get_questions_for_role(role)
    return {'role': role, 'total_questions': len(questions), 'questions': questions,
            'note': 'Demo questions only. Use /api/interview/plan for resume-specific interviews.'}


@app.post("/api/interview/evaluate", summary="Legacy rubric evaluation")
async def evaluate_interview_endpoint(payload: EvaluateRequest):
    return VoiceInterviewEngine.evaluate_answer_local(
        payload.question_id, payload.candidate_answer, payload.role or "Data Scientist")

@app.websocket("/ws/mock-interview")
async def voice_interview_websocket(websocket: WebSocket):
    await websocket.accept()
    logger.info("Candidate connected to voice mock interview session.")

    try:
        questions = VoiceInterviewEngine.get_questions_for_role("Data Scientist")
        current_idx = 0
        first_q = questions[current_idx]
        await websocket.send_json({
            "type": "INTERVIEWER_PROMPT",
            "question_id": first_q["id"],
            "stage": first_q["stage"],
            "category": first_q["category"],
            "text": first_q["question"],
            "question_index": current_idx + 1,
            "total_questions": len(questions)
        })

        while True:
            data = await websocket.receive_text()
            payload = json.loads(data)
            candidate_text = payload.get("transcript", "")
            q_id = payload.get("question_id", first_q["id"])
            role = payload.get("role", "Data Scientist")

            report = VoiceInterviewEngine.evaluate_answer_local(q_id, candidate_text, role=role)
            await websocket.send_json({
                "type": "RUBRIC_EVALUATION_REPORT",
                "data": report.model_dump()
            })

    except WebSocketDisconnect:
        logger.info("Voice interview session closed by client.")
