import pathlib
import re


ROOT = pathlib.Path(__file__).resolve().parent

# Matches real-looking Sentry DSN strings, e.g.
# https://<32 hex>@o123.ingest.de.sentry.io/12345
SENTRY_DSN_PATTERN = re.compile(
    r"https://[a-fA-F0-9]{32}@o\d+\.ingest\.[A-Za-z0-9.-]+\.sentry\.io/\d+"
)

TEXT_EXTENSIONS = {
    ".py",
    ".md",
    ".txt",
    ".yml",
    ".yaml",
    ".env",
    ".example",
    ".json",
    ".toml",
    ".ini",
    ".cfg",
    ".sh",
    ".js",
    ".ts",
}

SKIP_PARTS = {
    ".git",
    ".venv",
    "__pycache__",
    "node_modules",
    "artifacts",
}


def _is_text_candidate(path: pathlib.Path) -> bool:
    suffix = path.suffix.lower()
    if suffix in TEXT_EXTENSIONS:
        return True
    # allow files like ".env.example"
    if path.name.endswith(".example"):
        return True
    return False


def _iter_candidate_files():
    for path in ROOT.rglob("*"):
        if not path.is_file():
            continue
        if any(part in SKIP_PARTS for part in path.parts):
            continue
        if _is_text_candidate(path):
            yield path


def test_no_real_sentry_dsn_in_repository_files():
    offenders = []
    for path in _iter_candidate_files():
        try:
            content = path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        if SENTRY_DSN_PATTERN.search(content):
            offenders.append(str(path.relative_to(ROOT)))

    assert offenders == [], f"Potential real Sentry DSN found in: {offenders}"


def test_env_example_keeps_sentry_placeholder_only():
    env_example = ROOT / ".env.example"
    content = env_example.read_text(encoding="utf-8")
    assert 'SENTRY_DSN=""' in content
