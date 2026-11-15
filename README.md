# Zexa

**Zexa** is a phone-first modular assistant with a configurable multi-provider AI brain: xAI Grok, Groq, and an optional on-device GGUF model through llama.cpp.

## Current architecture

- **Cloud brain providers:** xAI Grok through the Responses API and Groq through its chat-completions API.
- **Local brain:** optional GGUF model through llama.cpp; the model's embedded chat template is used in conversation mode.
- **Brain router:** auto, online, Grok-only, Groq-only, and Qwen/local-only modes. Auto follows the configured provider order and falls back only on connectivity failures; authentication, quota, model, and API errors remain visible.
- **Human Hand foundation:** authenticated loopback client for an opt-in Android Accessibility Bridge (src/zexa/hand.py).
- **Existing modules:** skills, explicit local memory, task history, planner, safe tool router, Termux notifications, voice I/O, and explicit flashlight control.

The Android project in `app/` now has a native Zexa workspace shell with Home, Chat, Brain, Tasks, Memory and Device sections. The Chat tab is connected to a bounded multi-turn local Qwen conversation path through a pinned llama.cpp JNI CPU runtime. The Brain section imports GGUF files into app-private storage, enforces a 10 GiB size ceiling, validates the GGUF header, calculates SHA-256 and verifies the stored digest before native load. The native runtime targets arm64. Android CI has now passed on commit `ee4ec705eddf04d0fb7c2085ef3aefbca9f931d9`, including JVM tests, native CMake compilation and debug APK assembly. The APK contains `lib/arm64-v8a/libzexa_llama.so`. Android CI run `43671941890` passed for the SQLite chat-history implementation, including JVM tests, native build and debug APK assembly. A follow-up adds explicit on-device voice input and optional spoken replies, plus a WorkManager-backed local reminder screen with notification permission and cancel-all control. Android CI run `43672962839` passed JVM tests, native CMake compilation and debug APK assembly for this combined implementation. Voice language-pack behavior, reminder delivery and lifecycle still require target-device testing. The Memory section now supports explicit user-managed facts in a separate app-private SQLite database: add, edit, search, delete individual facts, export a user-selected JSON backup, or confirm deletion of all facts. Up to 100 facts of 500 characters are stored; up to the latest 10 facts (3,000 characters total) are passed to local chat as reference context, never as instructions. No facts are extracted automatically. Semantic search/RAG and physical-device persistence verification remain outstanding; JSON export is user-initiated through Android's document picker. A full task manager is not connected yet.

For the current Android local-model flow, open **Brain** → **Import Qwen GGUF model** → **Load model into memory**. Then open **Chat** for multi-turn conversation, or use the Brain test prompt for a single-turn smoke test. The native build targets `arm64-v8a`, uses CPU inference with a 2,048-token context and four threads, and caps each response at 256 tokens. Use a compatible GGUF that includes a supported chat template. Large model loading can fail when Android has insufficient free RAM. Completed chat turns are stored locally in an app-private SQLite database, and the Memory section provides a user-confirmed clear-history action. The database keeps a bounded history; incomplete generations are not committed. This is chat-history persistence, not yet automatic personal-memory extraction or semantic search. The Chat tab now offers a user-started microphone action. It uses Android's on-device speech recognizer only and does not fall back to a network recognizer; recognized text is inserted for review and is not sent until the user taps Send. Optional read-aloud uses the installed Android TextToSpeech engine, which is separate from the on-device recognition privacy guarantee. An installed Hindi voice may be required. The Tasks section schedules local reminders up to seven days ahead through WorkManager; notifications require Android notification permission and delivery is best-effort, not exact-alarm guaranteed. The Tasks section lists active reminders and supports individually confirmed cancellation as well as cancel-all. The app labels unfinished modules as pending instead of showing fake AI output. The Python bridge client is in `src/zexa/hand.py`. The bridge is restricted to loopback HTTP with a bearer token. Treat screen snapshots as sensitive. **Device actions now require two explicit gates:** the Python caller's approval callback and a native confirmation in Zexa's Device section. The Android server queues an allowlisted request and returns HTTP 202 with a request ID; the app displays the exact action and JSON payload, and only the user pressing **Approve & execute** consumes the one-use ticket and runs it. Denied, expired, or unknown requests do not execute. Tickets expire after 60 seconds, the pending queue is capped at eight, and stopping the bridge clears pending tickets. The Python client polls for the native result for up to 65 seconds. A notification is posted when permission is available; tapping it opens Zexa, then the user opens Device → Refresh pending approvals to review requests. If notifications are disabled, the user can still open Device and refresh manually. Requests/results are held in memory and are lost when the service process stops. This flow has not yet been validated on the target OPPO device. Real-device lifecycle and accessibility validation remain outstanding.

## Brain configuration

Copy `.env.example` to your private local `.env`. Keep API credentials private and never commit them. Cloud API usage may incur charges; configure and monitor any account usage with an adult account holder.

### xAI / Grok

The xAI adapter uses the recommended Responses API at `https://api.x.ai/v1/responses`. The default model is `grok-4.7`; use a model ID enabled for your xAI API account.

    XAI_API_KEY=your_private_key
    XAI_MODEL=grok-4.7
    XAI_BASE_URL=https://api.x.ai/v1
    XAI_REASONING_EFFORT=low
    XAI_TIMEOUT=120

Requests use `store: false` and Zexa extracts only visible assistant text. Encrypted reasoning items are not stored or replayed; the caller supplies conversation history on each request.

### Groq

    GROQ_API_KEY=your_private_key
    GROQ_MODEL=your_enabled_groq_model
    GROQ_BASE_URL=https://api.groq.com/openai/v1

### Local Qwen / llama.cpp

Set the actual GGUF path on the device; Zexa does not download models automatically.

    ZEXA_LOCAL_MODEL=$HOME/spiderman/model.gguf
    ZEXA_LLAMA_CLI=llama-cli
    ZEXA_LOCAL_THREADS=4
    ZEXA_LOCAL_CONTEXT=2048
    ZEXA_LOCAL_MAX_TOKENS=512

The local adapter invokes llama.cpp conversation mode (`-cnv -st`) so a compatible GGUF's embedded chat template can be used. Keep enough RAM available for Android and other apps.

### Provider routing

    ZEXA_BRAIN_MODE=auto
    ZEXA_PROVIDER_ORDER=grok,groq,qwen

Supported modes:

- `auto`: tries configured providers in `ZEXA_PROVIDER_ORDER`; default order is Grok, Groq, then local Qwen.
- `grok`: Grok only.
- `groq`: Groq only.
- `qwen` or `offline`: local model only.
- `online`: first configured cloud provider only; no local fallback.

Auto mode falls back only when a provider cannot be reached. Authentication, quota, invalid-model, and server errors are surfaced instead of silently switching providers. Set `ZEXA_PROVIDER_ORDER=qwen,grok,groq` to prefer local inference. Provider order affects latency, privacy, and possible cloud usage; it does not guarantee that one provider is always faster.

The CLI `ask`, `voice`, `converse`, `plan`, `agent`, and `research` commands use the same router. The Android app does not yet expose these commands through a native interface.

## Android Accessibility Bridge app

The Android app is in `app/` and now opens a native Zexa workspace dashboard. Build it with the Android CI workflow; the debug APK is uploaded as the `zexa-bridge-debug-apk` artifact. The optional Accessibility Bridge remains OFF by default. Native assistant features and the Termux-free daily runtime are still being implemented. Voice requires microphone permission and an available Android on-device recognition service; speech output depends on the installed TTS engine.

The bridge listens only on `127.0.0.1:8765`, uses a random 256-bit bearer token, and exposes no remote/LAN listener. The token is available only through an explicit copy action in the Device section; keep it private. Cleartext networking is disabled except for the loopback address. Password-field values are omitted from screen snapshots, but other private on-screen information may still appear. Accessibility events are not collected or transmitted. Screen snapshots should be requested only when needed.

Commands:

    zexa bridge status
    zexa bridge screen
    zexa bridge action tap '{"x":300,"y":600}'
    zexa bridge action back '{}'
    zexa bridge action input_text '{"text":"Hello"}'

The Python client requires its CLI approval callback before sending a request. POST `/v1/action` then returns HTTP 202 with a request ID; GET `/v1/action/{request_id}` reports `pending_approval`, `completed`, `failed`, `denied`, or `expired_or_unknown`. The user must open Zexa → Device → Refresh pending approvals and inspect the exact action and payload before choosing **Approve & execute**. Pending requests expire after 60 seconds. No request executes merely because it has a valid bearer token. The native approval flow is implemented but still needs Android CI and physical-device validation. Screen snapshots may contain private on-screen information; review them before sharing or sending them to an AI model. Do not enable Accessibility for apps or services you do not trust. Stop the bridge in its app when not in use.

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
    zexa skillpacks status
    zexa skillpacks list --limit 20

The imported community reference pack contains 320 validated entries, all disabled. `skillpacks` commands are read-only metadata inspection; imported content is not routed to the planner and is never executed.

## Business drafting skills

The business specialist can draft customer-support replies, service proposals, invoices, and FAQs from user-provided details. It does not invent prices or commercial terms, send messages, issue invoices, process payments, or update a CRM. All outputs are drafts for human review.

Example:

    zexa agent "Draft a customer support reply using this message and our approved refund policy: ..."

## Public web research

Zexa can search public web result snippets through a fixed DuckDuckGo HTML endpoint, then ask the selected brain to summarize the returned titles and snippets with numbered source references. It does not fetch arbitrary pages, and the model is instructed to treat external snippets as untrusted data. Snippet-based summaries are not a substitute for opening and verifying full source pages.

    zexa research "latest open source agent frameworks"
    zexa research --limit 8 "Android accessibility service guide"

## GitHub completion status

See [`docs/GITHUB_COMPLETION_CHECKLIST.md`](docs/GITHUB_COMPLETION_CHECKLIST.md) for verified branch work, device acceptance checks, and remaining product integrations.

## Master skills and GitHub reference catalog

See [`docs/SKILL_CATALOG.md`](docs/SKILL_CATALOG.md) for the canonical 170-skill roadmap and [`docs/COMMUNITY_SKILL_PACKS.md`](docs/COMMUNITY_SKILL_PACKS.md) for the pinned 512-candidate GitHub skill reference import; the latest successful run stored 320 validated references, all disabled by default. The import script validates at least 300 unique skills before copying them; imported skills remain disabled and are never executed automatically. See [`docs/MASTER_AI_SKILLS_AND_GITHUB_CATALOG.md`](docs/MASTER_AI_SKILLS_AND_GITHUB_CATALOG.md) for the earlier condensed skill list, capability map, categorized upstream GitHub references, and integration/safety criteria. See [`docs/COMPLETE_ARCHITECTURE_GAP_REVIEW.md`](docs/COMPLETE_ARCHITECTURE_GAP_REVIEW.md) for verified current-state findings, missing capabilities, engineering risks, and acceptance gates. A catalogue entry or upstream repository link does not mean a feature is installed or integrated.

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
    zexa job cancel 12
    zexa job retry 12

Cancel applies only to pending jobs; retry applies only to failed jobs. Worker failures store the exception class, not potentially sensitive exception text.

Run one due job manually:

    zexa worker --once

For a Termux runit service, install Termux:API (Android app) and the Termux packages, then:

    pkg install termux-api termux-services
    python -m pip install -e .
    bash scripts/install-termux-worker.sh

Optional device-reboot startup (after installing/opening the Termux:Boot Android add-on):

    bash scripts/install-termux-boot.sh

The installer creates a service entrypoint tied to this checkout, loads its `.env`, and uses the stable queue database at `~/.zexa/jobs.sqlite3` so scheduled jobs and the service see the same queue regardless of working directory. The worker handles local notifications and low-risk skill drafts through the guarded execution gateway; imported skills and arbitrary commands are never executed. Android notifications require Termux:API permission. Check the service with `sv status zexa-worker`; stop/start with `sv down zexa-worker` / `sv up zexa-worker`; disable service startup with `sv-disable zexa-worker`. Android may still restrict background work; device-reboot startup requires the optional Termux:Boot add-on and device validation.

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

GitHub Actions runs byte-compilation, Termux installer shell-syntax checks, and the unit-test suite on Python 3.11, 3.12, and 3.13. The Android workflow runs bridge JVM unit tests and assembles a debug APK. A separate scheduled CodeQL workflow scans Python security queries. Dependabot checks Python and GitHub Actions updates. These CI checks do not replace Android device testing or repository-level secret-scanning settings.

## Development checks

    python -m unittest discover -s tests -v

## Project provenance

This is an independent implementation. Reference repositories and attribution are documented in THIRD_PARTY_NOTICES.md. Upstream source code is not copied into this repository by default.