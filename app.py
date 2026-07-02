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

# --- Load the robot viewer HTML template ---
ROBOT_HTML_PATH = Path(__file__).parent / "robot_viewer.html"
ROBOT_HTML = ROBOT_HTML_PATH.read_text(encoding="utf-8")

# --- PROMPTS ---

CORE_TALK_SYSTEM = """You are a scriptwriter for a geoscience podcast called "Core Talk".
Write a debate between two petrographers examining a rock core/thin section:
- Dr. Elena Vasquez: sequence stratigrapher, focuses on depositional environments and facies
- Dr. Marcus Chen: structural/diagenetic specialist, focuses on post-depositional alteration

They should debate the interpretation of what they observe, respectfully disagree on key points,
and arrive at a partial consensus. Keep it educational, engaging, and scientifically accurate.

Return ONLY a JSON array of objects with "speaker" and "line" keys. 8-12 exchanges total.
Example: [{"speaker": "Dr. Elena Vasquez", "line": "Looking at this core..."}, ...]"""

LOG_DOCTOR_SYSTEM = """You are a scriptwriter for a geoscience podcast called "Log Doctor".
Write a consultation between two well log analysts diagnosing a formation like doctors diagnosing a patient:
- Dr. Resistivity (Dr. R): senior petrophysicist, speaks in medical metaphors, focuses on resistivity and porosity
- Dr. Gamma (Dr. G): sedimentologist-turned-log-analyst, focuses on lithology indicators and GR patterns

They discuss the well log data like a medical case: the formation is the "patient", anomalies are "symptoms",
and their interpretation is the "diagnosis". They should identify pay zones, fluid contacts, and lithology.

Return ONLY a JSON array of objects with "speaker" and "line" keys. 8-12 exchanges total.
Example: [{"speaker": "Dr. Resistivity", "line": "The patient presents with..."}, ...]"""

FIELD_TRIP_SYSTEM = """You are a scriptwriter for a geoscience podcast called "Field Trip FM".
Write a narrated virtual field trip between:
- Prof. Hawkins: enthusiastic geology professor, loves storytelling, connects outcrops to Earth history
- Sam: curious grad student, asks insightful questions, makes pop-culture analogies

They're standing in front of an outcrop and discussing what they see, the geological history it records,
and what processes formed it. Prof. Hawkins teaches while Sam asks questions and makes observations.

Return ONLY a JSON array of objects with "speaker" and "line" keys. 8-12 exchanges total.
Example: [{"speaker": "Prof. Hawkins", "line": "Now Sam, look at this beautiful exposure..."}, ...]"""


# --- Robot HTML Helpers ---


def get_robot_idle_html(message="Waiting for episode..."):
    """Return the robot viewer in idle state."""
    return f"""<div style="width:100%;border-radius:12px;overflow:hidden;">
<iframe id="robot-frame" srcdoc='{ROBOT_HTML.replace(chr(39), "&#39;")}' 
    style="width:100%;height:520px;border:none;border-radius:12px;" 
    sandbox="allow-scripts allow-same-origin"></iframe>
</div>"""


def get_robot_live_html(results: list[dict], audio_path: str) -> str:
    """Return robot viewer HTML with audio embedded and auto-play on load."""
    # Build timeline data
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

    speaker_names = sorted(speakers_seen.keys(), key=lambda s: speakers_seen[s])
    speaker_a = speaker_names[0] if len(speaker_names) > 0 else "Speaker A"
    speaker_b = speaker_names[1] if len(speaker_names) > 1 else "Speaker B"

    # Encode audio as base64 data URI for embedding in iframe
    with open(audio_path, "rb") as f:
        audio_b64 = base64.b64encode(f.read()).decode("utf-8")
    audio_data_uri = f"data:audio/mpeg;base64,{audio_b64}"

    js_data = json.dumps(timeline_data)

    # Inject auto-start script
    auto_start_script = f"""
<script>
window.addEventListener('load', function() {{
    setTimeout(function() {{
        if (window.GeoTalkRobots) {{
            window.GeoTalkRobots.start(
                {js_data},
                "{speaker_a}",
                "{speaker_b}",
                "{audio_data_uri}"
            );
        }}
    }}, 600);
}});
</script>
</body>"""

    modified_html = ROBOT_HTML.replace("</body>", auto_start_script)

    return f"""<div style="width:100%;border-radius:12px;overflow:hidden;">
<iframe id="robot-frame" srcdoc='{modified_html.replace(chr(39), "&#39;")}' 
    style="width:100%;height:520px;border:none;border-radius:12px;" 
    sandbox="allow-scripts allow-same-origin"></iframe>
</div>"""


# --- TAB FUNCTIONS ---


def run_core_talk(image):
    if image is None:
        return "Please upload a core or thin section image.", get_robot_idle_html()

    yield "🔬 Analyzing core image with AI vision...", get_robot_idle_html()

    description = describe_image(
        image,
        "Describe this geological core or thin section image in detail. "
        "Focus on: lithology, texture, grain size, sorting, visible structures "
        "(laminations, fractures, fossils), color variations, and any diagenetic features.",
    )

    yield f"📝 Generating debate script...\n\n*Image analysis:* {description[:200]}...", get_robot_idle_html()

    script = generate_debate_script(
        CORE_TALK_SYSTEM,
        f"The two petrographers are examining a core sample. Here is an AI-generated description of what they see:\n\n{description}\n\nWrite their debate about the interpretation.",
    )

    yield "🎙️ Generating audio narration...", get_robot_idle_html()

    results = generate_audio_for_script(script, "core_talk")
    audio_path = combine_audio_files(results)
    transcript = format_transcript(results)

    # Build the live robot viewer with embedded audio
    robot_html = get_robot_live_html(results, audio_path)
    yield transcript, robot_html


def run_log_doctor(las_file):
    if las_file is None:
        return "Please upload a LAS file.", get_robot_idle_html()

    yield "📊 Parsing LAS file...", get_robot_idle_html()

    las = lasio.read(las_file.name)

    # Summarize curves
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

    yield f"📋 Log summary:\n{curve_summary}\n\n🩺 Generating diagnosis...", get_robot_idle_html()

    script = generate_debate_script(
        LOG_DOCTOR_SYSTEM,
        f"The two log doctors are examining this well log data:\n\n{curve_summary}\n\nWrite their medical-style consultation about what the logs reveal about the formation.",
    )

    yield "🎙️ Generating audio narration...", get_robot_idle_html()

    results = generate_audio_for_script(script, "log_doctor")
    audio_path = combine_audio_files(results)
    transcript = format_transcript(results)

    robot_html = get_robot_live_html(results, audio_path)
    yield transcript, robot_html


def run_field_trip(image):
    if image is None:
        return "Please upload an outcrop photo.", get_robot_idle_html()

    yield "🏔️ Analyzing outcrop with AI vision...", get_robot_idle_html()

    description = describe_image(
        image,
        "Describe this geological outcrop photo in detail. "
        "Focus on: rock types visible, bedding orientation, fold structures, faults, "
        "weathering patterns, vegetation clues, scale indicators, and overall geological setting.",
    )

    yield f"📝 Generating field trip narration...\n\n*Outcrop analysis:* {description[:200]}...", get_robot_idle_html()

    script = generate_debate_script(
        FIELD_TRIP_SYSTEM,
        f"Prof. Hawkins and Sam are standing in front of this outcrop. Here is an AI description of what they see:\n\n{description}\n\nWrite their field trip conversation.",
    )

    yield "🎙️ Generating audio narration...", get_robot_idle_html()

    results = generate_audio_for_script(script, "field_trip")
    audio_path = combine_audio_files(results)
    transcript = format_transcript(results)

    robot_html = get_robot_live_html(results, audio_path)
    yield transcript, robot_html


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
                core_robots = gr.HTML(value=get_robot_idle_html(), label="🤖 GeoTalk Live")
        core_btn.click(run_core_talk, inputs=core_image, outputs=[core_status, core_robots])

    with gr.Tab("🩺 Log Doctor"):
        gr.Markdown("*Two log analysts diagnose your formation like doctors diagnosing a patient.*")
        with gr.Row():
            with gr.Column(scale=1):
                las_input = gr.File(label="Upload LAS file", file_types=[".las", ".LAS"])
                log_btn = gr.Button("🩺 Run Consultation", variant="primary")
                log_status = gr.Markdown(label="Status")
            with gr.Column(scale=2):
                log_robots = gr.HTML(value=get_robot_idle_html(), label="🤖 GeoTalk Live")
        log_btn.click(run_log_doctor, inputs=las_input, outputs=[log_status, log_robots])

    with gr.Tab("🏕️ Field Trip FM"):
        gr.Markdown("*A professor and student narrate a virtual field trip to your outcrop.*")
        with gr.Row():
            with gr.Column(scale=1):
                outcrop_image = gr.Image(type="filepath", label="Upload outcrop photo")
                field_btn = gr.Button("🎒 Start Field Trip", variant="primary")
                field_status = gr.Markdown(label="Status")
            with gr.Column(scale=2):
                field_robots = gr.HTML(value=get_robot_idle_html(), label="🤖 GeoTalk Live")
        field_btn.click(run_field_trip, inputs=outcrop_image, outputs=[field_status, field_robots])

    gr.Markdown(
        "---\n*Powered by Llama 3.2 Vision + Llama 3.1 + Edge-TTS on Hugging Face 🤗*\n"
        "*Robot avatars inspired by [Reachy Mini](https://huggingface.co/spaces/build-small-hackathon/small-talk) — animated with three.js*"
    )

if __name__ == "__main__":
    app.launch()
