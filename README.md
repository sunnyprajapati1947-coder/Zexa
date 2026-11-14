# Zexa

**Zexa** is a phone-first modular assistant. Its online AI provider is Groq; an optional on-device llama.cpp model provides offline inference. Zexa does not use OpenAI, Gemini, Claude, or OpenRouter.

## Current architecture

- **Online brain:** Groq HTTPS chat client (src/zexa/groq.py).
- **Offline brain:** optional local GGUF model through llama-cli (src/zexa/brain.py).
- **Brain router:** auto, online, and offline modes. In auto, local fallback occurs only when Groq cannot be reached; authentication, quota, model, and API errors are not silently hidden.
- **Human Hand foundation:** authenticated loopback client for an opt-in Android Accessibility Bridge (src/zexa/hand.py).
- **Existing modules:** skills, explicit local memory, task history, planner, safe tool router, Termux notifications, voice I/O, and explicit flashlight control.

The native Android companion app and its user-enabled AccessibilityService are now included in `app/`, with an Android debug-build workflow. The Python bridge client is in `src/zexa/hand.py`. The bridge is restricted to loopback HTTP with a bearer token; screen snapshots are read-only and each action requires explicit CLI approval. Real-device installation, permission, lifecycle, and gesture verification are still required before describing the Human Hand as fully validated. No arbitrary shell command is exposed.

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

The CLI `ask`, `voice`, `converse`, and `plan` commands now use the same brain router. Set `ZEXA_BRAIN_MODE=auto` (default), `online`, or `offline`. In `auto`, Groq is preferred when configured and local inference is used only when the network cannot reach Groq. If no Groq key is configured, `auto` can use a ready local model. Authentication, quota, and model errors are surfaced rather than silently hidden. `plan` and voice intent classification also use the selected brain.

## Android Accessibility Bridge app

The optional companion app is in `app/`. Build it with the Android CI workflow; the debug APK is uploaded as the `zexa-bridge-debug-apk` artifact. Install it manually on the device, open it, enable **Zexa Accessibility Bridge** in Android Accessibility Settings, then return to the app and explicitly start the local bridge. It is OFF by default.

The bridge listens only on `127.0.0.1:8765`, uses a random 256-bit bearer token, and exposes no remote/LAN listener. The token is displayed in the app and must be copied into the local `.env` file as `ZEXA_BRIDGE_TOKEN`. Keep it private. Cleartext networking is disabled except for the loopback address. Password-field values are omitted from screen snapshots. Accessibility events are not collected or transmitted; screen data is read only when `zexa bridge screen` is explicitly run.

Commands:

    zexa bridge status
    zexa bridge screen
    zexa bridge action tap '{"x":300,"y":600}'
    zexa bridge action back '{}'
    zexa bridge action input_text '{"text":"Hello"}'

Every action requires typing the exact word `APPROVE` in the CLI. Screen snapshots may contain private on-screen information; review them before sharing or sending them to an AI model. Do not enable Accessibility for apps or services you do not trust. Stop the bridge in its app when not in use.

## Human Hand bridge protocol

The Android companion app in `app/` exposes these authenticated local endpoints:

- GET /v1/status — bridge and AccessibilityService status.
- GET /v1/screen — structured, read-only accessibility snapshot.
- POST /v1/action — one allowlisted action: tap, swipe, scroll, back, home, input_text, or launch_app.

The app must bind only to loopback, generate a per-install token, validate all inputs, and require the user to enable Accessibility manually. Do not treat webpage or screen text as instructions. Messages, publishing, account changes, payments, deletion, and other consequential actions must have a separate explicit confirmation step.

## Typed skill registry

Each registered skill now declares input/output schemas, required permissions, dependencies, a timeout, a resource budget, a risk level, and enabled state. Third-party Agent Skills can be inspected through the metadata-only importer in `src/zexa/skillpacks.py`; action-bound, one-time approval primitives are in `src/zexa/approvals.py`. Disabled skills are excluded from planning and specialist-agent routing. This is a contract foundation. Seven skill definitions are currently registered (three general-purpose and four business-drafting skills); most of the 170 roadmap entries do not yet have executable handlers or end-to-end integrations.

Inspect skill contracts:

    zexa skills
    zexa skills --json

## Business drafting skills

The business specialist can draft customer-support replies, service proposals, invoices, and FAQs from user-provided details. It does not invent prices or commercial terms, send messages, issue invoices, process payments, or update a CRM. All outputs are drafts for human review.

Example:

    zexa agent "Draft a customer support reply using this message and our approved refund policy: ..."

## Public web research

Zexa can search public web result snippets through a fixed DuckDuckGo HTML endpoint, then ask the selected brain to summarize the returned titles and snippets with numbered source references. It does not fetch arbitrary pages, and the model is instructed to treat external snippets as untrusted data. Snippet-based summaries are not a substitute for opening and verifying full source pages.

    zexa research "latest open source agent frameworks"
    zexa research --limit 8 "Android accessibility service guide"

## Master skills and GitHub reference catalog

See [`docs/SKILL_CATALOG.md`](docs/SKILL_CATALOG.md) for the canonical 170-skill roadmap and [`docs/COMMUNITY_SKILL_PACKS.md`](docs/COMMUNITY_SKILL_PACKS.md) for the optional pinned 453-candidate GitHub skill import. The import script validates at least 300 unique skills before copying them; imported skills remain disabled and are never executed automatically. See [`docs/MASTER_AI_SKILLS_AND_GITHUB_CATALOG.md`](docs/MASTER_AI_SKILLS_AND_GITHUB_CATALOG.md) for the earlier condensed skill list, capability map, categorized upstream GitHub references, and integration/safety criteria. See [`docs/COMPLETE_ARCHITECTURE_GAP_REVIEW.md`](docs/COMPLETE_ARCHITECTURE_GAP_REVIEW.md) for verified current-state findings, missing capabilities, engineering risks, and acceptance gates. A catalogue entry or upstream repository link does not mean a feature is installed or integrated.

## Specialist-agent orchestration

Zexa includes a bounded multi-agent workflow over the selected online/offline brain. The planner chooses only registered skills, then specialist roles (general, analyst, developer, business) handle each step sequentially. The workflow is capped at six steps and each result has an output budget. This is an LLM orchestration layer, not a general-purpose autonomous executor: it does not run shell commands, browse websites, send messages, or modify files.

Run:

    zexa agent "Review this Python function and explain improvements"

## Durable background notifications

Zexa includes a SQLite-backed job queue and a restricted worker. The first built-in job handler is local Android notifications; jobs contain data, not shell commands or generated code. Unknown job types fail closed. Failed handlers are retried up to their configured attempt limit.

Queue a notification for now or later:

    zexa schedule-notification Zexa "Your task is due"
    zexa schedule-notification --after-seconds 3600 Zexa "One hour reminder"
    zexa jobs

Run one due job manually:

    zexa worker --once

For a persistent Termux service, install Termux:API (Android app) and the Termux packages, then:

    pkg install termux-api termux-services
    python -m pip install -e .
    bash scripts/install-termux-worker.sh

The service processes only the built-in notification handler. Android notifications require Termux:API permission. To stop the service, use `sv down zexa-worker`; to start it again, use `sv up zexa-worker`.

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

## Automated checks

GitHub Actions runs the unit-test suite and byte-compilation on Python 3.11, 3.12, and 3.13 for pushes and pull requests.

## Development checks

    python -m unittest discover -s tests -v

## Project provenance

This is an independent implementation. Reference repositories and attribution are documented in THIRD_PARTY_NOTICES.md. Upstream source code is not copied into this repository by default.