---
title: GeoTalk
emoji: 🚀
colorFrom: green
colorTo: yellow
sdk: gradio
sdk_version: 6.19.0
python_version: '3.13'
app_file: app.py
pinned: false
---

<div align="center">

<!-- Animated SVG Banner -->
<svg width="800" height="200" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <linearGradient id="bg" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:#1a1a2e"/>
      <stop offset="50%" style="stop-color:#16213e"/>
      <stop offset="100%" style="stop-color:#0f3460"/>
    </linearGradient>
    <linearGradient id="text-grad" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" style="stop-color:#4caf50"/>
      <stop offset="50%" style="stop-color:#4fc3f7"/>
      <stop offset="100%" style="stop-color:#9c27b0"/>
    </linearGradient>
  </defs>
  <rect width="800" height="200" rx="16" fill="url(#bg)"/>
  <text x="400" y="85" text-anchor="middle" font-family="Arial, sans-serif" font-size="48" font-weight="bold" fill="url(#text-grad)">🌍🎙️ GeoTalk</text>
  <text x="400" y="130" text-anchor="middle" font-family="Arial, sans-serif" font-size="18" fill="#e0e0e0">AI-Generated Geoscience Debate Podcast</text>
  <text x="400" y="165" text-anchor="middle" font-family="Arial, sans-serif" font-size="14" fill="#888">Powered by LLMs • Edge-TTS • Three.js Robot Avatars</text>
  <!-- Animated dots -->
  <circle cx="300" cy="180" r="3" fill="#4caf50">
    <animate attributeName="opacity" values="1;0.3;1" dur="2s" repeatCount="indefinite"/>
  </circle>
  <circle cx="400" cy="180" r="3" fill="#4fc3f7">
    <animate attributeName="opacity" values="0.3;1;0.3" dur="2s" repeatCount="indefinite"/>
  </circle>
  <circle cx="500" cy="180" r="3" fill="#9c27b0">
    <animate attributeName="opacity" values="1;0.3;1" dur="2s" repeatCount="indefinite" begin="0.5s"/>
  </circle>
</svg>

**Watch AI geoscientists debate your geological data — live, with animated robot avatars!**

[![Hugging Face Space](https://img.shields.io/badge/🤗%20Live%20Demo-GeoTalk-blue?style=for-the-badge)](https://huggingface.co/spaces/ShebMichel/GeoTalk)
[![Python](https://img.shields.io/badge/Python-3.13-green?style=flat-square&logo=python)](https://python.org)
[![Gradio](https://img.shields.io/badge/Gradio-6.19-orange?style=flat-square)](https://gradio.app)

</div>

---

## 🎬 What is GeoTalk?

GeoTalk is an AI-powered geoscience podcast generator that turns your geological data into an engaging debate between AI scientists — complete with **animated 3D robot avatars**, **text-to-speech voices**, and **live captions**.

Upload a core photo, well log, or outcrop image, and watch two AI geoscientists (plus a moderator) debate the interpretation in real-time.

<div align="center">

```
┌─────────────────────────────────────────────────────────┐
│  🎙️ GeoTalk Live                          ● LIVE       │
├─────────────┬──────────┬────────────────────────────────┤
│             │          │                                │
│   🤖 Robot A │  🎙️ Chair │   🤖 Robot B                   │
│  (Speaker 1) │(Moderator)│  (Speaker 2)                  │
│             │          │                                │
├─────────────┴──────────┴────────────────────────────────┤
│  Dr. Vasquez: "The laminations suggest a tidal flat..." │
├─────────────────────────────────────────────────────────┤
│  ⏸ ════════════════════════ 2:34 / 5:12                │
└─────────────────────────────────────────────────────────┘
```

</div>

## ✨ Features

| Feature | Description |
|---------|-------------|
| 🔬 **Core Talk** | Two petrographers debate your core/thin section photo |
| 🩺 **Log Doctor** | Two analysts diagnose your well log data (LAS files) like doctors diagnosing a patient |
| 🏕️ **Field Trip FM** | A professor and student narrate a virtual field trip to your outcrop |
| 🎙️ **Chair/Moderator** | A professional host introduces the topic, speakers, and guides the debate |
| 🤖 **3D Robot Avatars** | Reachy Mini-inspired robots animate per speaker turn (Three.js) |
| 🗣️ **Multi-voice TTS** | Each character has a distinct voice (Edge-TTS) |
| 📝 **Live Captions** | Real-time subtitles synced to audio playback |
| ▶️ **Auto-play** | Episode starts automatically when ready |

## 🏗️ Architecture

```
┌──────────────┐     ┌──────────────────┐     ┌─────────────┐
│  User Input  │────▶│  Vision Model    │────▶│  LLM Script │
│  (Image/LAS) │     │  (Qwen2.5-VL)   │     │  Generator  │
└──────────────┘     └──────────────────┘     └──────┬──────┘
                                                      │
                     ┌──────────────────┐             │
                     │   Edge-TTS       │◀────────────┘
                     │  (Multi-voice)   │
                     └────────┬─────────┘
                              │
                     ┌────────▼─────────┐
                     │  Robot Viewer    │
                     │  (Three.js +    │
                     │   Audio Sync)   │
                     └─────────────────┘
```

**Pipeline:**
1. **Vision Analysis** — Qwen2.5-VL-72B describes the uploaded geological image
2. **Script Generation** — Qwen2.5-72B writes a multi-character debate script (with Chair)
3. **Text-to-Speech** — Edge-TTS generates distinct voices for each character
4. **Live Viewer** — Three.js renders animated robots synced to audio playback

## 🚀 Quick Start

### Run locally

```bash
git clone https://github.com/ShebMichel/GeoTalk.git
cd GeoTalk
pip install -r requirements.txt
export HF_TOKEN="your_huggingface_token"
python app.py
```

### Try the live demo

👉 **[Launch GeoTalk on Hugging Face Spaces](https://huggingface.co/spaces/ShebMichel/GeoTalk)**

## 📁 Project Structure

```
GeoTalk/
├── app.py              # Gradio UI + tab functions
├── backend.py          # LLM client, TTS generation, script parsing
├── robot_viewer.html   # Three.js robot viewer (self-contained)
├── requirements.txt    # Python dependencies
└── README.md           # This file
```

## 🤖 Robot Avatars

The 3D robot avatars are inspired by [Reachy Mini](https://huggingface.co/spaces/build-small-hackathon/small-talk) from the Small Talk project. They feature:

- **Procedural Three.js geometry** — no external model files needed
- **Per-speaker animations** — talking (head bob, antenna wiggle), listening (head tilt), idle (gentle sway)
- **Visual feedback** — active speaker panel highlighted with colored border
- **Chair indicator** — center panel with pulsing microphone icon

## 🛠️ Tech Stack

- **Frontend:** Three.js, Gradio, HTML5 Audio
- **LLM:** Qwen2.5-72B-Instruct (script generation)
- **Vision:** Qwen2.5-VL-72B-Instruct (image analysis)
- **TTS:** Edge-TTS (Microsoft Neural voices)
- **Hosting:** Hugging Face Spaces

## 📄 License

MIT

---

<div align="center">
  <sub>Built with ❤️ for the geoscience community</sub>
</div>
