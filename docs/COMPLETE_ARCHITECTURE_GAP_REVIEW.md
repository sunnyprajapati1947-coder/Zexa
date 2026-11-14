# Zexa Complete Architecture Gap Review

**Review basis:** GitHub repository `main`, source tree, Python modules, Android companion source, tests, and the two current GitHub Actions workflows inspected for this review.

**Purpose:** Translate the intended phone-first Jarvis-style Zexa into verifiable engineering requirements. This is an audit and implementation plan, not a claim that every roadmap item is already built.

## 1. Executive assessment

Zexa has a useful working foundation:
- Groq online brain and optional local llama.cpp brain with an explicit router.
- CLI for ask, planning, voice, research, memory, tasks, notifications, jobs, and bridge operations.
- SQLite key-value memory and task/job persistence.
- A bounded specialist-agent layer and a small typed skill registry.
- A native Android AccessibilityService companion app with a loopback-only authenticated bridge.
- Python CI across Python 3.11–3.13 and an Android debug-build workflow.

Zexa is **not yet a full autonomous Jarvis or a complete AI operating system**. Most of the 170-skill catalogue is a roadmap. The current code has seven registered skill definitions, but only a small set of real local tools and one built-in background job handler. Most external integrations and device workflows are not present.

## 2. Verified current state

| Area | Verified repository state | Honest status |
|---|---|---|
| Online brain | Groq chat client | Implemented foundation; provider/model availability depends on configuration |
| Offline brain | llama.cpp CLI + GGUF configuration | Implemented foundation; model must be installed separately |
| Brain router | auto/online/offline; network-only fallback | Implemented |
| Skill registry | 7 registered definitions: general, analysis, code review, support draft, proposal, invoice draft, FAQ | Partial |
| Specialist agents | general, analyst, developer, business; sequential bounded LLM calls | Partial; no external tool execution |
| Tools | calculator and text statistics | Minimal |
| Memory | explicit SQLite key/value save, recall, list, forget, clear | Partial; no semantic retrieval or automatic context injection |
| Task history | SQLite task records and status updates | Partial |
| Background jobs | durable SQLite queue, retry and stale-job recovery | Partial; built-in worker handles notifications only |
| Web research | DuckDuckGo result snippets with numbered references | Partial; no full-page reading or source verification |
| Voice | Termux push-to-talk/STT/TTS and user-started conversation loop | Partial; no native always-on wake-word service |
| Android Human Hand | native app, manually enabled AccessibilityService, local authenticated bridge, allowlisted actions and CLI approval | Implemented foundation; real-device end-to-end validation remains |
| Business | customer reply, proposal, invoice and FAQ drafts | Partial; no CRM/email/payment integrations |
| CI | Python tests on 3.11/3.12/3.13 | Implemented |
| Android CI | debug APK build and artifact upload | Implemented build pipeline; no release-signing pipeline |
| Browser automation | no browser automation adapter found in source tree | Missing |
| Calendar/CRM/email | no provider adapters found | Missing |
| Plugin/MCP integration | no plugin runtime or MCP client/server adapter found | Missing |
| Semantic memory / RAG | no vector index or retrieval pipeline found | Missing |
| User-facing dashboard | no Zexa control dashboard found | Missing |

The 170-item `docs/SKILL_CATALOG.md` is the canonical roadmap. The separate 53-name master list is an earlier condensed inventory and must not be treated as the full roadmap or as an implementation count.

## 3. Concrete documentation inconsistencies to fix

1. README's opening architecture section still describes the Android app as not yet present, while `app/` contains the native companion app and Android workflow.
2. README calls the companion app a future requirement in the protocol section even though the app is now in the repository.
3. README links the 53-name condensed catalogue as though it were the primary inventory; the canonical roadmap contains 170 named skills.
4. README describes the specialist-agent flow, but should more clearly state that the agents do not execute browser, shell, GitHub, messaging, or arbitrary device workflows.
5. README's current implementation summary should distinguish local draft generation from real customer-facing integrations.

## 4. Engineering gaps and required work

### P0 — correctness, safety and trust boundaries

- **Runtime skill validation:** skill schemas are descriptive metadata today. Add actual input validation before dispatch; reject missing, extra, malformed, and oversized fields.
- **Permission enforcement:** `required_permissions` and dependencies are recorded but are not yet a complete policy engine. Add a central permission registry and enforce permissions at the execution boundary, not only in prompts.
- **Approval lifecycle:** current approval primitives are small and the generic tool router refuses consequential tools. Add approval records bound to a specific action, exact arguments, user, expiry, and one-time use. Revalidate after approval to prevent argument substitution.
- **Audit trail:** persist who requested an action, normalized arguments, permission decision, approval, execution result, and failure. Redact tokens and personal data.
- **Prompt-injection boundary:** keep web pages, screen text, documents, repository content, and tool output as untrusted data. Add tests proving external content cannot change tool permissions or override system policy.
- **Path and URL validation:** every future file and browser adapter needs an allowlisted root/domain, redirect policy, size limit, timeout, MIME validation, and traversal protection.
- **Secret handling:** add documented secret rotation and redaction; scan repository history and CI output for accidental credentials. Never store tokens in source or logs.
- **Action idempotency:** external actions need idempotency keys and duplicate-submit protection before email, CRM, scheduling, or publishing adapters are introduced.

### P1 — core Jarvis intelligence

- **Real skill handlers:** connect each implemented skill to a typed handler. A skill must not be considered available just because it is listed in the registry.
- **Agent collaboration:** the current orchestrator runs specialists sequentially but does not pass prior specialist results into later steps. Add a bounded shared task context, explicit handoff schema, provenance, and final synthesis.
- **Plan validation:** validate planner output against a strict schema, reject unknown skills, cap steps and input/output size, and provide a deterministic fallback when the model returns malformed plans.
- **Memory-aware conversation:** add explicit opt-in memory retrieval to relevant requests; provide source/provenance, edit/delete, retention settings, export, and backup/restore. Keep current explicit-save behavior as the default.
- **Conversation context:** add bounded conversation sessions and summaries. Make it clear when context is session-only versus persisted.
- **Task lifecycle:** unify task and job IDs, states, cancellation, retry policy, deadlines, progress, and user-visible completion/error notifications.
- **Brain resilience:** add provider health checks, bounded timeouts, rate-limit handling, retry/backoff, cancellation, token budgets, and clear provider attribution. Never silently switch providers for authentication or quota errors.
- **Evaluation:** add golden task tests for Hindi/Hinglish, tool selection, factuality, refusal boundaries, prompt injection, malformed output, and online/offline parity.

### P1 — Android Human Hand

- **On-device verification:** test install, Accessibility opt-in, bridge start/stop, token mismatch, screen read, all allowlisted gestures, app launch, permission revocation, process death, and reboot on the target Android version.
- **Action-specific confirmation:** show the target app, screen context, action, and exact text before each consequential action. Require fresh confirmation for messages, posts, account changes, purchases, deletion, and form submission.
- **Sensitive UI handling:** redact password, payment, OTP, private-message, and other sensitive fields before any optional AI processing; do not upload screen snapshots automatically.
- **Foreground/background lifecycle:** document Android background limits, battery optimization, service state, and recovery. Do not claim persistent background operation unless verified under Doze and process-kill conditions.
- **Bridge lifecycle:** add token rotation/revocation, request IDs, replay protection, strict payload schemas, request rate limits, and clear service status.
- **Accessibility limitations:** document that AccessibilityService is not equivalent to unrestricted device/root control and that secure/system screens may not be accessible.

### P1 — voice

- Keep microphone capture visibly user-started and provide a reliable stop/cancel control.
- Add explicit microphone state, timeout, silence handling, and error recovery.
- Keep wake-word detection optional and disabled by default; if introduced, document on-device processing, battery use, and visible controls.
- Add speech-language selection and Hindi/Hinglish regression tests.
- Prevent voice transcription from directly authorizing sensitive actions; spoken intent must still pass the same approval flow.

### P2 — internet, browser and research

- Add a provider interface for search and page reading; retain the current fixed search adapter as one provider.
- Add full-page fetch with domain allowlists, redirect restrictions, robots/terms awareness, content-size limits, and safe HTML-to-text extraction.
- Store source URL, title, retrieval time, and content hash; cite claims to actual retrieved source passages.
- Add cross-source fact checks and clear confidence/uncertainty labels.
- Add browser automation only as a separate optional adapter with isolated browser context, no saved credentials by default, and user approval for submissions.
- Add monitoring only for user-selected sources and a clear stop/delete control.

### P2 — productivity, business and creator workflows

- Add optional calendar, contacts, email, CRM, cloud-storage, and social publishing adapters only after OAuth scopes and provider permissions are reviewed.
- Keep customer replies, proposals, invoices, posts, and lead lists as drafts by default. Do not send bulk outreach, spam, publish, issue invoices, or alter customer records without review and explicit confirmation.
- Add a business workspace with customer/project records, service catalogue, approved pricing, proposal templates, and delivery status.
- Add content calendar, asset library, captions, scripts, brand voice, and analytics import/export.
- Add data import/export with schema validation and backup/restore.
- Treat payment processing, financial transfers, and account ownership changes as out of scope for unattended automation.

### P2 — developer and GitHub automation

- Add read-only GitHub inspection first: repository metadata, tree, issues, PRs, CI status, releases, and dependency alerts.
- Add branch/file writes only through reviewed diffs and an approval step; never commit secrets.
- Add test execution in an isolated, resource-limited environment. Never execute untrusted repository code on the phone with unrestricted access.
- Add PR creation as a reviewable artifact; do not auto-merge by default.
- Add release notes, versioning, changelog, signed release artifacts, and rollback instructions.
- Add dependency inventory/SBOM, license report, vulnerability report, and provenance for release artifacts.

### P2 — reliability and operations

- Add structured, redacted logs with rotation and configurable retention.
- Add health/status commands for brain, database, worker, voice, Android bridge, and integrations.
- Add database schema migrations, corruption detection, backup/restore, and recovery tests.
- Add worker cancellation, graceful shutdown, queue visibility, failed-job inspection, and safe retry controls.
- Add resource telemetry for RAM, storage, CPU, battery, network, model load time, and inference latency.
- Add offline-first behavior and clear network-required indicators for every feature.
- Add a minimal local dashboard only if it can run reliably on the target phone; otherwise keep CLI-first.

## 5. GitHub repository and CI/CD gaps

Current workflows declare read-only repository permissions, which is a good baseline. The workflows currently reference Actions by mutable version tags (for example, `actions/checkout@v4`). Before production releases:
- Pin third-party Actions to verified full commit SHAs or adopt GitHub's workflow dependency lockfile where supported.
- Add Dependabot updates for Python packages and GitHub Actions.
- Add CodeQL or equivalent static analysis for Python and Kotlin.
- Add secret scanning and push protection in repository settings; verify settings in GitHub because they are not fully represented by source files.
- Add dependency vulnerability scanning and license/SBOM reporting.
- Add Android unit/instrumentation tests in addition to `assembleDebug`.
- Add release build signing through protected GitHub environments and short-lived credentials; never commit keystores or signing secrets.
- Keep fork PR workflows read-only and never run untrusted code in privileged `pull_request_target` or `workflow_run` contexts.
- Retain least-privilege `GITHUB_TOKEN` permissions and review any future permission elevation.

These recommendations align with GitHub's official secure-use guidance: https://docs.github.com/en/actions/reference/security/secure-use

## 6. Device-specific acceptance targets

The target is a phone-first Android/Termux runtime, not a server stack. The current project should preserve a small baseline and make heavy features optional.

- ARM64 Android compatibility.
- No root required for baseline operation.
- No DPI changes or hidden device modifications.
- Online Groq brain and optional local GGUF brain.
- Local-first memory and task records.
- Explicit permissions and approvals for Android actions.
- Background worker must report when Android has stopped or restricted it.
- Configurable CPU threads, context, output tokens, timeout, and memory budgets.
- Graceful low-memory behavior; no automatic large model downloads.
- Every optional integration must state storage, RAM, battery, network, and credential requirements.

## 7. Acceptance gates before calling Zexa “Jarvis-ready”

A milestone is complete only when all applicable gates pass:

1. **Code:** implementation exists behind a stable interface.
2. **Schema:** input and output validation is enforced in code.
3. **Permissions:** least-privilege permissions are checked before execution.
4. **Approval:** consequential actions require explicit, action-bound user confirmation.
5. **Tests:** unit, integration, negative, failure/retry, and security tests pass.
6. **Device:** Android features are tested on a real supported device and OS version.
7. **Reliability:** cancellation, timeout, recovery, and offline behavior are verified.
8. **Privacy:** data collection, retention, deletion, redaction, and export are documented.
9. **Operations:** status, logs, backup, and recovery are usable.
10. **Docs:** README and skill status match actual behavior.
11. **Release:** versioned artifact, checksum/provenance, and rollback instructions exist.

## 8. Recommended implementation sequence

1. Reconcile README and roadmap truth; keep the 170-skill catalogue canonical.
2. Finish typed skill input validation, permission registry, action-bound approvals, and audit log.
3. Improve agent handoffs so each step receives previous verified results; add planner-output validation.
4. Add memory retrieval/context injection with explicit opt-in and backup/export.
5. Harden Android bridge lifecycle and complete real-device test matrix.
6. Improve the worker/task lifecycle and notification/error reporting.
7. Upgrade web research to source-grounded page retrieval and citations.
8. Add GitHub read-only adapter, code scanning, dependency management, and safe PR workflow.
9. Add optional browser, calendar, email, CRM, and creator adapters one at a time.
10. Add local dashboard only after core reliability and resource budgets are met.

## 9. Definition of done

Zexa is ready for a capability only when the feature works end-to-end on the target device, the permission and approval boundary is enforced in code, tests cover both success and denial/failure, documentation matches reality, and the user can inspect, stop, revoke, and recover the operation.

**Bottom line:** Keep Zexa as one repository. Keep the 170-skill list as a roadmap. Implement the smallest dependable phone-first core first; do not bulk-import 167 upstream projects or pretend that catalogue entries are working skills.
