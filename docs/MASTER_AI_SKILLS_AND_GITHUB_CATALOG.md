# Zexa Master AI Skills, Tools & GitHub Reference Catalog

> Status: consolidated roadmap and reference index. This document records capabilities and upstream projects discussed for Zexa. **A repository being listed here does not mean its code is installed, integrated, enabled, maintained, or safe to run inside Zexa.** Each integration requires compatibility, license, security, resource, and test review.

## 1. Skill inventory

### 1.1 Registered baseline skills (3)
These are the three baseline skill names in the current catalog:
- `general_assistant`
- `text_analysis`
- `coding_review`

### 1.2 Proposed skill roadmap (50)
These are proposed names, not claims of completed implementation.

**AI brain & intelligence**
- `reasoning_engine`
- `intent_detection`
- `context_awareness`
- `self_reflection`
- `task_decomposition`
- `decision_engine`
- `adaptive_personality`
- `multi_agent_orchestration`

**Internet & research**
- `web_search`
- `web_browsing`
- `web_scraping`
- `deep_research`
- `fact_verification`
- `news_monitoring`
- `document_research`

**Android Human Hand**
- `android_app_control`
- `screen_understanding`
- `touch_gesture_control`
- `file_manager`
- `notification_manager`
- `clipboard_manager`
- `device_status_monitor`

**Voice assistant**
- `voice_assistant`

**GitHub & coding**
- `github_agent`
- `code_generation`
- `code_debugging`
- `code_review_advanced`
- `automated_testing`
- `project_builder`
- `git_management`

**Memory & productivity**
- `long_term_memory`
- `semantic_memory_search`
- `knowledge_base`
- `calendar_manager`
- `reminder_scheduler`
- `background_task_manager`

**Business & earning automation**
- `business_research`
- `customer_support`
- `lead_research`
- `content_creation`
- `seo_research`
- `social_media_manager`
- `ecommerce_assistant`
- `workflow_automation`

**System management**
- `skill_discovery`
- `dynamic_skill_loader`
- `plugin_manager`
- `error_recovery`
- `security_guardian`
- `task_verification`

**Inventory count:** 3 baseline names + 50 proposed names = 53 named skills. This is a roadmap inventory, not a claim that all 53 are implemented.

## 2. Additional tools and capabilities

These are capability areas discussed for Zexa. Their implementation state must be checked in code and tests before use.

- Calculator
- Text statistics
- SQLite memory
- Task history and task status tracking
- Task planner
- Safe tool router
- Approval system
- Android capability detection
- Android notifications and toast
- Clipboard read/write
- Speech-to-text and text-to-speech
- Open URL
- Flashlight control (only where supported and explicitly permitted)
- Android Accessibility Bridge
- Online Groq brain
- Offline llama.cpp brain
- Online/offline brain router

## 3. GitHub upstream reference directory

The following are upstream projects to evaluate as references or optional integration candidates. Do not bulk-clone or bundle all projects into the Android/Termux runtime. Prefer narrow adapters and documented interfaces. Verify current repository ownership, availability, license, release health, dependency footprint, platform support, and security posture before selecting any project.

### 3.1 AI agents & Jarvis systems
- [OpenHands](https://github.com/All-Hands-AI/OpenHands)
- [Open Interpreter](https://github.com/OpenInterpreter/open-interpreter)
- [AutoGPT](https://github.com/Significant-Gravitas/AutoGPT)
- [Leon AI](https://github.com/leon-ai/leon)
- [SuperAGI](https://github.com/TransformerOptimus/SuperAGI)
- [AgentGPT](https://github.com/reworkd/AgentGPT)
- [BabyAGI](https://github.com/yoheinakajima/babyagi)
- [OpenManus](https://github.com/FoundationAgents/OpenManus)
- [Microsoft JARVIS](https://github.com/microsoft/JARVIS)
- [AI Waves Agents](https://github.com/aiwaves-cn/agents)
- [MetaGPT](https://github.com/FoundationAgents/MetaGPT)
- [CrewAI](https://github.com/crewAIInc/crewAI)
- [Microsoft TaskWeaver](https://github.com/microsoft/TaskWeaver)
- [AgentVerse](https://github.com/OpenBMB/AgentVerse)

### 3.2 AI brain, LLM & model runtimes
- [llama.cpp](https://github.com/ggml-org/llama.cpp)
- [Ollama](https://github.com/ollama/ollama)
- [llama-cpp-python](https://github.com/abetlen/llama-cpp-python)
- [Transformers](https://github.com/huggingface/transformers)
- [vLLM](https://github.com/vllm-project/vllm)
- [SGLang](https://github.com/sgl-project/sglang)
- [LiteLLM](https://github.com/BerriAI/litellm)
- [Llama Stack](https://github.com/llamastack/llama-stack)
- [LocalAI](https://github.com/mudler/LocalAI)
- [MLX](https://github.com/ml-explore/mlx)
- [GPT4All](https://github.com/nomic-ai/gpt4all)
- [Jan](https://github.com/janhq/jan)
- [Open WebUI](https://github.com/open-webui/open-webui)
- [AnythingLLM](https://github.com/Mintplex-Labs/anything-llm)

### 3.3 Multi-agent & workflow systems
- [LangGraph](https://github.com/langchain-ai/langgraph)
- [LangChain](https://github.com/langchain-ai/langchain)
- [Microsoft AutoGen](https://github.com/microsoft/autogen)
- [Semantic Kernel](https://github.com/microsoft/semantic-kernel)
- [Haystack](https://github.com/deepset-ai/haystack)
- [LlamaIndex](https://github.com/run-llama/llama_index)
- [Pydantic AI](https://github.com/pydantic/pydantic-ai)
- [Agno](https://github.com/agno-agi/agno)
- [Mastra](https://github.com/mastra-ai/mastra)
- [Temporal](https://github.com/temporalio/temporal)
- [Prefect](https://github.com/PrefectHQ/prefect)
- [Dagster](https://github.com/dagster-io/dagster)
- [n8n](https://github.com/n8n-io/n8n)
- [Dify](https://github.com/langgenius/dify)
- [Flowise](https://github.com/FlowiseAI/Flowise)

### 3.4 Android Human Hand & device control
- [uiautomator2](https://github.com/openatx/uiautomator2)
- [Appium](https://github.com/appium/appium)
- [Maestro](https://github.com/mobile-dev-inc/maestro)
- [scrcpy](https://github.com/Genymobile/scrcpy)
- [Android Debug Bridge (platform tools)](https://github.com/Genymobile/adb)
- [Airtest](https://github.com/AirtestProject/Airtest)
- [atx-agent](https://github.com/openatx/atx-agent)
- [AndroidViewClient](https://github.com/dtmilano/AndroidViewClient)
- [Fastbot Android](https://github.com/bytedance/Fastbot_Android)
- [Robot Framework](https://github.com/robotframework/robotframework)
- [Accessibility Test Framework](https://github.com/google/Accessibility-Test-Framework-for-Android)
- [ADB Enhanced](https://github.com/ashishb/adb-enhanced)
- [Termux](https://github.com/termux/termux-app)
- [Termux API](https://github.com/termux/termux-api)
- [Shizuku](https://github.com/RikkaApps/Shizuku)

### 3.5 Browser automation & web intelligence
- [Browser Use](https://github.com/browser-use/browser-use)
- [Playwright](https://github.com/microsoft/playwright)
- [Puppeteer](https://github.com/puppeteer/puppeteer)
- [Selenium](https://github.com/SeleniumHQ/selenium)
- [Stagehand](https://github.com/browserbase/stagehand)
- [Crawl4AI](https://github.com/unclecode/crawl4ai)
- [Firecrawl](https://github.com/firecrawl/firecrawl)
- [Crawlee](https://github.com/apify/crawlee)
- [Scrapy](https://github.com/scrapy/scrapy)
- [Beautiful Soup](https://github.com/wention/BeautifulSoup4)
- [MechanicalSoup](https://github.com/MechanicalSoup/MechanicalSoup)
- [Browserless](https://github.com/browserless/browserless)
- [Skyvern](https://github.com/Skyvern-AI/skyvern)
- [LaVague](https://github.com/lavague-ai/LaVague)
- [AgentQL](https://github.com/tinyfish-io/agentql)

### 3.6 Memory & knowledge systems
- [Mem0](https://github.com/mem0ai/mem0)
- [Zep](https://github.com/getzep/zep)
- [Graphiti](https://github.com/getzep/graphiti)
- [Letta](https://github.com/letta-ai/letta)
- [Cognee](https://github.com/topoteretes/cognee)
- [Chroma](https://github.com/chroma-core/chroma)
- [Qdrant](https://github.com/qdrant/qdrant)
- [Milvus](https://github.com/milvus-io/milvus)
- [Weaviate](https://github.com/weaviate/weaviate)
- [LanceDB](https://github.com/lancedb/lancedb)
- [FAISS](https://github.com/facebookresearch/faiss)
- [SQLite](https://github.com/sqlite/sqlite)
- [DuckDB](https://github.com/duckdb/duckdb)
- [TinyDB](https://github.com/msiemens/tinydb)
- [txtai](https://github.com/neuml/txtai)

### 3.7 Voice assistant & speech
- [Whisper](https://github.com/openai/whisper)
- [whisper.cpp](https://github.com/ggml-org/whisper.cpp)
- [Faster Whisper](https://github.com/SYSTRAN/faster-whisper)
- [Piper](https://github.com/rhasspy/piper)
- [Coqui TTS](https://github.com/coqui-ai/TTS)
- [Kokoro](https://github.com/hexgrad/kokoro)
- [Vosk](https://github.com/alphacep/vosk-api)
- [SpeechBrain](https://github.com/speechbrain/speechbrain)
- [Silero Models](https://github.com/snakers4/silero-models)
- [openWakeWord](https://github.com/dscripka/openWakeWord)
- [Porcupine](https://github.com/Picovoice/porcupine)
- [ESPnet](https://github.com/espnet/espnet)
- [Mimic 3](https://github.com/MycroftAI/mimic3)
- [MaryTTS](https://github.com/marytts/marytts)
- [RealtimeTTS](https://github.com/KoljaB/RealtimeTTS)

### 3.8 Coding, GitHub & software development
- [SWE-agent](https://github.com/SWE-agent/SWE-agent)
- [Aider](https://github.com/Aider-AI/aider)
- [Continue](https://github.com/continuedev/continue)
- [OpenDevin](https://github.com/OpenDevin/OpenDevin)
- [Cline](https://github.com/cline/cline)
- [Roo Code](https://github.com/RooCodeInc/Roo-Code)
- [Mentat](https://github.com/AbanteAI/mentat)
- [GPT Pilot](https://github.com/Pythagora-io/gpt-pilot)
- [AI PR Reviewer](https://github.com/coderabbitai/ai-pr-reviewer)
- [Reviewdog](https://github.com/reviewdog/reviewdog)
- [Semgrep](https://github.com/semgrep/semgrep)
- [Ruff](https://github.com/astral-sh/ruff)
- [Pytest](https://github.com/pytest-dev/pytest)
- [Pre-commit](https://github.com/pre-commit/pre-commit)

### 3.9 Business, CRM & customer support
- [Twenty CRM](https://github.com/twentyhq/twenty)
- [EspoCRM](https://github.com/espocrm/espocrm)
- [SuiteCRM](https://github.com/salesagility/SuiteCRM)
- [Odoo](https://github.com/odoo/odoo)
- [ERPNext](https://github.com/frappe/erpnext)
- [Chatwoot](https://github.com/chatwoot/chatwoot)
- [Zammad](https://github.com/zammad/zammad)
- [FreeScout](https://github.com/freescout-helpdesk/freescout)
- [Cal.com](https://github.com/calcom/cal.com)
- [Formbricks](https://github.com/formbricks/formbricks)
- [Baserow](https://github.com/bram2w/baserow)
- [Appsmith](https://github.com/appsmithorg/appsmith)
- [Budibase](https://github.com/Budibase/budibase)
- [Directus](https://github.com/directus/directus)
- [NocoDB](https://github.com/nocodb/nocodb)

### 3.10 Content creation, social media & SEO
- [Postiz](https://github.com/gitroomhq/postiz-app)
- [Mixpost](https://github.com/inovector/mixpost)
- [WordPress](https://github.com/WordPress/wordpress-develop)
- [Ghost](https://github.com/TryGhost/Ghost)
- [Strapi](https://github.com/strapi/strapi)
- [Payload CMS](https://github.com/payloadcms/payload)
- [Keystone](https://github.com/keystonejs/keystone)
- [Remotion](https://github.com/remotion-dev/remotion)
- [MoviePy](https://github.com/Zulko/moviepy)
- [FFmpeg](https://github.com/FFmpeg/FFmpeg)
- [Manim](https://github.com/ManimCommunity/manim)
- [OpenShot](https://github.com/openshot/openshot-qt)
- [Shotcut](https://github.com/mltframework/shotcut)
- [Plausible Analytics](https://github.com/plausible/analytics)
- [Umami](https://github.com/umami-software/umami)

### 3.11 Security, permissions & reliability
- [OWASP ZAP](https://github.com/zaproxy/zaproxy)
- [Bandit](https://github.com/PyCQA/bandit)
- [Safety](https://github.com/pyupio/safety)
- [Trivy](https://github.com/aquasecurity/trivy)
- [Gitleaks](https://github.com/gitleaks/gitleaks)
- [Checkov](https://github.com/bridgecrewio/checkov)
- [Open Policy Agent](https://github.com/open-policy-agent/opa)
- [Casbin](https://github.com/casbin/casbin)
- [Sentry](https://github.com/getsentry/sentry)
- [GlitchTip](https://github.com/glitchtip/glitchtip)

### 3.12 Plugins, integrations & protocols
- [Model Context Protocol](https://github.com/modelcontextprotocol)
- [MCP Servers](https://github.com/modelcontextprotocol/servers)
- [FastMCP](https://github.com/jlowin/fastmcp)
- [Composio](https://github.com/ComposioHQ/composio)
- [Pipedream](https://github.com/PipedreamHQ/pipedream)
- [Trigger.dev](https://github.com/triggerdotdev/trigger.dev)
- [Inngest](https://github.com/inngest/inngest)
- [Windmill](https://github.com/windmill-labs/windmill)
- [Activepieces](https://github.com/activepieces/activepieces)
- [Kestra](https://github.com/kestra-io/kestra)

## 4. Other named projects from prior planning

- [Open Jarvis](https://github.com/open-jarvis) — organization/project reference; verify the intended repository before integrating.
- [OpenHands](https://github.com/All-Hands-AI/OpenHands)
- [Leon AI](https://github.com/leon-ai/leon)
- [Open Interpreter](https://github.com/OpenInterpreter/open-interpreter)
- [Zexa](https://github.com/sunnyprajapati1947-coder/Zexa) — this repository.
- Spdyi-AI
- SunnyAI / Nova
- ZIXU
- ALEXA

The final four project names above are recorded as discussed names; exact repository URLs were not available in the consolidated notes and are intentionally not guessed.

## 5. Zexa target architecture

### AI brain
Online model + local LLM + brain router.

### Intelligence layer
Skill registry + reasoning + memory + planner + bounded multi-agent orchestration.

### Human Hand
Android Accessibility Bridge + supported Android APIs + browser adapter + files + voice.

### Execution and safety
Least-privilege permissions + user approvals + background task queue + notifications + audit history + recovery.

### Work domains
Coding + research + business operations + customer support + content creation.

## 6. Integration rules and acceptance criteria

1. **Catalog is not integration.** A listed skill or upstream repository must not be described as implemented until code, tests, and user-facing documentation exist.
2. **No bulk installation.** Select only the smallest compatible components needed for a concrete feature. Large server stacks may not be suitable for Android/Termux.
3. **License review.** Record SPDX license, attribution obligations, and redistribution constraints before copying or packaging code.
4. **Supply-chain review.** Pin versions/commits, inspect dependencies, scan for secrets and known vulnerabilities, and avoid untrusted install scripts.
5. **Capability boundaries.** Skills declare required permissions and risk levels. Android actions, external messages, purchases, account changes, and destructive file operations require explicit user approval.
6. **Network boundaries.** Keep the Android bridge loopback-only by default. Never expose its control endpoint to public networks without a separately reviewed authentication and transport design.
7. **Privacy.** Minimize screen, clipboard, file, and conversation data collection. Redact credentials and sensitive fields; do not collect continuously by default.
8. **Resource budgets.** Evaluate RAM, storage, CPU, battery, network use, model size, and cold-start time on the target Android device.
9. **Testing.** Add unit tests, integration tests, permission-denial tests, failure/retry tests, and on-device checks for Android-specific features.
10. **Observability.** Record task IDs, status transitions, tool outcomes, approval decisions, and sanitized error details. Never log tokens or secrets.
11. **Human confirmation.** Treat model plans as proposals. Validate arguments and permissions in deterministic code before executing a tool.
12. **Compatibility.** Prefer adapters around existing Zexa interfaces; do not replace working project components solely to adopt a popular framework.

## 7. Roadmap status convention

Use these labels in future documentation and issue tracking:
- **Implemented:** code exists and tests pass for the stated behavior.
- **Partially implemented:** code exists, but at least one required behavior or verification remains.
- **Planned:** design/name exists; implementation has not been completed.
- **Research candidate:** upstream project is listed for evaluation only.
- **Blocked:** implementation depends on missing permission, platform support, credential, or external service.

Do not infer status from this catalog alone.
