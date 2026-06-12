"""Shared Groq LLM instance with crewAI cache_breakpoint workaround.

crewAI 1.14.x injects Anthropic-style `cache_breakpoint` markers into
system messages. Groq rejects them. The monkeypatch below disables the
marker globally before any LLM is constructed.

Source: https://github.com/crewAIInc/crewAI/issues/5886
"""
import os

try:
    import crewai.llms.cache as _crewai_cache
    _crewai_cache.mark_cache_breakpoint = lambda msg: msg
except (ImportError, AttributeError):
    pass

from crewai import LLM  # noqa: E402


# Default reasoning model — used by analyzer and curator agents.
groq_llm = LLM(
    model="groq/llama-3.3-70b-versatile",
    api_key=os.getenv("GROQ_API_KEY"),
)

# Tool-calling model — Llama 3.3 70B on Groq has an intermittent bug
# wrapping tool calls in <function=...> XML tags that the API rejects.
# Llama 3.1 8B Instant handles tools reliably and has a separate, larger
# rate-limit bucket on the free tier.
groq_llm = LLM(
    model="groq/llama-3.3-70b-versatile",
    api_key=os.getenv("GROQ_API_KEY"),
    num_retries=3,
)

groq_tool_llm = LLM(
    model="groq/llama-3.1-8b-instant",
    api_key=os.getenv("GROQ_API_KEY"),
    num_retries=3,
)