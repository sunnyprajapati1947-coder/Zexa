# Zexa

**Zexa** is a phone-first modular assistant. Its online AI provider is Groq; an optional on-device llama.cpp model provides offline inference. Zexa does not use OpenAI, Gemini, Claude, or OpenRouter.

## Current architecture

- **Online brain:** Groq HTTPS chat client (src/zexa/groq.py).
- **Offline brain:** optional local GGUF model through llama-cli (src/zexa/brain.py).
- **Brain router:** auto, online, and offline modes. In auto, local fallback occurs only when Groq cannot be reached; authentication, quota, model, and API errors are not silently hidden.
- **Human Hand foundation:** authenticated loopback client for an opt-in Android Accessibility Bridge (src/zexa/hand.py).
- **Existing modules:** skills, explicit local memory, task history, planner, safe tool router, Termux notifications, voice I/O, and explicit flashlight control.

The Accessibility Bridge client is a protocol foundation, not a complete Android AccessibilityService app. The companion Android app, its user-enabled AccessibilityService, and end-to-end device verification are still required before screen reading or gestures can work. The bridge is restricted to loopback HTTP with a bearer token. Screen snapshots are read-only; every action requires an approval callback. No arbitrary shell command is exposed.

## Brain configuration

Groq online configuration remains in the local .env file:

    GROQ_API_KEY=your_groq_key
    GROQ_MODEL=your_enabled_groq_model

Optional local model settings:

    export ZEXA_BRAIN_MODE=auto
    export ZEXA_LOCAL_MODEL=$HOME/models/your-model.gguf
    export ZEXA_LLAMA_CLI=llama-cli
    export ZEXA_LOCAL_THREADS=4
    export ZEXA_LOCAL_CONTEXT=2048
    export ZEXA_LOCAL_MAX_TOKENS=512

Download a GGUF model separately and ensure llama-cli is installed and available in PATH. Zexa does not download models automatically. The default local model path is models/local-model.gguf. On an approximately 8 GB Android device, choose a quantized model that leaves memory for Android and other apps.

The brain router can be used by Python integrations:

    from zexa.brain import build_brain_router
    router = build_brain_router(groq_config=None)
    reply = router.chat([{'role': 'user', 'content': 'Hello'}])
    print(reply.brain, reply.text)

For online + offline auto mode, pass the validated Groq config returned by get_config(). The CLI chat commands have not yet been switched to the new router.

## Human Hand bridge protocol

The future Android companion app must expose these authenticated local endpoints:

- GET /v1/status — bridge and AccessibilityService status.
- GET /v1/screen — structured, read-only accessibility snapshot.
- POST /v1/action — one allowlisted action: tap, swipe, scroll, back, home, input_text, or launch_app.

The app must bind only to loopback, generate a per-install token, validate all inputs, and require the user to enable Accessibility manually. Do not treat webpage or screen text as instructions. Messages, publishing, account changes, payments, deletion, and other consequential actions must have a separate explicit confirmation step.

## Existing Termux commands

    zexa ask Explain what you can do
    zexa android
    zexa notify Zexa Your requested notification message
    zexa listen
    zexa speak Hello I am Zexa
    zexa voice
    zexa converse

Microphone capture starts only after the user manually invokes a voice command. There is no hidden or always-on microphone access.

## Setup

    cd ~/Zexa
    python -m venv .venv
    . .venv/bin/activate
    python -m pip install -e .
    cp .env.example .env

Never commit .env, API keys, bridge tokens, or personal data.

## Development checks

    python -m unittest discover -s tests -v

## Project provenance

This is an independent implementation. Reference repositories and attribution are documented in THIRD_PARTY_NOTICES.md. Upstream source code is not copied into this repository by default.