# Contributing

## Workflow
- Create a feature branch from the current integration branch.
- Keep PRs scoped and small.
- Ensure CI is green before requesting review.

## Security Requirements
- Never commit real credentials, tokens, passwords, or DSNs.
- Use placeholders in docs and examples.
- If you suspect a leak, stop and report immediately.

## Validation Minimum
Run before opening a PR:

```bash
make smoke
```

For a full local CI-equivalent run:

```bash
make test
```

## PR Checklist
- Code changes are minimal and focused.
- Tests or validation steps were executed.
- Relevant docs were updated.
- No secrets are present in changed files.
