# Security Policy

## Supported versions

Security fixes are applied to the current default branch. Older snapshots may not receive fixes.

## Reporting a vulnerability

Please do not publish credentials, tokens, private customer data, or exploitable vulnerability details in a public issue.

If GitHub Private Vulnerability Reporting is enabled for this repository, use the repository's **Security → Advisories → Report a vulnerability** flow. If that private reporting option is unavailable, contact the repository maintainer through a private channel before sharing technical details publicly.

## Scope and expectations

Please include:
- affected commit or release;
- affected component and Android/Python version, where relevant;
- impact and realistic reproduction conditions;
- a minimal proof of concept that does not access other users' data or disrupt services.

Do not include real API keys, bridge tokens, passwords, personal data, or third-party secrets in a report.

## Security design commitments

- Android bridge binds to loopback and is disabled until the user starts it.
- AccessibilityService must be manually enabled by the device owner.
- Screen reads are explicit; device actions require confirmation.
- No unrestricted shell execution is exposed as a general-purpose tool.
- External content is untrusted input and must not grant permissions.
- Secrets must remain outside source control and logs.
