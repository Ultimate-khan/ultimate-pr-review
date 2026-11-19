#!/usr/bin/env python3
"""Deterministic pre-scan of a diff: flags secrets, risky patterns, and
structural signals BEFORE the semantic review, so nothing mechanical is
left to model judgment.

Usage:
    git diff main...HEAD | python3 prescan.py
    python3 prescan.py --file changes.diff --format text

Exit code 1 if any critical finding (usable in CI gates).
"""
import argparse
import json
import re
import sys

SECRET_PATTERNS = [
    ("AWS access key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("GitHub token", re.compile(r"\b(ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{36,}\b")),
    ("Generic API key assignment", re.compile(r"(?i)(api[_-]?key|secret|token)\s*[:=]\s*['\"][A-Za-z0-9_\-]{20,}['\"]")),
    ("Private key block", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----")),
    ("Password literal", re.compile(r"(?i)password\s*[:=]\s*['\"][^'\"]{8,}['\"]")),
    ("Slack/Discord webhook", re.compile(r"https://hooks\.(slack|discord)\.com/[^\s'\"]+")),
    ("JWT literal", re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b")),
]

RISKY_PATTERNS = [
    ("critical", "Hardcoded localhost/internal URL", re.compile(r"https?://(localhost|127\.0\.0\.1|0\.0\.0\.0|10\.\d+\.\d+\.\d+|192\.168\.\d+\.\d+)")),
    ("high", "Debug/print statement", re.compile(r"^\+\s*(console\.log|print\(|debugger;|fmt\.Print|System\.out\.print)")),
    ("high", "Disabled security check", re.compile(r"(?i)(verify\s*=\s*False|rejectUnauthorized\s*:\s*false|--insecure|skip[_-]?ssl)")),
    ("high", "Broad exception swallow", re.compile(r"^\+\s*(except\s*:|except\s+Exception\s*(as\s+\w+)?\s*:\s*(pass|continue)|catch\s*\([^)]*\)\s*\{\s*\})")),
    ("medium", "TODO/FIXME/HACK added", re.compile(r"^\+\s*.*\b(TODO|FIXME|HACK|XXX)\b")),
    ("medium", "Commented-out code block", re.compile(r"^\+\s*(#|//|/\*)\s*(if|for|while|def |function|class)\b")),
    ("medium", "Dependency version unpinned", re.compile(r"^\+\s*[\"']?[\w@/-]+[\"']?\s*:\s*[\"']?(\*|latest)[\"']?\s*,?\s*$")),
    ("low", "Large single-line change", None),  # handled specially
]

CONFIG_FILES = re.compile(r"(Dockerfile|docker-compose|\.env|\.ya?ml|\.toml|\.ini|nginx\.conf|requirements\.txt|package\.json|go\.mod|Cargo\.toml)$")
TEST_FILE = re.compile(r"(test_|_test\.|\.test\.|\.spec\.|/tests?/|/spec/|__tests__/)")
MIGRATION_FILE = re.compile(r"(migration|schema|\.sql$)", re.I)


def scan(diff_text: str) -> dict:
    findings = []
    current_file = None
    new_line = 0
    added_by_file = {}
    touched_files = set()

    for raw in diff_text.splitlines():
        if raw.startswith("+++ "):
            p = raw[4:]
            current_file = None if p == "/dev/null" else p.removeprefix("b/")
            if current_file:
                touched_files.add(current_file)
                added_by_file.setdefault(current_file, 0)
        elif m := re.match(r"^@@ -\d+(?:,\d+)? \+(\d+)", raw):
            new_line = int(m.group(1))
        elif raw.startswith("+") and not raw.startswith("+++"):
            content = raw[1:]
            for name, pat in SECRET_PATTERNS:
                if pat.search(content):
                    findings.append({"severity": "critical", "category": "secret",
                                     "rule": name, "file": current_file, "line": new_line,
                                     "evidence": content.strip()[:120]})
            for sev, name, pat in RISKY_PATTERNS:
                if pat and pat.search(raw):
                    findings.append({"severity": sev, "category": "risk-pattern",
                                     "rule": name, "file": current_file, "line": new_line,
                                     "evidence": content.strip()[:120]})
            if len(content) > 500:
                findings.append({"severity": "low", "category": "risk-pattern",
                                 "rule": "Very long line added (possible minified/blob content)",
                                 "file": current_file, "line": new_line, "evidence": f"{len(content)} chars"})
            if current_file:
                added_by_file[current_file] += 1
                new_line += 1
        elif raw.startswith("-") and not raw.startswith("---"):
            pass
        elif raw.startswith(" "):
            new_line += 1

    # structural signals
    signals = []
    code_touched = [f for f in touched_files if not TEST_FILE.search(f)]
    tests_touched = [f for f in touched_files if TEST_FILE.search(f)]
    if code_touched and not tests_touched:
        signals.append({"severity": "medium", "signal": "no-tests",
                        "detail": "Code changed but no test files touched"})
    config_touched = [f for f in touched_files if CONFIG_FILES.search(f)]
    if config_touched:
        signals.append({"severity": "medium", "signal": "config-change",
                        "detail": f"Config/infra files changed: {', '.join(sorted(config_touched))}"})
    migrations = [f for f in touched_files if MIGRATION_FILE.search(f)]
    if migrations:
        signals.append({"severity": "high", "signal": "db-migration",
                        "detail": f"Schema/migration files changed: {', '.join(sorted(migrations))}"})
    total_added = sum(added_by_file.values())
    if total_added > 800:
        signals.append({"severity": "low", "signal": "large-pr",
                        "detail": f"{total_added} added lines; recommend splitting"})

    return {"findings": findings, "signals": signals,
            "summary": {"files": len(touched_files), "added_lines": total_added,
                        "critical": sum(1 for f in findings if f["severity"] == "critical")}}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", help="diff file path (default: stdin)")
    ap.add_argument("--format", choices=["json", "text"], default="json")
    args = ap.parse_args()
    text = open(args.file).read() if args.file else sys.stdin.read()
    result = scan(text)

    if args.format == "text":
        s = result["summary"]
        print(f"Prescan: {s['files']} files, +{s['added_lines']} lines, {s['critical']} critical findings")
        for f in result["findings"]:
            print(f"  [{f['severity']:8}] {f['rule']} @ {f['file']}:{f['line']}")
        for sig in result["signals"]:
            print(f"  signal[{sig['severity']:8}] {sig['signal']}: {sig['detail']}")
    else:
        json.dump(result, sys.stdout, indent=2)
        print()

    sys.exit(1 if result["summary"]["critical"] else 0)


if __name__ == "__main__":
    main()
