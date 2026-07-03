"""GeoTalk: AI-Generated Geoscience Debate Podcast"""

import base64
import json
from pathlib import Path

import gradio as gr
import lasio
import numpy as np

from backend import (
    combine_audio_files,
    describe_image,
    format_transcript,
    generate_audio_for_script,
    generate_debate_script,
)

# --- PROMPTS ---

CORE_TALK_SYSTEM = """You are a scriptwriter for a geoscience podcast called "Core Talk".
Write a debate between two petrographers examining a rock core/thin section, moderated by a chair.

Characters:
- The Chair: professional moderator who opens by introducing the topic and both speakers, then occasionally guides the discussion
- Dr. Elena Vasquez: sequence stratigrapher, focuses on depositional environments and facies
- Dr. Marcus Chen: structural/diagenetic specialist, focuses on post-depositional alteration

The Chair should open with a brief introduction (1-2 lines), introduce both speakers and the sample,
then let them debate. The Chair may interject once mid-way to steer the discussion or ask a probing question,
and closes with a brief wrap-up. The debaters should respectfully disagree on key points and arrive at a partial consensus.

Return ONLY a JSON array of objects with "speaker" and "line" keys. 10-14 exchanges total.
Example: [{"speaker": "The Chair", "line": "Welcome to Core Talk..."}, {"speaker": "Dr. Elena Vasquez", "line": "Looking at this core..."}, ...]"""

LOG_DOCTOR_SYSTEM = """You are a scriptwriter for a geoscience podcast called "Log Doctor".
Write a consultation between two well log analysts, moderated by a chair.

Characters:
- The Chair: professional moderator who opens by introducing the case and both specialists, guides the consultation
- Dr. Resistivity (Dr. R): senior petrophysicist, speaks in medical metaphors, focuses on resistivity and porosity
- Dr. Gamma (Dr. G): sedimentologist-turned-log-analyst, focuses on lithology indicators and GR patterns

The Chair opens by presenting the "patient" (the formation) and introducing the two doctors.
They discuss the well log data like a medical case: anomalies are "symptoms", interpretation is the "diagnosis".
The Chair may ask a clarifying question mid-way and wraps up with the final diagnosis summary.

Return ONLY a JSON array of objects with "speaker" and "line" keys. 10-14 exchanges total.
Example: [{"speaker": "The Chair", "line": "Welcome doctors, we have an interesting case today..."}, {"speaker": "Dr. Resistivity", "line": "The patient presents with..."}, ...]"""

FIELD_TRIP_SYSTEM = """You are a scriptwriter for a geoscience podcast called "Field Trip FM".
Write a narrated virtual field trip, moderated by a chair.

Characters:
- The Chair: podcast host who introduces the episode, the location, and both guests before handing over
- Prof. Hawkins: enthusiastic geology professor, loves storytelling, connects outcrops to Earth history
- Sam: curious grad student, asks insightful questions, makes pop-culture analogies

The Chair opens with a brief welcome, sets the scene (location, geological context), introduces Prof. Hawkins and Sam,
then lets them explore. The Chair may pop in once to ask "what should our listeners look for?" and closes the episode.

Return ONLY a JSON array of objects with "speaker" and "line" keys. 10-14 exchanges total.
Example: [{"speaker": "The Chair", "line": "Welcome to Field Trip FM! Today we're at..."}, {"speaker": "Prof. Hawkins", "line": "Now Sam, look at this beautiful exposure..."}, ...]"""


# --- Build the live viewer HTML ---

VIEWER_TEMPLATE = Path(__file__).parent / "robot_viewer.html"


def build_live_viewer(results: list[dict], audio_path: str) -> str:
    """Build a self-contained HTML viewer with embedded audio and timeline."""
    # Build timeline
    timeline_data = []
    speakers_seen = {}
    for item in results:
        timeline_data.append({
            "speaker": item["speaker"],
            "line": item["line"],
            "duration": item.get("duration", 3.0),
            "speakerIdx": item.get("speakerIdx", 0),
        })
        if item["speaker"] not in speakers_seen:
            speakers_seen[item["speaker"]] = item.get("speakerIdx", len(speakers_seen))

    # Get debater names (idx 0 and 1), skip chair (idx 2)
    speaker_a = "Speaker A"
    speaker_b = "Speaker B"
    for name, idx in speakers_seen.items():
        if idx == 0:
            speaker_a = name
        elif idx == 1:
            speaker_b = name

    # Encode audio
    with open(audio_path, "rb") as f:
        audio_b64 = base64.b64encode(f.read()).decode("utf-8")

    timeline_json = json.dumps(timeline_data)

    # Read the viewer template and inject data
    viewer_html = VIEWER_TEMPLATE.read_text(encoding="utf-8")

    # Replace placeholders
    viewer_html = viewer_html.replace("__TIMELINE_DATA__", timeline_json)
    viewer_html = viewer_html.replace("__SPEAKER_A__", speaker_a)
    viewer_html = viewer_html.replace("__SPEAKER_B__", speaker_b)
    viewer_html = viewer_html.replace("__AUDIO_B64__", audio_b64)

    # Wrap in iframe (srcdoc) — this ensures scripts execute on every update
    # Escape for srcdoc attribute
    escaped = viewer_html.replace("&", "&amp;").replace('"', "&quot;")
    return f'<iframe srcdoc="{escaped}" style="width:100%;height:650px;border:none;border-radius:12px;" allow="autoplay"></iframe>'


def get_idle_viewer() -> str:
    """Return a simple idle state."""
    return """<div style="width:100%;height:650px;border-radius:12px;background:linear-gradient(135deg,#1a1a2e,#16213e,#0f3460);display:flex;align-items:center;justify-content:center;flex-direction:column;gap:16px;">
<div style="font-size:48px;">🤖🎙️🤖</div>
<div style="color:rgba(255,255,255,0.7);font-size:16px;font-family:system-ui;">Upload data and click Generate to start GeoTalk Live</div>
</div>"""


# --- TAB FUNCTIONS ---


def run_core_talk(image):
    if image is None:
        return "Please upload a core or thin section image.", get_idle_viewer()

    yield "🔬 Analyzing core image with AI vision...", get_idle_viewer()

    try:
        description = describe_image(
            image,
            "Describe this geological core or thin section image in detail. "
            "Focus on: lithology, texture, grain size, sorting, visible structures "
            "(laminations, fractures, fossils), color variations, and any diagenetic features.",
        )
    except Exception as e:
        yield f"❌ Vision model error: {e}", get_idle_viewer()
        return

    yield f"📝 Generating debate script...\n\n*Image analysis:* {description[:200]}...", get_idle_viewer()

    try:
        script = generate_debate_script(
            CORE_TALK_SYSTEM,
            f"The two petrographers are examining a core sample. Here is an AI-generated description of what they see:\n\n{description}\n\nWrite their debate about the interpretation.",
        )
    except Exception as e:
        yield f"❌ Script generation error: {e}", get_idle_viewer()
        return

    yield "🎙️ Generating audio narration...", get_idle_viewer()

    try:
        results = generate_audio_for_script(script, "core_talk")
        audio_path = combine_audio_files(results)
        transcript = format_transcript(results)
        viewer_html = build_live_viewer(results, audio_path)
    except Exception as e:
        yield f"❌ Audio generation error: {e}", get_idle_viewer()
        return

    yield transcript, viewer_html


def run_log_doctor(las_file):
    if las_file is None:
        return "Please upload a LAS file.", get_idle_viewer()

    yield "📊 Parsing LAS file...", get_idle_viewer()

    try:
        las = lasio.read(las_file.name)
    except Exception as e:
        yield f"❌ LAS parsing error: {e}", get_idle_viewer()
        return

    summary_lines = [f"**Well:** {las.well.WELL.value if hasattr(las.well, 'WELL') else 'Unknown'}"]
    summary_lines.append(f"**Depth range:** {las.index[0]:.1f} - {las.index[-1]:.1f} {las.index_unit}")
    summary_lines.append(f"**Curves:** {', '.join(las.keys())}")

    for curve in las.curves:
        data = curve.data[~np.isnan(curve.data)] if len(curve.data) > 0 else curve.data
        if len(data) > 0:
            summary_lines.append(
                f"- **{curve.mnemonic}** ({curve.unit}): min={data.min():.2f}, max={data.max():.2f}, mean={data.mean():.2f}"
            )

    curve_summary = "\n".join(summary_lines)

    yield f"📋 Log summary:\n{curve_summary}\n\n🩺 Generating diagnosis...", get_idle_viewer()

    try:
        script = generate_debate_script(
            LOG_DOCTOR_SYSTEM,
            f"The two log doctors are examining this well log data:\n\n{curve_summary}\n\nWrite their medical-style consultation about what the logs reveal about the formation.",
        )
    except Exception as e:
        yield f"❌ Script generation error: {e}", get_idle_viewer()
        return

    yield "🎙️ Generating audio narration...", get_idle_viewer()

    try:
        results = generate_audio_for_script(script, "log_doctor")
        audio_path = combine_audio_files(results)
        transcript = format_transcript(results)
        viewer_html = build_live_viewer(results, audio_path)
    except Exception as e:
        yield f"❌ Audio generation error: {e}", get_idle_viewer()
        return

    yield transcript, viewer_html


def run_field_trip(image):
    if image is None:
        return "Please upload an outcrop photo.", get_idle_viewer()

    yield "🏔️ Analyzing outcrop with AI vision...", get_idle_viewer()

    try:
        description = describe_image(
            image,
            "Describe this geological outcrop photo in detail. "
            "Focus on: rock types visible, bedding orientation, fold structures, faults, "
            "weathering patterns, vegetation clues, scale indicators, and overall geological setting.",
        )
    except Exception as e:
        yield f"❌ Vision model error: {e}", get_idle_viewer()
        return

    yield f"📝 Generating field trip narration...\n\n*Outcrop analysis:* {description[:200]}...", get_idle_viewer()

    try:
        script = generate_debate_script(
            FIELD_TRIP_SYSTEM,
            f"Prof. Hawkins and Sam are standing in front of this outcrop. Here is an AI description of what they see:\n\n{description}\n\nWrite their field trip conversation.",
        )
    except Exception as e:
        yield f"❌ Script generation error: {e}", get_idle_viewer()
        return

    yield "🎙️ Generating audio narration...", get_idle_viewer()

    try:
        results = generate_audio_for_script(script, "field_trip")
        audio_path = combine_audio_files(results)
        transcript = format_transcript(results)
        viewer_html = build_live_viewer(results, audio_path)
    except Exception as e:
        yield f"❌ Audio generation error: {e}", get_idle_viewer()
        return

    yield transcript, viewer_html


# --- GRADIO UI ---

with gr.Blocks(title="GeoTalk 🌍🎙️", theme=gr.themes.Soft()) as app:
    gr.Markdown(
        """# 🌍🎙️ GeoTalk — AI Geoscience Debate Podcast
Upload geological data and watch AI geoscientists debate the interpretation live!
        """
    )

    with gr.Tab("🔬 Core Talk"):
        gr.Markdown("*Two petrographers debate your core/thin section.*")
        with gr.Row():
            with gr.Column(scale=1):
                core_image = gr.Image(type="filepath", label="Upload core or thin section photo")
                core_btn = gr.Button("🎬 Generate Debate", variant="primary")
                core_status = gr.Markdown(label="Status")
            with gr.Column(scale=2):
                core_viewer = gr.HTML(value=get_idle_viewer(), label="🤖 GeoTalk Live")
        core_btn.click(run_core_talk, inputs=core_image, outputs=[core_status, core_viewer])

    with gr.Tab("🩺 Log Doctor"):
        gr.Markdown("*Two log analysts diagnose your formation like doctors diagnosing a patient.*")
        with gr.Row():
            with gr.Column(scale=1):
                las_input = gr.File(label="Upload LAS file", file_types=[".las", ".LAS"])
                log_btn = gr.Button("🩺 Run Consultation", variant="primary")
                log_status = gr.Markdown(label="Status")
            with gr.Column(scale=2):
                log_viewer = gr.HTML(value=get_idle_viewer(), label="🤖 GeoTalk Live")
        log_btn.click(run_log_doctor, inputs=las_input, outputs=[log_status, log_viewer])

    with gr.Tab("🏕️ Field Trip FM"):
        gr.Markdown("*A professor and student narrate a virtual field trip to your outcrop.*")
        with gr.Row():
            with gr.Column(scale=1):
                outcrop_image = gr.Image(type="filepath", label="Upload outcrop photo")
                field_btn = gr.Button("🎒 Start Field Trip", variant="primary")
                field_status = gr.Markdown(label="Status")
            with gr.Column(scale=2):
                field_viewer = gr.HTML(value=get_idle_viewer(), label="🤖 GeoTalk Live")
        field_btn.click(run_field_trip, inputs=outcrop_image, outputs=[field_status, field_viewer])

    gr.Markdown(
        "---\n*Powered by Llama 3.2 Vision + Llama 3.1 + Edge-TTS on Hugging Face 🤗*\n"
        "*Robot avatars inspired by [Reachy Mini](https://huggingface.co/spaces/build-small-hackathon/small-talk) — animated with three.js*"
    )

if __name__ == "__main__":
    app.launch()
