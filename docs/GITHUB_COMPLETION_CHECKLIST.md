# GitHub-side completion checklist

## Standalone Android app status (2026-11-15)

The Android project now includes a native workspace shell, GGUF import/integrity handling, a pinned llama.cpp JNI CPU runtime and a multi-turn local chat UI. The latest verified CI run `43671195011` passed and produced an APK containing the arm64 native library. Android CI run `43671941890` passed for app-private SQLite persistence of completed chat turns and a confirmed clear-history action. A subsequent change adds explicit on-device speech input, optional Android TTS output and a WorkManager-backed local reminder screen with notification permission, cancel-all control and reminder validation tests. The first CI attempt exposed a missing `android.useAndroidX=true` setting; `gradle.properties` now enables AndroidX and the workflow watches that file. Android CI run `43672962839` completed successfully, including JVM tests, native CMake compilation and debug APK assembly. Voice/reminder target-device verification remains outstanding. Native Android per-action approval now includes an exact-payload review screen, one-use 60-second tickets, a notification when permission is available, and a Python polling client; Android CI is running for this integration and physical-device validation remains outstanding. It is not yet the full Zexa assistant: semantic memory/RAG, full task management and several security/lifecycle features remain incomplete. Do not mark Termux-free daily use complete until all of the following are implemented and device-tested:

- [x] Native Android workspace shell with Home, Chat, Brain, Tasks, Memory and Device sections; unfinished modules are explicitly marked pending.
- [x] Android bridge action requests are queued with HTTP 202 and require exact-payload native confirmation; a bearer token alone never executes an action.
- [x] Native multi-turn chat UI wired to the local llama.cpp/Qwen adapter; recent history is bounded.
- [x] App-private SQLite persistence for completed chat turns and a confirmed clear-history action (Android CI run `43671941890` passed; physical-device persistence check remains outstanding).
- [x] arm64 llama.cpp JNI runtime integration, GGUF import into app-private storage, 10 GiB size cap, header validation, SHA-256 verification before load, CPU inference configuration and RAM warning.
- [x] Verify the voice/reminder integration build in CI (run `43672962839`); JVM tests, native CMake compilation and debug APK assembly passed.
- [ ] Install the APK and run actual Qwen inference on the target Android 16 device; assess memory, thermals, voice language-pack availability and supported GGUF templates.
- [ ] Online provider setup with secure Android Keystore-backed credential storage; no API keys in source, logs, or clipboard.
- [x] Explicit Android on-device speech recognition wired into Chat, with runtime microphone permission, visible status, cancellation on navigation, Hindi locale preference and review-before-send.
- [ ] Verify voice input with Hindi/Hinglish offline language packs on the target Android 16 device; confirm installed TTS voice behavior and lifecycle.
- [ ] Verify WorkManager reminder delivery, cancellation, reboot recovery, notification permission denial and Doze/battery behavior on the target Android 16 device.
- [x] Explicit personal-memory facts with local SQLite save, edit, case-insensitive search, individual delete and confirmed clear-all; up to 100 facts of 500 characters each. Up to 10 facts/3,000 characters are supplied as reference context to local chat.
- [ ] Semantic search/RAG and physical-device memory persistence verification.
- [x] User-initiated personal memory JSON export through Android's document picker (Android CI verification pending).
- [x] Basic local reminder scheduling via WorkManager, pending-reminder list, individual confirmed cancellation and cancel-all, with Android 13+ notification permission and a bounded 1-minute to 7-day delay (Android build verification pending; physical-device delivery verification outstanding).
- [ ] Full task management, reminder editing/history, reminder notification deep links and target-device Doze/reboot validation.
- [ ] Native settings and health dashboard for brain, model, permissions, worker and bridge state.
- [ ] Android execution gateway, durable approval/audit state, and physical-device confirmation-flow validation.
- [x] Native Device-section approval UI, exact action/payload display, 60-second expiry, eight-request queue limit, one-use approve/deny, HTTP 202 queue protocol, result polling, Python client wait flow, and notification deep-linking to the matching approval dialog (latest Android CI and physical-device validation outstanding; Device refresh remains available as fallback).
- [ ] Accessibility bridge lifecycle recovery, token rotation/revocation, durable request/result state and sensitive-screen redaction; one-use in-memory request IDs and replay rejection are implemented.
- [ ] Android unit/instrumentation tests, release signing, install/upgrade tests and target-device acceptance on Android 16.

Termux remains a development/migration tool until this checklist is complete. Do not advertise the current APK as a full assistant.

This file separates work that is implemented and CI-verified on the feature branch from work that requires a real Android device, external credentials, or a deliberate product decision.

## Implemented on this branch

- [x] Deny-by-default permission policy and trusted capability metadata.
- [x] Exact-action, exact-payload, one-use approval tokens for consequential actions.
- [x] Local SQLite audit events with sensitive-value redaction.
- [x] Android bridge CLI actions routed through the execution gateway and an explicit local allowlist.
- [x] Unified skill execution engine with input/output schema validation and trusted native handlers.
- [x] Brain-backed drafting/analysis adapters that accept JSON output only and do not execute model-generated code.
- [x] Sequential specialist-agent handoff includes bounded prior outputs as untrusted reference data.
- [x] Planner validates exact JSON fields, registered skill names, and bounded goal/task lengths.
- [x] Low-risk background skill jobs routed through the same skill engine and gateway.
- [x] Stable job database path, early environment-file loading, pending-job cancellation, failed-job retry, and safe error identifiers.
- [x] Termux:Services installer and optional Termux:Boot startup hook.
- [x] 320 pinned community skill references imported with provenance and SHA-256 metadata; all are disabled, and one requires manual review.
- [x] Read-only `zexa skillpacks status/list` commands; imported references are not executable capabilities.
- [x] Android bridge limits concurrent clients, reports actual readiness, and can recover after a bind failure.
- [x] Android bridge JVM unit tests cover token comparison, body-size limits, coordinates, gesture duration, and package-name validation.
- [x] Python CI covers 3.11, 3.12, and 3.13; Termux shell scripts are syntax-checked.
- [x] Python CodeQL security analysis workflow.
- [x] Android CI runs JVM unit tests and builds the debug APK; run `43671195011` passed for commit `ee4ec705eddf04d0fb7c2085ef3aefbca9f931d9`.
- [x] Android CI run `43671941890` passed for the app-private SQLite chat-history integration.
- [x] Pending Dependabot action-version updates are consolidated in this branch to avoid overlapping workflow changes.

## Still requires real-device / account verification

- [ ] Install the current branch on the OPPO Android 16 device and validate Termux commands. (Not performed by GitHub CI.)
- [ ] Enable Accessibility manually and test the local bridge, approval prompts, and every supported action. (Not performed by GitHub CI.)
- [ ] Validate Termux:Services and optional Termux:Boot across app restart and device reboot. (Not performed by GitHub CI.)
- [ ] Verify notifications, Doze/battery restrictions, process recovery, and queue persistence on-device. (Not performed by GitHub CI.)
- [ ] Confirm the installed APK on the physical device; CI assembly is not a device test.
- [ ] Test microphone permission, on-device speech recognition, Hindi/Hinglish language pack behavior and installed TTS voice on the OPPO Android 16 device.

## Product integrations not yet implemented

- [ ] Browser automation adapter and controlled browser session lifecycle.
- [ ] Production email, calendar, CRM, and messaging connectors with OAuth and revocation.
- [ ] A general MCP runtime and reviewed tool registry.
- [ ] Route every future side-effecting tool through the execution gateway.
- [ ] Durable long-running task cancellation/heartbeat and idempotency for external side effects.
- [ ] Semantic memory/RAG with retention and deletion controls.
- [ ] Kotlin/Android static analysis and Android instrumentation tests.
- [ ] Signed release build, release provenance/SBOM, and repository-level secret-scanning configuration.

## Latest GitHub Actions verification

- [x] Zexa CI #284 passed on commit `43f5882` (Python 3.11/3.12/3.13; tests, byte-compilation, and Termux shell syntax).
- [x] CodeQL #113 passed on commit `43f5882`.
- [x] Android Bridge Build #70 passed on commit `43f5882` (Android SDK 36, JVM unit tests, and debug APK assembly).
- [x] Community skill import #13 passed; manifest records 320 references, 0 enabled, 1 flagged for manual review.
- [ ] Physical OPPO Android 16 validation remains outstanding, including GGUF import, SHA-256 verification, native model load, Hindi/Hinglish multi-turn chat, chat-history persistence/clear, RAM and thermal behavior.

## Pull request state

- PR #17 (`fix/reviewed-security-and-integrity`) is a draft against `feature/qwen-xai-multi-brain`; no merge has been performed.
- The separate Dependabot PRs remain open. Their action-version changes are included in this branch; they can be closed as superseded after PR #16 is merged.
- Imported skill references remain disabled. A skill becomes executable only after an individual review, trusted native handler, permission definition, tests, and explicit enablement path.
