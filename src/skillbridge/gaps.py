"""Gap calculation — pure Python, no LLM.

Compares required_skills (JD) against candidate_skills (resume) and
produces a ranked list of SkillGap objects. Gap score is 1-10; priority
is derived from the score.
"""
from typing import Dict, List

from skillbridge.models import (
    GapPriority,
    Skill,
    SkillGap,
    SkillLevel,
    SkillsAnalysis,
    SKILL_LEVEL_ORDER,
)


def _normalize(name: str) -> str:
    """Case- and whitespace-insensitive skill name key."""
    return name.strip().lower()


def _index_skills(skills: List[Skill]) -> Dict[str, Skill]:
    """Build a normalized-name → Skill lookup, last-write-wins on dupes."""
    return {_normalize(s.name): s for s in skills}


def _score_gap(required: SkillLevel, candidate: SkillLevel) -> int:
    """Gap score from 1 (trivial) to 10 (critical/missing).

    Math: distance between required and candidate levels on the 0-4 scale,
    weighted so a missing skill at expert level scores 10 and a 1-step
    behind at beginner level scores ~2.
    """
    req_val = SKILL_LEVEL_ORDER[required]
    cand_val = SKILL_LEVEL_ORDER[candidate]
    distance = max(0, req_val - cand_val)

    # Missing entirely (candidate == UNKNOWN, value 0): scale by required level
    if candidate == SkillLevel.UNKNOWN:
        # required expert (4) → 10, advanced (3) → 8, intermediate (2) → 6,
        # beginner (1) → 4, unknown (0) → 2
        return max(2, req_val * 2 + 2)

    # Partial match: candidate has the skill but not at the right level
    # 1-step behind → 3, 2-step → 6, 3-step → 9, 4-step → 10
    if distance == 0:
        return 1  # met or exceeded
    return min(10, distance * 3)


def _priority(score: int) -> GapPriority:
    if score >= 9:
        return GapPriority.CRITICAL
    if score >= 6:
        return GapPriority.HIGH
    if score >= 3:
        return GapPriority.MEDIUM
    return GapPriority.LOW


def calculate_gaps(
    analysis: SkillsAnalysis,
    min_score: int = 3,
) -> List[SkillGap]:
    """Return gaps for every required skill, filtered and sorted.

    A gap is included if its score >= min_score. Default 3 drops trivial
    "you have it, just go one level deeper" matches so we don't spam the
    course recommender.

    Sorted by gap_score descending so the curator sees the worst gaps first.
    """
    candidate_index = _index_skills(analysis.candidate_skills)

    gaps: List[SkillGap] = []
    for required in analysis.required_skills:
        key = _normalize(required.name)
        candidate = candidate_index.get(key)
        candidate_level = candidate.level if candidate else SkillLevel.UNKNOWN

        score = _score_gap(required.level, candidate_level)
        if score < min_score:
            continue

        gaps.append(
            SkillGap(
                skill=required.name,
                required_level=required.level,
                candidate_level=candidate_level,
                gap_score=score,
                priority=_priority(score),
            )
        )

    gaps.sort(key=lambda g: g.gap_score, reverse=True)
    return gaps


def format_gaps_for_research(gaps: List[SkillGap]) -> str:
    """Format the gap list as a prompt-ready string for Crew 2."""
    lines = []
    for g in gaps:
        have = (
            g.candidate_level.value
            if g.candidate_level != SkillLevel.UNKNOWN
            else "missing"
        )
        lines.append(
            f"- {g.skill} (need: {g.required_level.value}, have: {have}) "
            f"[{g.priority.value.upper()} priority]"
        )
    return "\n".join(lines)