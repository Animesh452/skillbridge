from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from crewai.agents.agent_builder.base_agent import BaseAgent

from skillbridge.llm import groq_llm
from skillbridge.models import CandidateSkillsList, RequiredSkillsList


@CrewBase
class SkillsAnalysisCrew():
    """Crew 1 — extracts skills from JD and resume in parallel."""

    agents: list[BaseAgent]
    tasks: list[Task]

    @agent
    def jd_analyzer(self) -> Agent:
        return Agent(
            config=self.agents_config['jd_analyzer'],  # type: ignore[index]
            llm=groq_llm,
            verbose=True,
        )

    @agent
    def resume_analyzer(self) -> Agent:
        return Agent(
            config=self.agents_config['resume_analyzer'],  # type: ignore[index]
            llm=groq_llm,
            verbose=True,
        )

    @task
    def analyze_jd_task(self) -> Task:
        return Task(
            config=self.tasks_config['analyze_jd_task'],  # type: ignore[index]
            output_pydantic=RequiredSkillsList,
        )

    @task
    def analyze_resume_task(self) -> Task:
        return Task(
            config=self.tasks_config['analyze_resume_task'],  # type: ignore[index]
            output_pydantic=CandidateSkillsList,
        )

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True,
        )