---
title: SkillBridge
emoji: 🌉
colorFrom: indigo
colorTo: purple
sdk: gradio
sdk_version: 6.16.0
app_file: app.py
pinned: false
license: mit
---

# SkillBridge

JD + resume → skill gap analysis → curated course recommendations.

Paste a job description, upload your resume (PDF or DOCX), and SkillBridge extracts skills from each side, computes prioritized gaps, and recommends one online course per gap.

## Architecture

```
JD + Resume (Gradio)
       ↓
   parse_inputs        — Python; PDF/DOCX → text
       ↓
   Skills Analysis Crew                ── Crew 1
   ├── jd_analyzer       (Llama 3.3 70B)
   └── resume_analyzer   (Llama 3.3 70B)
       ↓
   calculate_gaps       — Python; 1–10 score, priority bucket
       ↓
   Course Recommendation Crew          ── Crew 2
   ├── course_researcher (Llama 3.1 8B + Serper)
   └── course_curator    (Llama 3.3 70B)
       ↓
   _ensure_one_per_gap  — Python cardinality validator
       ↓
   format_report        — Python; markdown
```

Built with crewAI Flows. Pydantic models bind structured output to each task. `@start` / `@listen` decorators orchestrate the pipeline; `SkillBridgeState` carries inputs, analysis, gaps, courses, and the final report through every step.

## Stack

- **Orchestration:** crewAI 1.14.7 with Flows
- **LLM:** Groq — Llama 3.3 70B (reasoning), Llama 3.1 8B Instant (tool calls)
- **Search:** Serper (custom `LeanSerperTool` for token-trimmed results)
- **UI:** Gradio
- **Deploy:** HuggingFace Spaces

## Run locally

```bash
git clone https://github.com/Animesh452/skillbridge.git
cd skillbridge

python -m venv .venv
source .venv/Scripts/activate   # on Windows Git Bash; use .venv/bin/activate on macOS/Linux
pip install -r requirements.txt

cp .env.example .env
# add your GROQ_API_KEY and SERPER_API_KEY to .env

python app.py
```

Open http://127.0.0.1:7860.

## Design notes

- **Model mixing.** The researcher runs on Llama 3.1 8B Instant for reliable tool-calling (Llama 3.3 70B on Groq has an intermittent `<function=...>` XML formatting bug that triggers `tool_use_failed`). The curator stays on 70B for quality judgment. The two models also have separate rate-limit buckets.
- **`cache_breakpoint` workaround.** crewAI 1.14.x injects Anthropic-style cache markers into system messages; Groq rejects them. A targeted monkeypatch in `src/skillbridge/llm.py` disables the marker.
- **Lean Serper wrapper.** The default `SerperDevTool` returns 3–5K tokens per call (full sitelinks, peopleAlsoAsk, relatedSearches). With multiple sequential searches that exceeds 8B's 6K TPM ceiling. `LeanSerperTool` returns only title, URL, and snippet for the top 5 results — ~80% smaller.
- **Python cardinality enforcement.** LLMs treat "output exactly N items" as a soft constraint. The validator in `flow.py` matches curator output to input gaps by normalized skill name, drops extras silently, and re-invokes the crew on any missing gap to guarantee output count = input count.

## Known limitations

- **Experience and seniority blind spot.** The skill model is `name + level` only. Years-of-experience and team-leadership signals from the resume aren't extracted, so a JD demanding "3+ years leading a team" against a junior resume with the same skills shows as zero gaps.
- **Skill-family grouping.** Closely related skills (LangChain, LangGraph, LangSmith) are treated as independent gaps. A future enhancement would group them by stem name in a Python post-processing step.
- **Rate limits.** Free-tier Groq has per-minute and per-day token caps. The pipeline fits comfortably under them for individual runs but heavy load will throttle.

## License

MIT.