from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from crewai.agents.agent_builder.base_agent import BaseAgent
from skillbridge.tools.custom_tool import LeanSerperTool

from skillbridge.llm import groq_llm, groq_tool_llm
from skillbridge.models import CourseRecommendations


@CrewBase
class CourseRecommendationCrew():
    """Crew 2 — researches and curates course recommendations per skill gap."""

    # Override the default config/agents.yaml + config/tasks.yaml paths
    agents_config = "config/course_agents.yaml"
    tasks_config = "config/course_tasks.yaml"

    agents: list[BaseAgent]
    tasks: list[Task]

    @agent
    def course_researcher(self) -> Agent:
        return Agent(
            config=self.agents_config['course_researcher'],  # type: ignore[index]
            tools=[LeanSerperTool()],
            llm=groq_llm,
            verbose=True,
        )

    @agent
    def course_curator(self) -> Agent:
        return Agent(
            config=self.agents_config['course_curator'],  # type: ignore[index]
            llm=groq_tool_llm,
            verbose=True,
        )

    @task
    def research_courses_task(self) -> Task:
        return Task(
            config=self.tasks_config['research_courses_task'],  # type: ignore[index]
        )

    @task
    def curate_courses_task(self) -> Task:
        return Task(
            config=self.tasks_config['curate_courses_task'],  # type: ignore[index]
            output_pydantic=CourseRecommendations,
            context=[self.research_courses_task()],
        )

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True,
        )