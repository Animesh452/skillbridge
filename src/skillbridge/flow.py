"""SkillBridge Flow — assembles the four-step pipeline.

parse_inputs → SkillsAnalysisCrew → calculate_gaps → CourseRecommendationCrew → format_report
"""
from typing import List
import time

from crewai.flow.flow import Flow, listen, start
from pydantic import BaseModel

from skillbridge.course_crew import CourseRecommendationCrew
from skillbridge.crew import SkillsAnalysisCrew
from skillbridge.gaps import calculate_gaps, format_gaps_for_research
from skillbridge.models import (
    CourseRec,
    SkillGap,
    SkillsAnalysis,
)


class SkillBridgeState(BaseModel):
    """Flow state carried through all steps."""
    job_description: str = ""
    resume_text: str = ""

    analysis: SkillsAnalysis | None = None
    gaps: List[SkillGap] = []
    courses: List[CourseRec] = []
    report: str = ""


class SkillBridgeFlow(Flow[SkillBridgeState]):
    """End-to-end pipeline. Inputs land in state via kickoff(inputs=...)."""

    @start()
    def parse_inputs(self) -> None:
        """Validate inputs are present; trim whitespace."""
        self.state.job_description = self.state.job_description.strip()
        self.state.resume_text = self.state.resume_text.strip()
        if not self.state.job_description:
            raise ValueError("job_description is required")
        if not self.state.resume_text:
            raise ValueError("resume_text is required") 

    @listen(parse_inputs)
    def run_skills_analysis(self) -> None:
        """Crew 1 — extract required and candidate skills, combine in Python."""
        result = SkillsAnalysisCrew().crew().kickoff(inputs={
            "job_description": self.state.job_description,
            "resume_text": self.state.resume_text,
        })

        # tasks_output is in crew definition order: [jd, resume]
        jd_out = result.tasks_output[0].pydantic
        resume_out = result.tasks_output[1].pydantic

        self.state.analysis = SkillsAnalysis(
            required_skills=jd_out.required_skills,
            candidate_skills=resume_out.candidate_skills,
        )
  
    @listen(run_skills_analysis)
    def compute_gaps(self) -> None:
        """Phase 3 — pure-Python gap calculation."""
        self.state.gaps = calculate_gaps(self.state.analysis)

    @listen(compute_gaps)
    def recommend_courses(self) -> None:
        """Crew 2 — research and curate one course per gap.

        Sleeps 30s before kicking off Crew 2 so the Groq 70B TPM bucket
        refills after Crew 1. Curator stays on 70B to preserve judgment
        quality on platform/depth ranking. See README for rate-limit notes.
        """
        if not self.state.gaps:
            self.state.courses = []
            return

        result = CourseRecommendationCrew().crew().kickoff(inputs={
            "gaps_summary": format_gaps_for_research(self.state.gaps),
        })
        self.state.courses = result.pydantic.recommendations

    @listen(recommend_courses)
    def format_report(self) -> None:
        """Build the final markdown report from state."""
        lines: List[str] = []
        lines.append("# SkillBridge Report\n")

        # Gaps section
        lines.append("## Skill Gaps\n")
        if not self.state.gaps:
            lines.append("_No significant gaps detected — your resume covers the JD's requirements._\n")
        else:
            lines.append("| Priority | Skill | Required | You Have | Score |")
            lines.append("|---|---|---|---|---|")
            for g in self.state.gaps:
                have = (
                    g.candidate_level.value
                    if g.candidate_level.value != "unknown"
                    else "missing"
                )
                lines.append(
                    f"| **{g.priority.value.upper()}** | {g.skill} | "
                    f"{g.required_level.value} | {have} | {g.gap_score}/10 |"
                )
            lines.append("")

        # Course recommendations section
        lines.append("## Recommended Courses\n")
        if not self.state.courses:
            lines.append("_No course recommendations — nothing to close._\n")
        else:
            for c in self.state.courses:
                lines.append(f"### {c.skill}")
                lines.append(f"**[{c.title}]({c.url})** — {c.platform}")
                lines.append(f"_Duration: {c.duration} · Cost: {c.cost}_\n")

        self.state.report = "\n".join(lines)