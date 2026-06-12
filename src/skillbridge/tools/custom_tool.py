"""Lean Serper search tool.

The default SerperDevTool returns ~3-5K tokens per call (full sitelinks,
peopleAlsoAsk, relatedSearches). With 4 sequential gap searches that
overflows Groq's 6K TPM bucket on llama-3.1-8b-instant. This wrapper
returns only what the curator needs: title | link | snippet, top 5
results — roughly 500-1000 tokens per call.
"""
import os
from typing import Type

import requests
from crewai.tools import BaseTool
from pydantic import BaseModel, Field


class SearchCoursesInput(BaseModel):
    query: str = Field(
        ...,
        description="Course search query, e.g. 'PyTorch advanced course'.",
    )


class LeanSerperTool(BaseTool):
    name: str = "search_courses"
    description: str = (
        "Search the web for online courses. Returns up to 5 results, "
        "each formatted as 'title | url | snippet'."
    )
    args_schema: Type[BaseModel] = SearchCoursesInput

    def _run(self, query: str) -> str:
        api_key = os.getenv("SERPER_API_KEY")
        if not api_key:
            return "Error: SERPER_API_KEY not set."

        try:
            resp = requests.post(
                "https://google.serper.dev/search",
                headers={"X-API-KEY": api_key, "Content-Type": "application/json"},
                json={"q": query, "num": 5},
                timeout=15,
            )
            resp.raise_for_status()
        except requests.RequestException as e:
            return f"Search failed: {e}"

        results = resp.json().get("organic", [])[:5]
        if not results:
            return "No results."

        lines = [
            f"- {r.get('title', '')} | {r.get('link', '')} | {r.get('snippet', '')}"
            for r in results
        ]
        return "\n".join(lines)