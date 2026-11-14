# Secure Agent Foundation — implementation status

This branch adds two standard-library-only building blocks:

- `zexa.policy.PermissionPolicy`: explicit permission allowlist, deny-by-default decisions, and approval gates for high/critical risk.
- `zexa.audit.AuditLog`: local SQLite event persistence with recursive sensitive-key and bearer-token redaction.

## Current limitations

These modules are deliberately standalone. They are **not yet wired into every CLI, Android bridge, skill handler, background worker, or external integration**. Do not treat their presence as proof that all Zexa actions are centrally protected.

The existing `ApprovalManager` remains a separate one-time, action/payload-bound primitive. A production execution gateway still needs to combine:
1. validated skill/tool schemas;
2. the permission decision;
3. an action-bound approval grant for consequential actions;
4. audit records for allow/deny/start/result/failure;
5. cancellation, timeout, and idempotency controls.

## Local verification

Run from the repository root:

```bash
python -m pip install -e .
python -m unittest tests.test_policy_audit -v
python -m unittest discover -s tests -v
```

## Required next integration work

- Route all tool dispatch through one execution gateway.
- Derive required permissions and risk from trusted registered tool metadata, never from model output.
- Persist grants and revocations only through an explicit user-controlled settings path.
- Require fresh confirmation bound to the exact action and canonical arguments.
- Record audit metadata without storing raw screen contents, credentials, OTPs, or private message bodies.
- Add integration tests for CLI, worker, and Android bridge denial paths.
- Verify Android behavior on the actual supported handset and OS build.

No imported third-party skill is executable by default. Imported content remains untrusted and must pass provenance, license, dependency, schema, and security review before an operator enables it.
