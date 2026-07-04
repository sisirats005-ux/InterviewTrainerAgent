"""
readiness_score.py — Interview Readiness Score Engine
=======================================================
Calculates a holistic, multi-factor Interview Readiness
Score from:
  1. Resume quality (ATS formatting)
  2. Skill match (against target role)
  3. Mock interview performance (if available)
  4. Technical knowledge (cert + project depth)
  5. Communication / presentation quality (heuristics)

Produces an overall percentage, individual category
scores, readiness level label, and improvement recs.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger("InterviewTrainer.Readiness")

# Weight of each factor in final score (must sum to 1.0)
WEIGHTS: dict[str, float] = {
    "resume_quality": 0.20,
    "skill_match": 0.25,
    "mock_performance": 0.20,
    "technical_knowledge": 0.20,
    "communication": 0.15,
}

READINESS_LEVELS: list[tuple[int, str, str]] = [
    (85, "Interview Ready",
     "Your profile is well-prepared for interviews at this level."),
    (70, "Strong Candidate",
     "You have a solid foundation. A few targeted improvements will make you stand out."),
    (55, "Developing",
     "Core areas are in place but gaps remain. Focus on the recommendations below."),
    (0, "Needs Preparation",
     "Significant gaps detected. Use this roadmap to systematically prepare."),
]


def _readiness_label(score: int) -> tuple[str, str]:
    for threshold, label, desc in READINESS_LEVELS:
        if score >= threshold:
            return label, desc
    return "Needs Preparation", "Significant gaps detected."


def _resume_quality_score(candidate_data: dict[str, Any]) -> int:
    """
    Score resume completeness and professional quality (0-100).
    """
    score = 0
    if candidate_data.get("name") not in ("Candidate Profile", "", None):
        score += 15
    if candidate_data.get("email"):
        score += 12
    if candidate_data.get("phone"):
        score += 8
    if candidate_data.get("linkedin"):
        score += 10
    if candidate_data.get("github"):
        score += 10
    if len(candidate_data.get("skills", [])) >= 5:
        score += 15
    if candidate_data.get("education"):
        score += 10
    if candidate_data.get("experience"):
        score += 10
    if len(candidate_data.get("projects", [])) >= 1:
        score += 10
    return min(score, 100)


def _skill_match_score(gap_score: int) -> int:
    """
    Convert the gap analysis score (0-100) to a readiness sub-score.
    """
    return max(5, min(100, gap_score))


def _mock_performance_score(mock_history: list[dict[str, Any]] | None) -> int:
    """
    Derive a mock interview performance score from the answer history.
    Returns 60 as a neutral default when no history is available.
    """
    if not mock_history:
        return 60  # neutral baseline
    scores = [item.get("score", 70) for item in mock_history if isinstance(item.get("score"), (int, float))]
    if not scores:
        return 60
    return int(sum(scores) / len(scores))


def _technical_knowledge_score(candidate_data: dict[str, Any]) -> int:
    """
    Heuristic score based on certifications, project depth, and skill count.
    """
    score = 0
    cert_count = len(candidate_data.get("certifications", []))
    proj_count = len(candidate_data.get("projects", []))
    skill_count = len(candidate_data.get("skills", []))
    exp_count = len(candidate_data.get("experience", []))

    score += min(cert_count * 20, 40)
    score += min(proj_count * 15, 30)
    score += min(skill_count * 3, 20)
    score += min(exp_count * 5, 10)
    return min(score, 100)


def _communication_score(candidate_data: dict[str, Any], mock_history: list[dict[str, Any]] | None) -> int:
    """
    Estimate communication quality from answer length, structure,
    and presence of quantified results in experience bullets.
    """
    score = 50  # base

    raw_text = candidate_data.get("raw_text", "")

    # Quantified achievements signal strong communication
    quantified = len([c for c in raw_text if c.isdigit()])
    if quantified >= 10:
        score += 20
    elif quantified >= 5:
        score += 10

    # Presence of action verbs is a good resume signal
    action_verbs = [
        "developed", "built", "designed", "implemented", "optimised",
        "led", "managed", "reduced", "improved", "increased",
        "created", "deployed", "automated", "delivered",
    ]
    raw_lower = raw_text.lower()
    verb_count = sum(1 for v in action_verbs if v in raw_lower)
    score += min(verb_count * 3, 20)

    # If mock answers are available, measure average answer length
    if mock_history:
        avg_len = sum(len(item.get("answer", "")) for item in mock_history) / len(mock_history)
        if avg_len >= 300:
            score += 10
        elif avg_len >= 150:
            score += 5

    return min(score, 100)


def _build_improvement_recs(
    category_scores: dict[str, int],
    candidate_data: dict[str, Any],
    mock_history: list[dict[str, Any]] | None,
) -> list[str]:
    """Generate targeted improvement recommendations based on category scores."""
    recs: list[str] = []

    if category_scores["resume_quality"] < 70:
        recs.append(
            "Improve resume completeness: add LinkedIn, GitHub, and a "
            "Certifications section to boost ATS and recruiter visibility."
        )
    if category_scores["skill_match"] < 65:
        recs.append(
            "Bridge skill gaps by building 1-2 projects for each missing "
            "technology and adding them to GitHub."
        )
    if category_scores["mock_performance"] < 65:
        recs.append(
            "Practice mock interviews daily. Focus on structuring answers "
            "using the STAR method for behavioural questions."
        )
    if category_scores["technical_knowledge"] < 65:
        recs.append(
            "Earn at least one industry certification (e.g. AWS, GCP, or IBM SkillsBuild) "
            "to demonstrate validated technical knowledge."
        )
    if category_scores["communication"] < 65:
        recs.append(
            "Quantify your achievements — use numbers, percentages, and time "
            "frames (e.g. 'reduced load time by 40%') throughout your resume."
        )
    if not recs:
        recs.append(
            "Excellent preparation! Continue practicing coding challenges and "
            "system design to reach the top-tier candidate bracket."
        )
    return recs


def calculate_readiness_score(
    candidate_data: dict[str, Any],
    gap_score: int,
    mock_history: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """
    Calculate a holistic Interview Readiness Score.

    Parameters
    ----------
    candidate_data : dict
        Parsed resume data from ``resume_parser.parse_resume()``.
    gap_score : int
        Skill gap score (0-100) from ``skill_gap.analyse_skill_gap()``.
    mock_history : list[dict], optional
        Completed mock interview answers with per-answer scores.

    Returns
    -------
    dict with keys:
        overall_score        (int, 0-100)
        category_scores      (dict[str, int])
        readiness_level      (str)
        readiness_description (str)
        improvement_recs     (list[str])
    """
    category_scores: dict[str, int] = {
        "resume_quality": _resume_quality_score(candidate_data),
        "skill_match": _skill_match_score(gap_score),
        "mock_performance": _mock_performance_score(mock_history),
        "technical_knowledge": _technical_knowledge_score(candidate_data),
        "communication": _communication_score(candidate_data, mock_history),
    }

    overall = sum(
        category_scores[cat] * weight
        for cat, weight in WEIGHTS.items()
    )
    overall_score = int(round(overall))
    overall_score = max(5, min(100, overall_score))

    readiness_level, readiness_description = _readiness_label(overall_score)
    improvement_recs = _build_improvement_recs(category_scores, candidate_data, mock_history)

    logger.info(
        "Readiness score for candidate '%s': %d/100 (%s)",
        candidate_data.get("name", "unknown"),
        overall_score,
        readiness_level,
    )

    return {
        "overall_score": overall_score,
        "category_scores": category_scores,
        "readiness_level": readiness_level,
        "readiness_description": readiness_description,
        "improvement_recs": improvement_recs,
    }
