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

This is a first integration, not a claim that every Zexa execution path is protected. The gateway is not yet wired into all skill dispatch, agent orchestration, notification/background workers, browser automation, or future external integrations. Do not connect a new side-effecting tool until it has a trusted capability definition and routes through the gateway.

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

- Route every skill/tool dispatch through the same gateway.
- Add denial/approval tests for the CLI bridge and background workers.
- Add cancellation, timeout, idempotency and recovery semantics to long-running tasks.
- Verify Android behavior on the actual supported handset and OS build.
- Review third-party skills for provenance, license, dependencies, schemas and security before enabling them. Imported content is untrusted and never executable by default.


## Unified skill execution engine

`zexa skill list` prints the registered skill contracts. Run a pure-LLM draft or analysis skill with a JSON object matching its declared input schema:

```bash
zexa skill run proposal_writer '{"service":"Website design","client_needs":"A small business website","scope_timeline_pricing":"Scope and pricing to be confirmed"}'
```

The command validates the skill input, calls only the selected trusted brain-backed handler, requires a JSON response matching the declared output schema, and routes the invocation through `ExecutionGateway`. It does not send messages, publish content, make payments, or execute shell commands. High/critical skills require a fresh typed approval. Additional skill permissions must be explicitly listed in the local `ZEXA_SKILL_PERMISSIONS` environment variable.

The engine API is in `zexa.execution.SkillExecutionEngine`. Application code supplies trusted handlers; model output cannot register a handler or provide executable code. `skill_capabilities(registry)` creates the gateway's trusted action/permission/risk map from the registry.
