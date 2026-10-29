import re
from typing import List, Dict, Any, Tuple
import numpy as np

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger("SkillExtractor")
    logger.success = logger.info

class SkillAndEntityExtractor:
    """
    Production NLP Entity Extraction & ESCO Taxonomy Grounder.
    Extracts raw technical skills, years of experience, and degrees from unstructured text,
    then projects them into standardized canonical concepts.
    """

    # Core tech ontology dictionary for deterministic fast-path matching
    CORE_SKILL_PATTERNS = [
        "python", "pytorch", "tensorflow", "scikit-learn", "xgboost", "lightgbm",
        "langchain", "langgraph", "fastapi", "docker", "kubernetes", "aws", "gcp",
        "azure", "sql", "postgresql", "mongodb", "redis", "kafka", "spark",
        "airflow", "git", "ci/cd", "rest api", "graphql", "playwright", "spacy",
        "huggingface", "llm", "rag", "genai", "nlp", "computer vision", "c++", "go"
    ]

    def __init__(self, use_gpu: bool = False):
        self.use_gpu = use_gpu
        self._init_encoder()

    def _init_encoder(self):
        """Lazy load sentence transformer for semantic grounding using Hugging Face Hub."""
        try:
            from sentence_transformers import SentenceTransformer
            from src.config import settings
            token = settings.huggingface_api_key if settings.huggingface_api_key else None
            self.encoder = SentenceTransformer("BAAI/bge-large-en-v1.5", token=token)
            logger.info("Loaded BAAI/bge-large-en-v1.5 embedding model from Hugging Face Hub.")
        except Exception as e:
            logger.warning(f"Could not load SentenceTransformer ({e}). Running in lightweight regex mode.")
            self.encoder = None

    def extract_skills_regex(self, text: str) -> List[str]:
        """Fast-path deterministic skill extraction using case-insensitive regex boundaries."""
        lower_text = text.lower()
        matched = set()
        for skill in self.CORE_SKILL_PATTERNS:
            pattern = r'\b' + re.escape(skill) + r'\b'
            if re.search(pattern, lower_text):
                matched.add(skill.title() if len(skill) > 3 else skill.upper())
        return sorted(list(matched))

    def extract_experience_years(self, text: str) -> float:
        """
        Parses required years of experience from job descriptions or resumes.
        Handles phrases like '5+ years', '3-5 years', 'at least 2 years'.
        """
        patterns = [
            r'(\d+(?:\.\d+)?)\s*(?:\+)?\s*(?:years?|yrs?)(?:\s+of)?\s+(?:experience|exp)',
            r'(?:minimum|at least)\s*(\d+(?:\.\d+)?)\s*(?:years?|yrs?)',
            r'(\d+)\s*(?:to|-)\s*(\d+)\s*(?:years?|yrs?)'
        ]
        
        for pat in patterns:
            match = re.search(pat, text, re.IGNORECASE)
            if match:
                groups = match.groups()
                if len(groups) == 2 and groups[1]: # e.g. 3-5 years -> return 3.0
                    return float(groups[0])
                elif groups[0]:
                    return float(groups[0])
        return 0.0

    def extract_degree_level(self, text: str) -> int:
        """
        Maps degree qualifications into ordinal scale:
        0=None, 1=Associate, 2=Bachelors, 3=Masters, 4=PhD
        """
        lower = text.lower()
        if re.search(r'\b(ph\.?d|doctorate)\b', lower):
            return 4
        if re.search(r'\b(master|m\.s\b|m\.tech|m\.sc|mba)\b', lower):
            return 3
        if re.search(r'\b(bachelor|b\.s\b|b\.tech|b\.e\b|b\.sc)\b', lower):
            return 2
        if re.search(r'\b(associate|diploma)\b', lower):
            return 1
        return 0

    def ground_skill_to_esco(self, raw_mention: str, canonical_taxonomies: List[str]) -> Tuple[str, float]:
        """
        Semantic vector grounder: projects an extracted raw skill onto the nearest
        canonical ESCO / O*NET label using Cosine Vector Similarity.
        """
        if not self.encoder or not canonical_taxonomies:
            return raw_mention, 1.0

        mention_emb = self.encoder.encode([raw_mention], normalize_embeddings=True)
        tax_embs = self.encoder.encode(canonical_taxonomies, normalize_embeddings=True)
        
        sims = np.dot(tax_embs, mention_emb[0])
        best_idx = int(np.argmax(sims))
        best_sim = float(sims[best_idx])

        if best_sim >= 0.80:
            return canonical_taxonomies[best_idx], best_sim
        return raw_mention, best_sim
