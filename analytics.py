"""
analytics.py — User Analytics & Progress Tracker
==================================================
Persists and aggregates session analytics to a
local JSON file (uploads/analytics.json).

Tracks:
  - Total sessions / interviews completed
  - Per-session scores across all modules
  - Skill progress over time
  - Historical readiness trend
  - Strong / weak skill categories

Designed to be lightweight with no external DB.
All data is keyed by session_id (UUID).
"""

from __future__ import annotations

import json
import os
import logging
import time
from typing import Any

logger = logging.getLogger("InterviewTrainer.Analytics")

ANALYTICS_PATH = os.path.join("uploads", "analytics.json")


def _load() -> dict[str, Any]:
    """Load analytics store from disk."""
    try:
        if os.path.exists(ANALYTICS_PATH):
            with open(ANALYTICS_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception as exc:
        logger.warning("Failed to load analytics: %s", exc)
    return {"sessions": [], "summary": {}}


def _save(data: dict[str, Any]) -> None:
    """Persist analytics store to disk."""
    try:
        os.makedirs(os.path.dirname(ANALYTICS_PATH), exist_ok=True)
        with open(ANALYTICS_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception as exc:
        logger.warning("Failed to save analytics: %s", exc)


def record_session(
    session_id: str,
    candidate_name: str,
    job_role: str,
    company: str,
    ats_score: int,
    readiness_score: int,
    mock_avg_score: int | None,
    strong_skills: list[str],
    missing_skills: list[str],
    category_scores: dict[str, int],
) -> None:
    """
    Record a completed preparation session to the analytics store.
    """
    store = _load()

    entry: dict[str, Any] = {
        "session_id": session_id,
        "timestamp": time.time(),
        "candidate_name": candidate_name,
        "job_role": job_role,
        "company": company,
        "ats_score": ats_score,
        "readiness_score": readiness_score,
        "mock_avg_score": mock_avg_score,
        "strong_skills": strong_skills,
        "missing_skills": missing_skills,
        "category_scores": category_scores,
    }

    store.setdefault("sessions", []).append(entry)
    store["summary"] = _compute_summary(store["sessions"])
    _save(store)
    logger.info("Analytics recorded for session %s", session_id)


def get_dashboard_data() -> dict[str, Any]:
    """
    Return aggregated analytics for the dashboard template.

    Returns
    -------
    dict with keys:
        total_sessions         (int)
        avg_ats_score          (float)
        avg_readiness_score    (float)
        avg_mock_score         (float)
        top_strong_skills      (list[str])
        top_weak_skills        (list[str])
        recent_sessions        (list[dict])  — latest 5
        readiness_trend        (list[int])   — last 10 overall scores
        category_averages      (dict[str, int])
    """
    store = _load()
    sessions: list[dict[str, Any]] = store.get("sessions", [])

    if not sessions:
        return _empty_dashboard()

    recent = sorted(sessions, key=lambda s: s.get("timestamp", 0), reverse=True)[:5]
    trend = [s["readiness_score"] for s in sorted(sessions, key=lambda s: s.get("timestamp", 0))[-10:]]

    # Aggregate skill frequency
    strong_freq: dict[str, int] = {}
    weak_freq: dict[str, int] = {}
    for s in sessions:
        for sk in s.get("strong_skills", []):
            strong_freq[sk] = strong_freq.get(sk, 0) + 1
        for sk in s.get("missing_skills", []):
            weak_freq[sk] = weak_freq.get(sk, 0) + 1

    top_strong = sorted(strong_freq, key=lambda k: -strong_freq[k])[:6]
    top_weak = sorted(weak_freq, key=lambda k: -weak_freq[k])[:6]

    # Category averages
    cat_totals: dict[str, list[int]] = {}
    for s in sessions:
        for cat, val in s.get("category_scores", {}).items():
            cat_totals.setdefault(cat, []).append(val)
    cat_averages: dict[str, int] = {
        cat: int(sum(vals) / len(vals)) for cat, vals in cat_totals.items()
    }

    # Global averages
    ats_scores = [s["ats_score"] for s in sessions if s.get("ats_score")]
    readiness_scores = [s["readiness_score"] for s in sessions if s.get("readiness_score")]
    mock_scores = [s["mock_avg_score"] for s in sessions if s.get("mock_avg_score") is not None]

    return {
        "total_sessions": len(sessions),
        "avg_ats_score": round(sum(ats_scores) / len(ats_scores), 1) if ats_scores else 0,
        "avg_readiness_score": round(sum(readiness_scores) / len(readiness_scores), 1) if readiness_scores else 0,
        "avg_mock_score": round(sum(mock_scores) / len(mock_scores), 1) if mock_scores else 0,
        "top_strong_skills": top_strong,
        "top_weak_skills": top_weak,
        "recent_sessions": recent,
        "readiness_trend": trend,
        "category_averages": cat_averages,
    }


def _empty_dashboard() -> dict[str, Any]:
    return {
        "total_sessions": 0,
        "avg_ats_score": 0,
        "avg_readiness_score": 0,
        "avg_mock_score": 0,
        "top_strong_skills": [],
        "top_weak_skills": [],
        "recent_sessions": [],
        "readiness_trend": [],
        "category_averages": {},
    }


def _compute_summary(sessions: list[dict[str, Any]]) -> dict[str, Any]:
    if not sessions:
        return {}
    ats = [s["ats_score"] for s in sessions if s.get("ats_score")]
    rd = [s["readiness_score"] for s in sessions if s.get("readiness_score")]
    return {
        "total": len(sessions),
        "avg_ats": round(sum(ats) / len(ats), 1) if ats else 0,
        "avg_readiness": round(sum(rd) / len(rd), 1) if rd else 0,
    }
