"""SkillBridge — Gradio UI.

Entry point for HF Spaces. Reads JD as text and resume as PDF/DOCX,
runs the SkillBridgeFlow, returns markdown + structured JSON.
"""
import sys
from pathlib import Path

import gradio as gr
from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, str(Path(__file__).parent / "src"))

from skillbridge.flow import SkillBridgeFlow

# --- File parsing -----------------------------------------------------------

def _extract_pdf(path: str) -> str:
    from pypdf import PdfReader
    reader = PdfReader(path)
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def _extract_docx(path: str) -> str:
    from docx import Document
    doc = Document(path)
    return "\n".join(p.text for p in doc.paragraphs)


def parse_resume(file_obj) -> str:
    """Gradio passes a NamedString-like object with a .name attribute."""
    if file_obj is None:
        return ""
    path = file_obj.name if hasattr(file_obj, "name") else str(file_obj)
    suffix = Path(path).suffix.lower()
    if suffix == ".pdf":
        return _extract_pdf(path)
    if suffix == ".docx":
        return _extract_docx(path)
    raise gr.Error(f"Unsupported file type: {suffix}. Use .pdf or .docx.")


# --- Flow runner ------------------------------------------------------------

def run_skillbridge(job_description: str, resume_file, progress=gr.Progress()):
    if not job_description or not job_description.strip():
        raise gr.Error("Please paste a job description.")
    if resume_file is None:
        raise gr.Error("Please upload a resume (PDF or DOCX).")

    progress(0.05, desc="Parsing resume...")
    resume_text = parse_resume(resume_file)
    if not resume_text.strip():
        raise gr.Error("Couldn't extract text from the resume. Try a different file.")

    progress(0.20, desc="Analyzing skills (Crew 1)...")
    flow = SkillBridgeFlow()
    # Crew 1 + gap calc + (30s sleep) + Crew 2 + format
    # We can't easily hook into each step without rewriting the Flow, so we
    # show a single coarse update and let crewAI's stdout panels do the rest.
    progress(0.30, desc="Running pipeline — Crew 1, then 30s cooldown, then Crew 2...")
    flow.kickoff(inputs={
        "job_description": job_description,
        "resume_text": resume_text,
    })

    progress(1.0, desc="Done.")

    # Return three outputs: report, raw gaps JSON, raw courses JSON
    gaps_json = [g.model_dump() for g in flow.state.gaps]
    courses_json = [c.model_dump() for c in flow.state.courses]
    return flow.state.report, gaps_json, courses_json


# --- UI ---------------------------------------------------------------------

SAMPLE_JD = """\
Senior ML Engineer

We're hiring an ML engineer with deep experience in PyTorch and at least
3 years building production ML systems on AWS. You'll lead a team building
LLM-powered features, so familiarity with RAG, vector databases, and prompt
engineering is required. Exposure to Kubernetes is a plus. Strong Python
required.\
"""

with gr.Blocks(title="SkillBridge", theme=gr.themes.Soft()) as demo:
    gr.Markdown(
        "# SkillBridge\n"
        "Paste a job description, upload your resume, and get a gap analysis "
        "with course recommendations. Powered by crewAI Flows + Groq."
    )

    with gr.Row():
        with gr.Column():
            jd_input = gr.Textbox(
                label="Job Description",
                lines=12,
                value=SAMPLE_JD,
                placeholder="Paste the full JD here...",
            )
            resume_input = gr.File(
                label="Resume (.pdf or .docx)",
                file_types=[".pdf", ".docx"],
                file_count="single",
            )
            run_btn = gr.Button("Analyze", variant="primary")

        with gr.Column():
            report_output = gr.Markdown(label="Report")
            with gr.Accordion("Raw gap data", open=False):
                gaps_output = gr.JSON()
            with gr.Accordion("Raw course data", open=False):
                courses_output = gr.JSON()

    run_btn.click(
        fn=run_skillbridge,
        inputs=[jd_input, resume_input],
        outputs=[report_output, gaps_output, courses_output],
    )


if __name__ == "__main__":
    demo.launch()