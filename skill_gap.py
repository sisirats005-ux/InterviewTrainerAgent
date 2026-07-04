"""
skill_gap.py — Skill Gap Analysis Engine
==========================================
Compares a candidate's extracted skills against
a target job role and optional JD text to
produce four skill tiers and a learning roadmap.

This module is fully deterministic — no LLM call.
It runs quickly and can be used as a standalone
pre-processor before the Granite generation step.
"""

from __future__ import annotations

import re
import logging
from typing import Any

logger = logging.getLogger("InterviewTrainer.SkillGap")

# ---------------------------------------------------------------------------
# Recommended skill sets per role — used when no JD text is provided
# ---------------------------------------------------------------------------
ROLE_SKILL_SETS: dict[str, dict[str, list[str]]] = {
    "software engineer": {
        "required": [
            "Python", "Java", "Algorithms", "Data Structures",
            "SQL", "Git", "RESTful APIs", "System Design",
        ],
        "recommended": [
            "Docker", "Kubernetes", "CI/CD", "AWS", "Microservices",
            "Redis", "Unit Testing", "Agile",
        ],
    },
    "backend developer": {
        "required": [
            "Python", "Flask", "RESTful APIs", "PostgreSQL",
            "SQL", "Git", "Docker",
        ],
        "recommended": [
            "Redis", "Celery", "FastAPI", "MongoDB",
            "JWT", "CI/CD", "AWS",
        ],
    },
    "frontend developer": {
        "required": [
            "JavaScript", "React", "HTML", "CSS", "Git",
            "TypeScript", "Responsive Design",
        ],
        "recommended": [
            "Vue", "Tailwind", "Webpack", "Accessibility",
            "Unit Testing", "Figma",
        ],
    },
    "fullstack developer": {
        "required": [
            "JavaScript", "React", "Python", "Flask",
            "SQL", "RESTful APIs", "Git", "HTML", "CSS",
        ],
        "recommended": [
            "Docker", "MongoDB", "CI/CD", "TypeScript",
            "Authentication", "AWS",
        ],
    },
    "data scientist": {
        "required": [
            "Python", "Pandas", "NumPy", "Scikit-Learn",
            "Machine Learning", "SQL", "Statistics",
        ],
        "recommended": [
            "TensorFlow", "PyTorch", "Deep Learning", "NLP",
            "Data Visualization", "Feature Engineering", "Git",
        ],
    },
    "data analyst": {
        "required": [
            "Python", "SQL", "Pandas", "Excel",
            "Data Visualization", "Statistics",
        ],
        "recommended": [
            "Power BI", "Tableau", "R", "ETL", "Reporting", "Git",
        ],
    },
    "machine learning engineer": {
        "required": [
            "Python", "TensorFlow", "PyTorch", "Scikit-Learn",
            "Machine Learning", "Deep Learning", "SQL",
        ],
        "recommended": [
            "MLOps", "Docker", "Kubernetes", "Feature Engineering",
            "NLP", "AWS", "Model Deployment",
        ],
    },
    "devops engineer": {
        "required": [
            "Docker", "Kubernetes", "CI/CD", "Linux",
            "Git", "Bash", "AWS",
        ],
        "recommended": [
            "Terraform", "Ansible", "Jenkins",
            "Monitoring", "Networking", "Azure",
        ],
    },
    "cloud engineer": {
        "required": [
            "AWS", "Docker", "Kubernetes", "Linux",
            "Git", "Terraform", "Networking",
        ],
        "recommended": [
            "Azure", "GCP", "CI/CD", "Security",
            "Serverless", "Storage",
        ],
    },
    "ai engineer": {
        "required": [
            "Python", "LLMs", "LangChain", "HuggingFace",
            "PyTorch", "NLP", "RAG",
        ],
        "recommended": [
            "FAISS", "Generative AI", "MLOps", "Docker",
            "Prompt Engineering", "Git",
        ],
    },
    "default": {
        "required": [
            "Python", "SQL", "Git", "RESTful APIs",
        ],
        "recommended": [
            "Docker", "AWS", "Agile", "Communication",
        ],
    },
}

# ---------------------------------------------------------------------------
# Learning roadmap templates per skill
# ---------------------------------------------------------------------------
LEARNING_RESOURCES: dict[str, str] = {
    "Docker": "Week 1: Learn Docker fundamentals — containers, images, volumes, and networks. Practice by containerising a Flask app.",
    "Kubernetes": "Week 2-3: Study Kubernetes pods, deployments, and services. Deploy a multi-container application on Minikube.",
    "AWS": "Week 2-3: Earn AWS Cloud Practitioner Foundations badge on IBM SkillsBuild. Practice S3, EC2, and Lambda.",
    "CI/CD": "Week 1: Set up a GitHub Actions pipeline for a Python project covering lint, test, and build stages.",
    "Machine Learning": "Month 1: Complete Andrew Ng's ML course. Implement classification, regression, and clustering projects.",
    "Deep Learning": "Month 2: Study CNNs and RNNs using TensorFlow/PyTorch. Train a model on a public dataset.",
    "NLP": "Month 2: Build a text classification and sentiment analysis project using Hugging Face Transformers.",
    "System Design": "Week 2-4: Study rate limiters, caches, CDNs, and load balancers. Practice on system-design-primer.",
    "Microservices": "Week 2: Design a service-oriented architecture with independent deployable services using Docker Compose.",
    "Redis": "Week 1: Integrate Redis caching into a Flask/FastAPI application. Benchmark performance improvements.",
    "MongoDB": "Week 1: Build a CRUD application with MongoDB Atlas. Compare document design patterns.",
    "TypeScript": "Week 1-2: Add TypeScript to an existing JavaScript project. Learn interfaces, generics, and type guards.",
    "React": "Month 1: Build a full CRUD SPA using React with hooks, context API, and React Router.",
    "FastAPI": "Week 1: Convert a Flask REST API to FastAPI. Add Pydantic validation and async endpoints.",
    "Terraform": "Week 2: Write Terraform configurations to provision AWS EC2 and S3 resources. Use remote state.",
    "MLOps": "Month 2: Learn MLflow for experiment tracking, model registry, and deployment pipelines.",
    "RAG": "Week 2: Build a RAG pipeline using LangChain + FAISS + HuggingFace. Index your own documents.",
    "LangChain": "Week 1: Complete the LangChain official quickstart. Build a conversational agent with memory.",
    "default": "Allocate 1-2 weeks to study this topic with a practical hands-on project on GitHub.",
}


def _normalise(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower().strip())


def _get_role_profile(job_role: str) -> dict[str, list[str]]:
    """Return the best-matching skill profile for the given job role."""
    role_lower = _normalise(job_role)
    for key, profile in ROLE_SKILL_SETS.items():
        if key in role_lower or any(w in role_lower for w in key.split()):
            return profile
    return ROLE_SKILL_SETS["default"]


def analyse_skill_gap(
    candidate_data: dict[str, Any],
    job_role: str,
    jd_text: str = "",
) -> dict[str, Any]:
    """
    Perform a four-tier skill gap analysis.

    Returns
    -------
    dict with keys:
        strong_skills       (list[str]) — candidate has AND are role-relevant
        matching_skills     (list[str]) — candidate has; maps to required/recommended
        missing_skills      (list[str]) — required but absent from candidate
        recommended_skills  (list[str]) — nice-to-have; absent from candidate
        learning_roadmap    (list[str]) — prioritised steps to close gap
        gap_score           (int)       — 0-100; higher = better match
    """
    profile = _get_role_profile(job_role)
    required: list[str] = profile["required"]
    recommended: list[str] = profile["recommended"]

    # Candidate skills — build a lower-case set for matching
    candidate_skills_raw: list[str] = candidate_data.get("skills", [])
    candidate_lower: set[str] = {_normalise(s) for s in candidate_skills_raw}
    raw_text_lower = _normalise(candidate_data.get("raw_text", ""))

    def _has_skill(skill: str) -> bool:
        sl = _normalise(skill)
        if sl in candidate_lower:
            return True
        # Also match inside raw text for multi-word skills
        return bool(re.search(re.escape(sl), raw_text_lower))

    # --- Categorise ---
    strong_skills: list[str] = []
    matching_skills: list[str] = []
    missing_skills: list[str] = []
    recommended_present: list[str] = []
    recommended_missing: list[str] = []

    for skill in required:
        if _has_skill(skill):
            strong_skills.append(skill)
        else:
            missing_skills.append(skill)

    for skill in recommended:
        if _has_skill(skill):
            recommended_present.append(skill)
            matching_skills.append(skill)
        else:
            recommended_missing.append(skill)

    # Extra candidate skills not in either list — still show as matching
    all_role_skills_lower = {_normalise(s) for s in required + recommended}
    for raw_skill in candidate_skills_raw:
        if _normalise(raw_skill) not in all_role_skills_lower and raw_skill not in matching_skills:
            matching_skills.append(raw_skill)

    # --- Gap score ---
    total_required = max(len(required), 1)
    gap_score = int((len(strong_skills) / total_required) * 100)
    gap_score = max(5, min(100, gap_score))

    # --- Build learning roadmap from missing skills (priority: required first) ---
    roadmap_items: list[str] = []
    priority_missing = missing_skills + recommended_missing
    for skill in priority_missing[:8]:
        entry = LEARNING_RESOURCES.get(skill, LEARNING_RESOURCES["default"])
        roadmap_items.append(f"**{skill}**: {entry}")

    if not roadmap_items:
        roadmap_items.append(
            "Your skill set closely matches the role requirements. "
            "Focus on deepening expertise in your strongest areas and practicing system design."
        )

    logger.info(
        "Skill gap analysis for '%s': strong=%d, missing=%d, recommended_missing=%d, score=%d",
        job_role, len(strong_skills), len(missing_skills), len(recommended_missing), gap_score,
    )

    return {
        "strong_skills": strong_skills,
        "matching_skills": matching_skills,
        "missing_skills": missing_skills,
        "recommended_skills": recommended_missing,
        "learning_roadmap": roadmap_items,
        "gap_score": gap_score,
    }
