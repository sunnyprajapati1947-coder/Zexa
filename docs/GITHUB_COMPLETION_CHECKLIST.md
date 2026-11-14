# GitHub-side completion checklist

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
- [x] Android CI runs JVM unit tests and builds the debug APK.
- [x] Pending Dependabot action-version updates are consolidated in this branch to avoid overlapping workflow changes.

## Still requires real-device / account verification

- [ ] Install the current branch on the OPPO Android 16 device and validate Termux commands. (Not performed by GitHub CI.)
- [ ] Enable Accessibility manually and test the local bridge, approval prompts, and every supported action. (Not performed by GitHub CI.)
- [ ] Validate Termux:Services and optional Termux:Boot across app restart and device reboot. (Not performed by GitHub CI.)
- [ ] Verify notifications, Doze/battery restrictions, process recovery, and queue persistence on-device. (Not performed by GitHub CI.)
- [ ] Confirm the installed APK on the physical device; CI assembly is not a device test.

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
- [ ] Physical OPPO Android 16 validation remains outstanding.

## Pull request state

- PR #16 is a draft against `main`; no merge has been performed.
- The separate Dependabot PRs remain open. Their action-version changes are included in this branch; they can be closed as superseded after PR #16 is merged.
- Imported skill references remain disabled. A skill becomes executable only after an individual review, trusted native handler, permission definition, tests, and explicit enablement path.
