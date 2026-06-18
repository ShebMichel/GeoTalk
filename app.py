"""GeoTalk: AI-Generated Geoscience Debate Podcast"""

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


# --- TAB FUNCTIONS ---


def run_core_talk(image):
    if image is None:
        return None, "Please upload a core or thin section image."

    yield None, "🔬 Analyzing core image with AI vision..."

    description = describe_image(
        image,
        "Describe this geological core or thin section image in detail. "
        "Focus on: lithology, texture, grain size, sorting, visible structures "
        "(laminations, fractures, fossils), color variations, and any diagenetic features.",
    )

    yield None, f"📝 Vision description complete. Generating debate script...\n\n*Image analysis:* {description[:200]}..."

    script = generate_debate_script(
        CORE_TALK_SYSTEM,
        f"The two petrographers are examining a core sample. Here is an AI-generated description of what they see:\n\n{description}\n\nWrite their debate about the interpretation.",
    )

    yield None, "🎙️ Generating audio narration..."

    results = generate_audio_for_script(script, "core_talk")
    audio_path = combine_audio_files(results)
    transcript = format_transcript(results)

    yield audio_path, transcript


def run_log_doctor(las_file):
    if las_file is None:
        return None, "Please upload a LAS file."

    yield None, "📊 Parsing LAS file..."

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

    yield None, f"📋 Log summary:\n{curve_summary}\n\n🩺 Generating diagnosis..."

    script = generate_debate_script(
        LOG_DOCTOR_SYSTEM,
        f"The two log doctors are examining this well log data:\n\n{curve_summary}\n\nWrite their medical-style consultation about what the logs reveal about the formation.",
    )

    yield None, "🎙️ Generating audio narration..."

    results = generate_audio_for_script(script, "log_doctor")
    audio_path = combine_audio_files(results)
    transcript = format_transcript(results)

    yield audio_path, transcript


def run_field_trip(image):
    if image is None:
        return None, "Please upload an outcrop photo."

    yield None, "🏔️ Analyzing outcrop with AI vision..."

    description = describe_image(
        image,
        "Describe this geological outcrop photo in detail. "
        "Focus on: rock types visible, bedding orientation, fold structures, faults, "
        "weathering patterns, vegetation clues, scale indicators, and overall geological setting.",
    )

    yield None, f"📝 Vision description complete. Generating field trip narration...\n\n*Outcrop analysis:* {description[:200]}..."

    script = generate_debate_script(
        FIELD_TRIP_SYSTEM,
        f"Prof. Hawkins and Sam are standing in front of this outcrop. Here is an AI description of what they see:\n\n{description}\n\nWrite their field trip conversation.",
    )

    yield None, "🎙️ Generating audio narration..."

    results = generate_audio_for_script(script, "field_trip")
    audio_path = combine_audio_files(results)
    transcript = format_transcript(results)

    yield audio_path, transcript


# --- GRADIO UI ---

with gr.Blocks(title="GeoTalk 🌍🎙️", theme=gr.themes.Soft()) as app:
    gr.Markdown(
        """# 🌍🎙️ GeoTalk — AI Geoscience Debate Podcast
        Upload geological data and listen to AI geoscientists debate the interpretation.
        """
    )

    with gr.Tab("🔬 Core Talk"):
        gr.Markdown("*Two petrographers debate your core/thin section.*")
        with gr.Row():
            with gr.Column():
                core_image = gr.Image(type="filepath", label="Upload core or thin section photo")
                core_btn = gr.Button("🎬 Generate Debate", variant="primary")
            with gr.Column():
                core_audio = gr.Audio(label="Episode Audio", type="filepath")
                core_transcript = gr.Markdown(label="Transcript")
        core_btn.click(run_core_talk, inputs=core_image, outputs=[core_audio, core_transcript])

    with gr.Tab("🩺 Log Doctor"):
        gr.Markdown("*Two log analysts diagnose your formation like doctors diagnosing a patient.*")
        with gr.Row():
            with gr.Column():
                las_input = gr.File(label="Upload LAS file", file_types=[".las", ".LAS"])
                log_btn = gr.Button("🩺 Run Consultation", variant="primary")
            with gr.Column():
                log_audio = gr.Audio(label="Episode Audio", type="filepath")
                log_transcript = gr.Markdown(label="Transcript")
        log_btn.click(run_log_doctor, inputs=las_input, outputs=[log_audio, log_transcript])

    with gr.Tab("🏕️ Field Trip FM"):
        gr.Markdown("*A professor and student narrate a virtual field trip to your outcrop.*")
        with gr.Row():
            with gr.Column():
                outcrop_image = gr.Image(type="filepath", label="Upload outcrop photo")
                field_btn = gr.Button("🎒 Start Field Trip", variant="primary")
            with gr.Column():
                field_audio = gr.Audio(label="Episode Audio", type="filepath")
                field_transcript = gr.Markdown(label="Transcript")
        field_btn.click(run_field_trip, inputs=outcrop_image, outputs=[field_audio, field_transcript])

    gr.Markdown("---\n*Powered by Llama 3.2 Vision + Llama 3.1 + Edge-TTS on Hugging Face 🤗*")

if __name__ == "__main__":
    app.launch()
