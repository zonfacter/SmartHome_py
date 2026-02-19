# Security Policy

## Supported Scope
This project includes backend services, frontend assets, gateway integrations, and deployment manifests.

## Reporting a Vulnerability
Please report security issues privately via GitHub Security Advisories:
- https://github.com/zonfacter/SmartHome_py/security/advisories/new

Do not open public issues for active vulnerabilities that could be exploited.

## Secrets Handling Rules
- Never commit real secrets (API keys, DSN, passwords, tokens) to the repository.
- `.env.example` must only contain placeholders or empty values.
- Documentation must use redacted examples only.
- Use environment variables or secret stores for runtime credentials.

## Mandatory Response if a Secret is Exposed
1. Revoke/rotate the exposed secret immediately.
2. Audit provider-side access logs for suspicious usage.
3. Replace all affected configurations and redeploy.
4. Document incident timeline and mitigation in a dedicated issue.
5. Add/adjust detection guardrails (CI scanning, rules, checks).

## Repository Guardrails
- Secret scanning in CI (gitleaks workflow).
- Dependency vulnerability scanning in CI (python/node workflows).
- Protected branch with required checks and review.

## Hardening Baseline
- Protected control endpoints require auth.
- Critical endpoints are rate-limited.
- Session/CORS/origin controls are enabled for admin/control paths.
- Input validation is enforced for external ingress.
