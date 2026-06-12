"""Pydantic models for the SkillBridge pipeline."""
from enum import Enum
from typing import List

from pydantic import BaseModel, Field


class SkillLevel(str, Enum):
    UNKNOWN = "unknown"
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    EXPERT = "expert"


# Ordering helper for gap math — keep alongside the enum so any module that
# imports SkillLevel gets the comparison map for free.
SKILL_LEVEL_ORDER = {
    SkillLevel.UNKNOWN: 0,
    SkillLevel.BEGINNER: 1,
    SkillLevel.INTERMEDIATE: 2,
    SkillLevel.ADVANCED: 3,
    SkillLevel.EXPERT: 4,
}


class GapPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Skill(BaseModel):
    """A single skill with proficiency level."""
    name: str = Field(..., description="Skill name, e.g. 'PyTorch' or 'AWS Lambda'.")
    level: SkillLevel = Field(
        default=SkillLevel.UNKNOWN,
        description="Required level (for JD skills) or demonstrated level (for resume skills).",
    )


class SkillsAnalysis(BaseModel):
    """Output of Crew 1 — Skills Analysis Crew."""
    required_skills: List[Skill] = Field(..., description="Skills extracted from the job description.")
    candidate_skills: List[Skill] = Field(..., description="Skills extracted from the candidate's resume.")


class SkillGap(BaseModel):
    """A single gap produced by the Python gap calculator (Phase 3)."""
    skill: str
    required_level: SkillLevel
    candidate_level: SkillLevel
    gap_score: int = Field(..., ge=1, le=10, description="1 = trivial gap, 10 = critical missing skill.")
    priority: GapPriority


class CourseRec(BaseModel):
    """A single course recommendation from Crew 2."""
    skill: str = Field(..., description="The gap skill this course addresses.")
    title: str
    platform: str = Field(..., description="e.g. 'Coursera', 'DeepLearning.AI', 'Udemy'.")
    url: str
    duration: str = Field(..., description="e.g. '4 weeks' or '12 hours'.")
    cost: str = Field(..., description="e.g. 'Free', '$49', 'Subscription'.")


class CourseRecommendations(BaseModel):
    """Wrapper for crewAI's output_pydantic — holds the final course list."""
    recommendations: List[CourseRec]

class RequiredSkillsList(BaseModel):
    """Output of the JD analyzer task."""
    required_skills: List[Skill]


class CandidateSkillsList(BaseModel):
    """Output of the resume analyzer task."""
    candidate_skills: List[Skill]