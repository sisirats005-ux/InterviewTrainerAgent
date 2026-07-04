"""
ats_analyzer.py — ATS Resume Score Calculator
===============================================
Deterministic ATS compatibility scoring module.
Scores a parsed resume against a target job role
and returns keyword matches, missing keywords,
formatting signals, and actionable suggestions.

No LLM call — runs purely from parsed resume data
so it remains fast and offline-capable.
"""

from __future__ import annotations

import re
import logging
from typing import Any

logger = logging.getLogger("InterviewTrainer.ATS")

# ---------------------------------------------------------------------------
# ATS keyword library per job role family
# ---------------------------------------------------------------------------
ROLE_KEYWORDS: dict[str, list[str]] = {
    "software engineer": [
        "python", "java", "c++", "javascript", "algorithms", "data structures",
        "system design", "restful api", "microservices", "sql", "git", "docker",
        "kubernetes", "ci/cd", "unit testing", "agile", "oop", "problem solving",
    ],
    "backend developer": [
        "python", "flask", "django", "fastapi", "node.js", "restful api",
        "postgresql", "mongodb", "redis", "docker", "sql", "microservices",
        "authentication", "jwt", "celery", "rabbitmq", "git",
    ],
    "frontend developer": [
        "javascript", "typescript", "react", "vue", "angular", "html", "css",
        "tailwind", "responsive design", "webpack", "npm", "rest api",
        "accessibility", "git", "figma", "unit testing",
    ],
    "fullstack developer": [
        "javascript", "typescript", "react", "node.js", "python", "flask",
        "sql", "mongodb", "restful api", "docker", "git", "html", "css",
        "authentication", "ci/cd",
    ],
    "data scientist": [
        "python", "pandas", "numpy", "scikit-learn", "machine learning",
        "deep learning", "tensorflow", "pytorch", "sql", "data visualization",
        "statistics", "nlp", "feature engineering", "jupyter", "git",
    ],
    "data analyst": [
        "python", "sql", "pandas", "excel", "power bi", "tableau",
        "data visualization", "statistics", "r", "etl", "reporting", "git",
    ],
    "machine learning engineer": [
        "python", "tensorflow", "pytorch", "scikit-learn", "mlops", "docker",
        "kubernetes", "feature engineering", "model deployment", "sql",
        "deep learning", "nlp", "data pipelines", "aws", "git",
    ],
    "devops engineer": [
        "docker", "kubernetes", "jenkins", "ci/cd", "terraform", "ansible",
        "aws", "azure", "gcp", "linux", "bash", "monitoring", "git",
        "infrastructure as code", "networking",
    ],
    "cloud engineer": [
        "aws", "azure", "gcp", "docker", "kubernetes", "terraform", "ci/cd",
        "linux", "networking", "security", "storage", "serverless", "git",
        "infrastructure as code",
    ],
    "ai engineer": [
        "python", "llms", "langchain", "huggingface", "pytorch", "tensorflow",
        "rag", "vector database", "faiss", "nlp", "deep learning",
        "prompt engineering", "mlops", "docker", "git",
    ],
    "default": [
        "python", "sql", "git", "communication", "problem solving",
        "teamwork", "restful api", "agile", "documentation",
    ],
}

# ---------------------------------------------------------------------------
# ATS formatting / quality signals
# ---------------------------------------------------------------------------
POSITIVE_SIGNALS = [
    "github", "linkedin", "email", "phone", "certifications",
    "achievements", "projects", "education",
]

SECTION_PRESENCE_SCORE = {
    "name": 10,
    "email": 8,
    "phone": 6,
    "github": 5,
    "linkedin": 5,
    "skills": 15,
    "education": 10,
    "experience": 15,
    "projects": 10,
    "certifications": 10,
    "achievements": 6,
}


def _normalise(text: str) -> str:
    """Lower-case and strip extra whitespace."""
    return re.sub(r"\s+", " ", text.lower().strip())


def _get_role_keywords(job_role: str) -> list[str]:
    """Return the best-matching keyword list for the given job role."""
    role_lower = _normalise(job_role)
    for key, kws in ROLE_KEYWORDS.items():
        if key in role_lower or any(w in role_lower for w in key.split()):
            return kws
    return ROLE_KEYWORDS["default"]


def calculate_ats_score(
    candidate_data: dict[str, Any],
    job_role: str,
    jd_text: str = "",
) -> dict[str, Any]:
    """
    Calculate a deterministic ATS compatibility score (0-100).

    Parameters
    ----------
    candidate_data : dict
        Parsed resume data from ``resume_parser.parse_resume()``.
    job_role : str
        Target job role title.
    jd_text : str, optional
        Raw JD text — used for extra keyword extraction when available.

    Returns
    -------
    dict with keys:
        ats_score          (int)
        keyword_matches    (list[str])
        missing_keywords   (list[str])
        formatting_score   (int, 0-100)
        keyword_score      (int, 0-100)
        suggestions        (list[str])
        keyword_coverage   (float, 0.0-1.0)
    """
    raw_text: str = candidate_data.get("raw_text", "").lower()
    skills: list[str] = [s.lower() for s in candidate_data.get("skills", [])]

    # --- 1. Role keywords ---
    role_kws = _get_role_keywords(job_role)

    # Supplement with JD-extracted keywords if JD text is provided
    if jd_text:
        jd_lower = _normalise(jd_text)
        # Pull multi-word and single technical terms from JD
        jd_words = set(re.findall(r"[a-z][a-z0-9\+\#\.\-]{1,30}", jd_lower))
        for rk in list(role_kws):
            if rk in jd_lower:
                pass  # already included
        # Add prominent JD-specific terms not already in list
        extra = [w for w in jd_words if len(w) >= 3 and w not in role_kws]
        role_kws = role_kws + extra[:10]

    # --- 2. Keyword matching ---
    matched: list[str] = []
    missing: list[str] = []
    for kw in role_kws:
        # Allow partial word boundary match for compound terms like "ci/cd"
        pattern = re.escape(kw)
        if re.search(pattern, raw_text) or kw in skills:
            matched.append(kw)
        else:
            missing.append(kw)

    keyword_score = int((len(matched) / max(len(role_kws), 1)) * 100)
    keyword_coverage = round(len(matched) / max(len(role_kws), 1), 2)

    # --- 3. Formatting / section presence score ---
    formatting_score = 0
    max_fmt_score = sum(SECTION_PRESENCE_SCORE.values())
    for field, weight in SECTION_PRESENCE_SCORE.items():
        value = candidate_data.get(field)
        if isinstance(value, str) and value.strip():
            formatting_score += weight
        elif isinstance(value, list) and len(value) > 0:
            formatting_score += weight
    formatting_score = int((formatting_score / max_fmt_score) * 100)

    # --- 4. Composite ATS score (weighted) ---
    ats_score = int(keyword_score * 0.65 + formatting_score * 0.35)
    ats_score = max(5, min(100, ats_score))

    # --- 5. Generate concrete suggestions ---
    suggestions: list[str] = []

    if not candidate_data.get("linkedin"):
        suggestions.append(
            "Add a LinkedIn profile URL — ATS systems rank resumes with LinkedIn "
            "profiles significantly higher."
        )
    if not candidate_data.get("github"):
        suggestions.append(
            "Include a GitHub profile URL to showcase your code portfolio and "
            "open-source contributions."
        )
    if len(candidate_data.get("certifications", [])) == 0:
        suggestions.append(
            "Add relevant certifications (e.g. AWS, Google Cloud, IBM SkillsBuild) "
            "to strengthen keyword density."
        )
    if missing:
        top_missing = missing[:5]
        suggestions.append(
            f"Incorporate these high-value keywords into your resume: "
            f"{', '.join(top_missing)}."
        )
    if keyword_score < 60:
        suggestions.append(
            "Your resume keyword density is low for this role. Mirror the exact "
            "terms from the job description in your skills and experience sections."
        )
    if not candidate_data.get("experience"):
        suggestions.append(
            "Add a dedicated Work Experience section with quantified achievements "
            "(e.g. 'improved performance by 30%')."
        )
    if len(candidate_data.get("projects", [])) < 2:
        suggestions.append(
            "Include at least 2-3 personal or academic projects that directly "
            "demonstrate the skills required for this role."
        )
    if formatting_score < 70:
        suggestions.append(
            "Ensure your resume contains all core sections: Summary, Skills, "
            "Experience, Projects, Education, and Certifications."
        )

    logger.info(
        "ATS score calculated for role '%s': %d/100 "
        "(kw=%d%%, fmt=%d%%, matched=%d/%d)",
        job_role, ats_score, keyword_score, formatting_score,
        len(matched), len(role_kws),
    )

    return {
        "ats_score": ats_score,
        "keyword_score": keyword_score,
        "formatting_score": formatting_score,
        "keyword_matches": sorted(matched),
        "missing_keywords": sorted(missing),
        "keyword_coverage": keyword_coverage,
        "suggestions": suggestions,
    }
