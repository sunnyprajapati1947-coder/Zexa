# Legacy Assistant Consolidation Audit

Date: 2026-11-14
Target: `feature/qwen-xai-multi-brain`
Policy: preserve the existing Zexa implementation; migrate only reviewed, compatible capabilities.

## Scope and evidence

This audit uses the available prior conversation history and the GitHub repositories currently visible under the user's account. It is not a claim that every historical local folder or every past chat has been inspected.

| Project / repository | What is currently verifiable | Consolidation status |
|---|---|---|
| SunnyAI / Nova — `sunnyprajapati1947-coder/Sunny-` | Public repository exists. Current README describes a Google model-routing registry and a separate local Nova automation pipeline. Source tree includes a local-agent submodule copy, tool registry/router/bridge, Termux tools, security policy, approval gate, kill switch, audit log, task queues, verifier/repair, watchdog, YouTube queue and tests. | Source candidate; review before porting. Do not copy wholesale. |
| Spdyi-AI — `sunnyprajapati1947-coder/Spidy-ai` | Private repository is visible, but currently has only a 10-byte README in its main branch. | No implementation verified in this remote repository. Check local archives/folders before concluding project was empty. |
| ZIXU — `sunnyprajapati1947-coder/Zixu` | Public repository exists but GitHub reports it is empty. | No remote source to migrate. Check local archives/folders. |
| ALEXA | Prior conversation records describe a Groq configuration/API step as pending. No matching user-owned repository was confirmed in the current GitHub account search. | Historical project; implementation not yet located. |
| Jarvis-Groq | Prior conversation records describe a separate Open-Jarvis-based plan, with APK build and device testing pending. A user-owned repository was not confirmed. | Historical plan; implementation not yet located. |
| Zexa | Current repository and active feature branch exist. Latest phone audit: compilation passed; 126 unit tests passed; CLI and worker available; Termux APIs available; Qwen inference was not tested successfully because the test command used an unsupported `-no-cnv` flag; Android bridge port 8765 was not listening. SQLite ResourceWarnings remain. | Active consolidation target; not complete. |

## User's current target constraints

- Zexa is the single consolidated assistant project.
- Qwen/local is the selected brain for the current build; do not add new cloud-provider dependencies as part of this consolidation.
- Keep the existing phone-first Termux worker and Android bridge design.
- Preserve explicit user approval for sensitive Android/device actions.
- Preserve existing files and user data. In particular, do not delete or overwrite local untracked `Zexa/` or `sources/` directories.
- Do not merge into `main` without explicit permission.

## Reusable capabilities found in Sunny-/Nova source

Potential candidates, subject to code-level review, dependency compatibility, and tests:

1. Tool registry with JSON argument validation and unknown-argument rejection.
2. Tool router that only selects tool schemas and does not execute tools.
3. Central tool bridge with policy, audit, approval and kill-switch boundaries.
4. One-time approval bound to the exact tool and argument payload.
5. Termux capability adapters.
6. Persistent task queue with verification and bounded repair attempts.
7. Bounded watchdog/self-heal pattern that only stops a process it owns.
8. Source-led web research that treats fetched content as untrusted evidence.
9. Private-by-default media queue and explicit approval before external publishing.
10. Regression tests for tool boundaries, approval, untrusted input, verification and recovery.

## Known risks and fixes to verify

- Qwen command-line flags must be checked against the installed llama.cpp build before documenting inference as working.
- The current model file is a Qwen2.5 3B Instruct GGUF; ensure the adapter uses the model's embedded chat template and a tested llama.cpp invocation.
- The phone audit emitted repeated SQLite unclosed-connection ResourceWarnings. Identify and close the originating connections; do not suppress warnings as a fix.
- The Android bridge port was not listening during the last audit. Verify APK installation, Accessibility permission, service lifecycle, loopback binding and authentication separately.
- Worker running status does not prove reboot persistence. Test Termux:Boot after a controlled reboot before marking auto-start complete.
- A passing unit suite does not prove live Qwen inference, real Android actions, network research, or background reliability.
- Do not import Nova's Google provider registry or historical Groq-only provider plan into the current Qwen-only Zexa configuration.
- Do not blindly import shell, filesystem, browser, OCR, phone-control or upload tools. Each must be allowlisted, schema-validated, least-privileged, audited and approval-gated where appropriate.

## Migration gate

A legacy feature may be marked migrated only when all are true:

- Its original source and license are identified.
- The exact files and dependencies are reviewed.
- The Zexa equivalent is checked to avoid duplicate implementations.
- The feature is adapted to Zexa interfaces rather than copied with conflicting globals, paths or configuration.
- Unit tests and negative/security tests are added.
- Phone-level test is completed where the feature needs Android/Termux.
- Documentation states limitations and whether the feature is enabled, disabled or experimental.

## Next required inspection

The local Termux folders `~/Zexa/Zexa` and `~/Zexa/sources` are untracked and were not readable through the GitHub repository view. Inventory these directories before any import or cleanup. They may contain the actual historical project source not present in the remote repositories.
