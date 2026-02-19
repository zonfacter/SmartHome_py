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
python3 -m py_compile start_web_hmi.py module_manager.py import_tpy.py
python3 -m compileall -q modules
venv/bin/python -m pytest -q test_web_manager_fix.py test_logging_system.py
```

## PR Checklist
- Code changes are minimal and focused.
- Tests or validation steps were executed.
- Relevant docs were updated.
- No secrets are present in changed files.
