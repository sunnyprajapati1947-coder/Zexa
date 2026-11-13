# Zexa

**Zexa** is a phone-first, modular AI assistant and developer agent. Its only supported AI provider is **Groq**. No OpenAI, Gemini, Claude, OpenRouter, or local-model fallback is included.

## Project status

This repository is the independent Zexa implementation. The upstream projects listed in [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) are reference checkouts under the local `sources/` directory; their source code is not copied into this repository by default.

## Design principles

- **One provider:** Groq API only, configured with `GROQ_API_KEY` and `GROQ_MODEL`.
- **Modular skills:** tools and skills are explicit, discoverable modules.
- **Human approval:** sensitive or externally visible actions require a clear approval step.
- **Least privilege:** no arbitrary shell execution from model output; tools must validate inputs and permissions.
- **Phone-first:** keep the core lightweight and make Android capabilities optional adapters.
- **Traceability:** log tool decisions and outcomes without logging secrets.

## Initial architecture

```text
src/zexa/
  cli.py       Command-line entry point
  groq.py      Groq-only HTTPS chat client
  config.py    Environment configuration
  approvals.py Human approval primitives
```

Current modules include a skill registry, memory store, task history, task planner, permission-aware tool router, and a read-only Termux capability probe. The Android hand supports explicit CLI notification and speech input/output commands. `zexa voice` captures one utterance, sends its transcript to the configured Groq model, and speaks the reply. `zexa converse` starts a user-controlled loop with Groq-based intent routing: questions and casual conversation receive replies, unclear/empty captures are skipped, and clear task requests are acknowledged without executing anything. Task requests must still be planned separately; sensitive actions require explicit approval. Say `stop`, `exit`, `quit`, `band karo`, or `बंद करो`, or press Ctrl+C to end the session. After three consecutive empty speech captures, the loop exits cleanly. Microphone capture starts only after the user manually runs a voice command; there is no background or always-on microphone access.

## Requirements

- Python 3.11+
- A Groq API key
- A Groq model ID enabled for your account

## Setup

```bash
cd ~/Zexa
python -m venv .venv
. .venv/bin/activate
python -m pip install -e .
cp .env.example .env
``

Edit `.env` locally and set `GROQ_API_KEY` and `GROQ_MODEL`. Never commit `.env`.

Ask Zexa:

```bash
zexa ask "Explain what you can do"
zexa android
zexa notify "Zexa" "Your requested notification message"
zexa listen
zexa speak "Hello, I am Zexa"
zexa voice
``

Or run without installing the console script:

```bash
python -m zexa.cli ask "Explain what you can do"
``

## Safety boundary

Zexa may draft plans and prepare changes. Sending messages, publishing content, changing accounts, purchases/payments, deleting data, and other consequential actions must remain behind explicit user confirmation. Accessibility access is opt-in. A model response is never itself authorization to execute a tool.

## License

Project licensing and upstream attribution are documented in [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).