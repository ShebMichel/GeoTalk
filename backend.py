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
VISION_MODEL = "CohereLabs/aya-vision-32b"

client = InferenceClient(token=HF_TOKEN)

# Edge-TTS voice pairs for distinct speakers
VOICE_PAIRS = {
    "core_talk": ("en-US-GuyNeural", "en-US-JennyNeural"),
    "log_doctor": ("en-GB-RyanNeural", "en-GB-SoniaNeural"),
    "field_trip": ("en-US-DavisNeural", "en-US-AriaNeural"),
}


def encode_image(image_path: str) -> str:
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def describe_image(image_path: str, context: str) -> str:
    """Use vision model to describe an uploaded image."""
    b64 = encode_image(image_path)
    ext = Path(image_path).suffix.lower().strip(".")
    mime = f"image/{'jpeg' if ext in ('jpg', 'jpeg') else ext}"

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
    """
    voice_a, voice_b = VOICE_PAIRS.get(mode, VOICE_PAIRS["core_talk"])
    speakers = list(dict.fromkeys(item["speaker"] for item in script))
    voice_map = {}
    speaker_idx_map = {}
    for i, speaker in enumerate(speakers):
        voice_map[speaker] = voice_a if i % 2 == 0 else voice_b
        speaker_idx_map[speaker] = i % 2  # 0 = left robot, 1 = right robot

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
