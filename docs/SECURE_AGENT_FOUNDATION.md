# Secure Agent Foundation — implementation status

This branch adds a deny-by-default execution foundation and a first end-to-end integration point.

## Implemented

- `zexa.policy.PermissionPolicy`: explicit permission allowlist and risk-based approval decisions.
- `zexa.approvals.ApprovalManager`: short-lived, one-time grants bound to the exact action and canonical payload.
- `zexa.audit.AuditLog`: local SQLite audit events with sensitive-key and bearer-token redaction.
- `zexa.gateway.ExecutionGateway`: trusted capability registry; permission, risk and approval validation; execution outcome auditing. Capability risk comes from trusted application configuration, not model output.
- `zexa bridge action`: Android bridge action requests now pass through the gateway, after the operator enables the action in a local allowlist and confirms the exact displayed action and JSON payload.

## Android action opt-in

Add only the capabilities you intend to allow to the local, untracked `.env` file:

```dotenv
ZEXA_ALLOWED_ANDROID_ACTIONS=back,home,tap
# Optional; defaults to ~/.zexa/audit.sqlite3
ZEXA_AUDIT_DB=/data/data/com.termux/files/home/.zexa/audit.sqlite3
```

The supported values are `tap,swipe,scroll,back,home,input_text,launch_app`. Each enabled action is classified as high risk and requires a fresh typed confirmation every time. The bridge's local token and Android Accessibility permission are still required. Do not put the bridge token in a command, screenshot, issue, or audit record.

An action omitted from the allowlist is denied. Remove it from `ZEXA_ALLOWED_ANDROID_ACTIONS` to disable it. Audit records are local; inspect the SQLite database only on the user's device.

## Important limitations

This is a first guarded execution layer, not a claim that every Zexa execution path is protected. The `zexa skill run` path, low-risk background skill jobs, and Android bridge actions are routed through the gateway. The legacy text-only specialist-agent orchestration and generic read-only tools are not yet all routed through it; they currently have no general-purpose side-effecting handlers. Browser automation and future external integrations must not be connected until they have trusted capability definitions and route through the gateway.

The permission allowlist currently comes from local environment configuration; a dedicated settings UI, persistent grant/revocation workflow, and per-capability management are future work. The audit log intentionally avoids raw action payloads and exception text, but it is not a complete data-loss-prevention system.

## Local verification

Run from the repository root:

```bash
python -m pip install -e .
python -m compileall -q src tests
python -m unittest discover -s tests -v
```

No claim of successful tests or Android runtime verification should be made until those commands and a real device check have actually completed.

## Remaining integration work

- Route any future side-effecting specialist-agent/tool adapter through the same gateway; the existing specialist agents remain text-only.
- Add real-device denial/approval tests for the CLI bridge and Termux worker lifecycle.
- Add timeout enforcement, idempotency and stronger cancellation semantics to long-running tasks.
- Verify Android behavior on the actual supported handset and OS build.
- Review third-party skills for provenance, license, dependencies, schemas and security before enabling them. Imported content is untrusted and never executable by default.


## Unified skill execution engine

`zexa skill list` prints the registered skill contracts. Run a pure-LLM draft or analysis skill with a JSON object matching its declared input schema:

```bash
zexa skill run proposal_writer '{"service":"Website design","client_needs":"A small business website","scope_timeline_pricing":"Scope and pricing to be confirmed"}'
```

The command validates the skill input, calls only the selected trusted brain-backed handler, requires a JSON response matching the declared output schema, and routes the invocation through `ExecutionGateway`. It does not send messages, publish content, make payments, or execute shell commands. High/critical skills require a fresh typed approval. Additional skill permissions must be explicitly listed in the local `ZEXA_SKILL_PERMISSIONS` environment variable.

The engine API is in `zexa.execution.SkillExecutionEngine`. Application code supplies trusted handlers; model output cannot register a handler or provide executable code. `skill_capabilities(registry)` creates the gateway's trusted action/permission/risk map from the registry.


## Background skill jobs

The durable worker can process low-risk drafting/analysis jobs. Queue one:

```bash
zexa schedule-skill general_assistant '{"prompt":"Draft a polite reply to a customer asking about website design services."}'
```

Start the worker once:

```bash
zexa worker --once
```

Or keep it polling:

```bash
zexa worker --poll-seconds 5
```

The worker routes the job through `SkillExecutionEngine` and `ExecutionGateway`, writes the normal audit events, and sends a Termux notification when the result is ready. Only low-risk skills are accepted by the background queue. Medium/high/critical skills must be run interactively and, where required, receive a fresh approval; approval tokens are intentionally not persisted in the job database. Failed jobs use the existing bounded retry policy. The worker is a foreground process until installed/configured as an Android service; this change does not claim automatic boot persistence or guaranteed Android background survival.


## Job queue reliability and Termux service configuration

The job queue now defaults to `~/.zexa/jobs.sqlite3` and accepts `ZEXA_JOB_DB` to override the path. This avoids separate queues when the CLI and runit service start from different working directories. `ZEXA_ENV_FILE` selects the environment file; it is loaded before queue scheduling and worker startup.

- `zexa job cancel ID` cancels pending jobs only; running work is not falsely reported as cancelled.
- `zexa job retry ID` requeues failed jobs with a fresh bounded attempt budget.
- Worker exceptions persist only the exception class, not exception messages that could contain customer text, provider output, or credentials.
- `scripts/install-termux-worker.sh` generates a runit service entrypoint for the exact checkout, configures stable queue/audit paths, and enables the service through Termux:Services.
- Android reboot startup still depends on Termux:Boot being installed and configured. Android Doze, battery optimization, process death, and real-device lifecycle behavior are not verified from GitHub CI.

The current CI validates Python behavior on Linux; it does not validate Termux, Android notifications, AccessibilityService, or physical device lifecycle.
