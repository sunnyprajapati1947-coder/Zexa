# Zexa Human Hand — Master Architecture and Delivery Plan

**Status:** Architecture baseline; implementation is staged and must be verified per capability.  
**Parent baseline:** `fix/reviewed-security-and-integrity` at `086d1eca5d296fb778a112639115e90f2e865c82`.  
**Primary runtime:** Termux on the Android phone. The native Android companion is an optional, permission-gated device bridge.

## 1. Product objective

Zexa is a command-driven personal AI operator. The user gives a goal in natural Hindi, Hinglish, or English; Zexa plans the work, selects only installed and authorized capabilities, operates supported phone or paired-computer tools, reports progress, and returns evidence of what actually completed.

The Human Hand is the execution layer. It must not be confused with the language model: Qwen or an online model proposes plans, while deterministic controllers, typed adapters, permission checks, and approval gates decide what can execute.

"Human-like capability" is a product direction, not a claim of unrestricted access. Zexa can perform only actions exposed by supported operating-system APIs, installed adapters, user-granted permissions, and the relevant app's own security controls. It cannot bypass Android secure surfaces, device-owner restrictions, authentication, or physical-world requirements.

## 2. Core architecture

1. **Command interface** — Termux CLI first; optional voice input started by the user; optional Android companion UI and notifications.
2. **Brain router** — local Qwen/llama.cpp for offline work; configured online providers and web research when internet is available. Provider choice and fallback must be visible. Network failure may trigger offline fallback; authentication, quota, policy, or malformed-output errors must not be silently hidden.
3. **Planner/controller** — converts a user goal into a bounded typed task plan. The model may request registered capabilities but cannot invent handlers, permissions, risk levels, or approval results.
4. **Capability registry** — the authoritative list of installed actions, JSON input/output schemas, permission scopes, risk classes, platform requirements, timeouts, resource budgets, and enabled state.
5. **Human Hand adapters** — Android Accessibility Bridge, Termux/Android APIs, paired laptop agent, browser automation, and provider APIs. Each adapter has a narrow contract and its own health/status report.
6. **Execution gateway** — validates arguments, checks permissions, requests action-bound approval, invokes trusted handlers, enforces timeouts/idempotency, and writes an audit event.
7. **Task runtime** — durable task IDs, checkpoints, progress, cancellation, retry rules, deadlines, and restart recovery. Side-effecting actions are never blindly retried.
8. **Memory and learning** — user-controlled facts, task summaries, approved knowledge notes, and reviewed skill definitions with provenance. Imported instructions and webpages remain untrusted data.
9. **Observability** — notifications and a readable task history show the selected brain, device, capability, approval state, result, and any limitation.

## 3. Human Hand capability map

### A. Android phone hand

**Existing foundation in the repository:** opt-in AccessibilityService, authenticated loopback bridge, read-only screen snapshots, allowlisted tap/swipe/scroll/back/home/text-entry/app-launch requests, and native exact-action approval. This is a foundation, not yet a fully device-validated automation system.

Planned capability groups:

- App navigation: launch an installed app and navigate supported visible UI controls.
- Screen understanding: read a user-requested accessibility snapshot; redact password, OTP, payment, and other sensitive fields before optional model processing.
- Text and forms: prepare text, fill approved fields, show a preview, and require a fresh confirmation before submission.
- Files and media: use Android document/provider APIs and Termux file tools within user-approved folders; never assume access to every app's private storage.
- Device utilities: notifications, reminders, clipboard, speech input/output, and supported system intents through Termux:API or native APIs.
- Background operation: use Termux:Services/Boot or Android WorkManager only for supported, visible, restartable jobs. Show service state and explain Android battery/Doze limits.

### B. Laptop hand

The phone may act as the command centre for a separately installed Zexa Laptop Hand on the user's own computer.

Required design:

- Pair a laptop deliberately using a short-lived pairing code and a clear device identity; allow revocation and token rotation.
- Prefer an outbound authenticated connection or an explicitly paired local-network connection. Do not expose an unauthenticated public listener or require router port-forwarding.
- Use encrypted transport, replay-resistant request IDs, strict request schemas, rate limits, and per-device capability grants.
- Start with a restricted workspace: list/read/write files only under user-selected folders, open approved applications, and report task status.
- Shell or developer commands must be previewed with their working directory and effects. Use a restricted command allowlist and per-command approval; do not provide unrestricted administrator/root execution.
- Never read browser passwords, password-manager stores, private keys, session cookies, or other credentials. Do not bypass login, endpoint protection, OS permissions, or security prompts.
- The laptop agent must have a visible running indicator, pause/stop control, local audit log, and a way to revoke the phone's pairing.

A laptop hand is **not implemented by this document**. It becomes available only after a separate agent, pairing protocol, tests, and real-device validation exist.

### C. Browser and internet hand

- Separate read-only research from interactive browser control.
- Research adapters use source URLs, titles, retrieval timestamps, content limits, redirect controls, and source citations.
- Browser control uses an isolated profile without saved credentials by default.
- Treat webpage text, downloaded files, QR codes, and screen content as untrusted input, never as instructions that can grant permissions or change the task.
- Form submission, posting, messaging, purchases, account changes, and file uploads require a preview and fresh approval for the exact destination and content.

### D. App and service connectors

Prefer official, scoped APIs for email, calendar, cloud storage, CRM, and other services when available. Request minimum OAuth scopes, store tokens in the platform's protected credential store, support revocation, and keep send/publish/update operations behind exact-action approval. Do not claim a connector exists until it is implemented and tested.

## 4. Learn and teach workflow

When the user says "learn this", "study this", or "make a skill":

1. Identify the requested subject and allowed source material.
2. Read or research the supplied material; record source, version/date, and content hash where practical.
3. Produce a concise knowledge note with facts, uncertainty, and source references.
4. Test understanding using examples or a small evaluation set.
5. If a repeatable workflow is requested, draft a typed skill contract: purpose, inputs, outputs, dependencies, permissions, risk, timeout, resource budget, and tests.
6. Keep the skill disabled until it passes review and the user explicitly enables it.
7. Version the note/skill and allow the user to inspect, edit, export, disable, or delete it.

Learning means building retrievable knowledge and reviewed workflows. It does **not** mean silently changing model weights, executing arbitrary downloaded code, or allowing a webpage or imported skill to rewrite Zexa's security policy.

## 5. Permission and approval model

Every capability is registered with a trusted permission and risk class. The model cannot lower risk or approve its own actions.

- **Read-only / low risk:** status checks and explicitly requested, scoped reads may run without a separate approval after the relevant permission has been granted.
- **Reversible local action:** opening an app or navigating a screen may use a clear user command and a visible action log.
- **Data modification:** file writes, edits, clipboard changes, and form filling require a scoped workspace/target and a preview or confirmation according to the capability policy.
- **External or consequential action:** sending a message/email, publishing, submitting a form, changing account settings, sharing files, purchases, or deleting data requires fresh confirmation bound to the exact action, destination, content/arguments, device, expiry, and one-time request ID.
- **Forbidden:** credential theft, covert surveillance, permission bypass, hidden microphone/camera capture, stealth persistence, arbitrary remote command execution, and evasion of platform security controls.

Approvals must be invalidated if any material argument, destination, content, device, or target changes. Denial, expiry, cancellation, timeout, and uncertain outcomes must fail closed. A retry after an uncertain external side effect requires checking the provider's state or asking the user; never resend blindly.

## 6. Task lifecycle and reliability

Use a durable state machine:

`proposed → validated → awaiting_approval → queued → running → completed`

Terminal alternatives: `denied`, `cancelled`, `failed`, `expired`, and `needs_user_input`.

Each task records a stable task ID, parent task ID where applicable, requested goal, plan version, selected brain, target device, capability calls, approval references, timestamps, progress, bounded result summary, and redacted error category. Do not store secrets or full sensitive screen contents in ordinary logs.

Every task has maximum steps, wall-clock deadline, model-token/resource budget, per-tool timeout, and cancellation checks. Long workflows checkpoint between steps. Resume only from a validated checkpoint; re-check permissions and approvals after restart.

## 7. Internet and offline behaviour

- **Offline:** local Qwen, local memory, local files in permitted folders, installed Termux tools, and the local Android bridge when running. Report unavailable online capabilities instead of pretending to search.
- **Online:** configured provider, public research, and installed authenticated connectors. Display which provider/source was used.
- **Hybrid:** use local planning and private-data handling where practical; send only the minimum required data to an online provider, with explicit disclosure and user choice for sensitive content.
- Keep model download, provider credentials, and large file transfer separate from normal task execution. Never silently upload local documents or screen snapshots.

## 8. Delivery phases and acceptance gates

### Phase 0 — establish a trustworthy Human Hand baseline
- Verify the current Android bridge protocol and Python client end to end.
- Test exact-action approval, denial, expiry, replay, malformed payloads, token mismatch, service stop, process death, and permission revocation.
- Verify that screen snapshots are explicit, bounded, and redacted before model use.
- Confirm all current CLI device actions route through the trusted execution gateway.
- Validate Qwen load settings on the target phone before enabling model load by default.

**Gate:** automated tests pass and the target Android device passes a documented manual test matrix. No claim of full phone control before this gate.

### Phase 1 — typed capability and task controller
- Define one capability contract shared by planner, gateway, CLI, Android adapter, and future laptop adapter.
- Add schema validation, per-capability permissions, bounded execution, cancellation, task progress, durable checkpoints, and redacted audit.
- Add prompt-injection tests for webpages, screen text, files, and imported skills.

**Gate:** unknown tools and malformed arguments are rejected; approvals are exact and one-use; interrupted tasks recover safely.

### Phase 2 — laptop pairing and restricted hand
- Implement the desktop agent for one supported OS first.
- Add pairing, revocation, device status, workspace allowlists, restricted file operations, and visible local approvals.
- Add integration tests and a real phone-to-laptop acceptance test on a user-owned device.

**Gate:** no public unauthenticated listener, no arbitrary remote shell, and every write is scoped and auditable.

### Phase 3 — browser hand and useful integrations
- Add isolated browser read/navigation first, then reviewed form workflows.
- Add official provider connectors one at a time with minimum scopes and explicit send/publish gates.

**Gate:** source provenance, prompt-injection resistance, credential isolation, and exact-action confirmation are tested.

### Phase 4 — learning, memory, and adaptive workflows
- Add user-managed knowledge library, retrieval with citations, reviewed skill authoring, versioning, and evaluations.
- Add bounded specialist collaboration only where it improves a measured task.

**Gate:** learned skills are reproducible, inspectable, disabled by default, and pass regression tests before activation.

## 9. Definition of done for any Human Hand feature

A feature is not "done" because it appears in a catalogue or UI. It must have:

- a real adapter and a typed capability definition;
- least-privilege permission checks enforced outside the model;
- exact approval for consequential side effects;
- timeout, cancellation, retry/idempotency, and recovery behaviour;
- unit tests plus controlled integration tests;
- user-visible status and a useful audit result;
- documented platform/version limitations;
- evidence from CI and, where hardware is involved, a real-device test.

## 10. Current implementation boundary

At the architecture baseline, Android Accessibility and Termux integrations exist as foundations; local Qwen and online brain routing exist; the loopback task API exposes a restricted health/jobs/notification surface. Laptop pairing, general browser automation, full-page research, production app connectors, complete skill execution, and unrestricted autonomous computer control are not implemented. The roadmap must preserve this distinction in README, UI, and task reports.


## 12. Security without blocking useful work

Security is a set of proportionate controls, not a blanket lock on every action. Zexa must remain useful and responsive while protecting private data and consequential changes.

### User-facing autonomy tiers

- **Observe:** status, help, public research, and user-requested reads from already granted folders can proceed without repeated prompts. Sensitive screen fields remain redacted.
- **Assist:** opening an app, navigating, scrolling, and other reversible UI actions can run under a clearly visible, user-started task grant. The grant is scoped to one device, one task, an explicit action set, and a short expiry; the user can pause or revoke it at any time. Do not ask for a fresh confirmation for every tap in that approved task.
- **Change:** writing or editing local files requires a scoped folder and a preview. A task grant may cover a batch of reversible edits within that folder, but must not expand to other folders or destructive operations.
- **Commit externally:** sending, publishing, submitting, sharing, purchases, account/security changes, and deletion require a fresh confirmation showing the exact destination and content/effect. A task grant cannot silently approve these.
- **Restricted:** credentials, hidden recording, permission bypass, stealth control, and arbitrary remote execution are not available capabilities.

### Engineering rules

- Prefer one clear approval at the start of a bounded low-risk task over repeated approval dialogs for each navigation step.
- Approval must be revocable and scoped; expiry, device change, capability change, or material task change invalidates it.
- Keep a visible activity indicator and concise audit history, but do not log private screen contents or text payloads by default.
- When a capability is unavailable, explain the exact missing permission, adapter, or platform limitation and offer a supported alternative. Do not fail the whole task if an independent safe step can still complete.
- Never claim a task completed until the adapter returns verifiable success. Report partial completion and skipped steps separately.
- Security controls must be tested for both sides: unauthorized actions are blocked, while authorized routine tasks complete without unnecessary prompts.

**Current implementation note:** the native Android bridge currently asks for approval per queued action. This is intentionally conservative during the initial validation phase, but it is not the desired final interaction model for routine navigation. A bounded, revocable task grant for low-risk actions is a planned usability improvement and must be implemented with tests before it is enabled. Consequential actions keep exact-action approval.

## 11. Current Human Hand implementation progress

The shared capability controller is now present in `src/zexa/capabilities.py`. It owns trusted capability definitions, platform labels, permission names, risk levels, typed JSON input/output contracts, bounded payload sizes, and dispatch to application-registered handlers. It delegates authorization, one-use approvals, and audit events to the existing `ExecutionGateway`.

Android action definitions are created by `src/zexa/android_capabilities.py`. The CLI's `bridge action` path now routes through this shared controller before calling the existing `AccessibilityBridge`. The command requires all of the following:

1. The action is in the explicit `ZEXA_ALLOWED_ANDROID_ACTIONS` allowlist.
2. The caller reviews and types `APPROVE` for the exact action and payload.
3. The shared controller validates the registered capability, permission, risk, and one-use approval.
4. The Android companion app independently confirms the exact action through its native approval flow.

The capability controller is a foundation for future laptop and browser adapters; it does not itself implement laptop pairing, browser automation, or new Android gestures. Those adapters must register their own trusted contracts and pass platform-specific integration tests before they are advertised as available.
