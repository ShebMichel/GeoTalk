"""Shared backend: LLM client, debate script generation, TTS generation."""

import asyncio
import base64
import json
import os
import tempfile
from pathlib import Path

import edge_tts
from huggingface_hub import InferenceClient

HF_TOKEN = os.environ.get("HF_TOKEN", "")
TEXT_MODEL = "Qwen/Qwen2.5-72B-Instruct"
VISION_MODEL = "meta-llama/Llama-3.2-11B-Vision-Instruct"

client = InferenceClient(token=HF_TOKEN)

# Edge-TTS voice pairs for distinct speakers + chair voice
VOICE_PAIRS = {
    "core_talk": ("en-US-GuyNeural", "en-US-JennyNeural"),
    "log_doctor": ("en-GB-RyanNeural", "en-GB-SoniaNeural"),
    "field_trip": ("en-US-DavisNeural", "en-US-AriaNeural"),
}

# Chair/host voice (neutral, authoritative)
CHAIR_VOICE = "en-US-AndrewNeural"


def encode_image(image_path: str) -> str:
    """Encode image to base64, resizing if too large."""
    from PIL import Image
    import io

    img = Image.open(image_path)
    # Resize if larger than 1024px on any side (keeps API happy)
    max_dim = 1024
    if max(img.size) > max_dim:
        img.thumbnail((max_dim, max_dim), Image.LANCZOS)

    # Convert to JPEG for consistent format and smaller size
    buffer = io.BytesIO()
    img_format = "JPEG" if img.mode == "RGB" else "PNG"
    if img.mode == "RGBA":
        img_format = "PNG"
    elif img.mode != "RGB":
        img = img.convert("RGB")
        img_format = "JPEG"
    img.save(buffer, format=img_format, quality=85)
    return base64.b64encode(buffer.getvalue()).decode("utf-8")


def describe_image(image_path: str, context: str) -> str:
    """Use vision model to describe an uploaded image."""
    from PIL import Image

    b64 = encode_image(image_path)

    # Determine mime based on what encode_image outputs
    img = Image.open(image_path)
    if img.mode == "RGBA":
        mime = "image/png"
    else:
        mime = "image/jpeg"

    response = client.chat_completion(
        model=VISION_MODEL,
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}},
                    {"type": "text", "text": context},
                ],
            }
        ],
        max_tokens=500,
    )
    return response.choices[0].message.content


def generate_debate_script(system_prompt: str, user_prompt: str) -> list[dict]:
    """Generate a debate script as a list of {speaker, line} dicts."""
    response = client.chat_completion(
        model=TEXT_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        max_tokens=2000,
    )
    raw = response.choices[0].message.content
    # Extract JSON from response
    try:
        start = raw.index("[")
        end = raw.rindex("]") + 1
        script = json.loads(raw[start:end])
    except (ValueError, json.JSONDecodeError):
        # Fallback: treat as plain text conversation
        script = [{"speaker": "Narrator", "line": raw}]
    return script


async def _generate_tts(text: str, voice: str, output_path: str):
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(output_path)


def _run_async(coro):
    """Run a coroutine from a sync context, safe even when called from a worker thread."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def _get_audio_duration(audio_path: str) -> float:
    """Estimate MP3 duration in seconds from file size and bitrate.
    Edge-TTS outputs ~48kbps MP3. Falls back to word-count estimate.
    """
    try:
        file_size = os.path.getsize(audio_path)
        # Edge-TTS uses ~48kbps audio; duration ≈ file_size / (bitrate/8)
        duration = file_size / (48000 / 8)
        return max(duration, 0.5)
    except OSError:
        return 3.0  # fallback


def generate_audio_for_script(script: list[dict], mode: str) -> list[dict]:
    """Generate TTS audio files for each line in the script.
    Returns list of {speaker, line, audio_path, duration, speakerIdx} dicts.
    speakerIdx: 0=left, 1=right, 2=chair/center
    """
    voice_a, voice_b = VOICE_PAIRS.get(mode, VOICE_PAIRS["core_talk"])
    speakers = list(dict.fromkeys(item["speaker"] for item in script))

    # First speaker is the Chair (idx 2), next two are the debaters (idx 0, 1)
    voice_map = {}
    speaker_idx_map = {}
    debater_count = 0
    for speaker in speakers:
        if "chair" in speaker.lower() or "host" in speaker.lower() or "moderator" in speaker.lower():
            voice_map[speaker] = CHAIR_VOICE
            speaker_idx_map[speaker] = 2  # center/chair
        else:
            voice_map[speaker] = voice_a if debater_count % 2 == 0 else voice_b
            speaker_idx_map[speaker] = debater_count % 2
            debater_count += 1

    tmp_dir = tempfile.mkdtemp(prefix="geotalk_")
    results = []

    for i, item in enumerate(script):
        audio_path = os.path.join(tmp_dir, f"line_{i:03d}.mp3")
        voice = voice_map.get(item["speaker"], voice_a)
        _run_async(_generate_tts(item["line"], voice, audio_path))
        duration = _get_audio_duration(audio_path)
        results.append({
            "speaker": item["speaker"],
            "line": item["line"],
            "audio_path": audio_path,
            "duration": duration,
            "speakerIdx": speaker_idx_map.get(item["speaker"], 0),
        })

    return results


def combine_audio_files(results: list[dict]) -> str:
    """Concatenate all MP3 files into a single file."""
    tmp_dir = tempfile.mkdtemp(prefix="geotalk_combined_")
    combined_path = os.path.join(tmp_dir, "full_episode.mp3")
    with open(combined_path, "wb") as outfile:
        for item in results:
            with open(item["audio_path"], "rb") as infile:
                outfile.write(infile.read())
    return combined_path


def format_transcript(results: list[dict]) -> str:
    """Format the debate as a readable transcript."""
    lines = []
    for item in results:
        lines.append(f"**{item['speaker']}:** {item['line']}")
    return "\n\n".join(lines)
