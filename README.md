# ultimate-pr-review

An AI agent skill that reviews pull requests and code diffs like a senior engineer — deterministic scanning first (secrets, risky patterns, missing tests), then semantic analysis (security, correctness, performance, tests), reported as a structured review anchored to exact files and lines.

## What it does

- **Deterministic prescan** (`scripts/prescan.py`) — flags hard-coded secrets, risky patterns, and signals (no-tests, config-change, db-migration, large-pr). Exits `1` on any critical finding, so it doubles as a CI gate.
- **Diff parsing** (`scripts/parse_diff.py`) — emits structured line positions for anchoring inline PR comments.
- **Semantic review rubric** (`references/review-checklist.md`) — guides the deeper pass across security, correctness, performance, and tests.
- **Structured verdict** — approve / approve with comments / request changes, with blockers, majors, nits, questions, and suggested fixes.

## Repo layout

```
SKILL.md                        # Skill definition and review workflow
references/review-checklist.md  # Semantic review rubric
scripts/prescan.py              # Deterministic scanner (CI-gate ready)
scripts/parse_diff.py           # Diff parser for inline-comment positions
tests/sample.diff               # Example fixture with planted issues
```

## Usage

### As an agent skill

Drop the folder into your agent's skills directory. The skill triggers on requests like "review this PR", "check this diff before merging", or "find security issues in these changes". It accepts diffs from files, stdin, `git diff`, pasted text, or PR URLs (via `gh pr diff`).

### Standalone (no agent)

```bash
# Prescan a diff — exits 1 on critical findings
git diff origin/main...HEAD | python3 scripts/prescan.py --format text

# Get structured line positions for inline comments
git diff origin/main...HEAD | python3 scripts/parse_diff.py
```

### As a CI gate

```yaml
- run: git diff origin/main...HEAD | python3 scripts/prescan.py --format text
```

This repo dogfoods its own gate: [.github/workflows/pr-prescan.yml](.github/workflows/pr-prescan.yml) runs the prescan on every pull request and fails the check on any critical finding.

## Notes

- If a repo contains `REVIEW_GUIDE.md` (or `.review-guide.md` / `docs/review-guide.md`), its rules override generic style opinions.
- Reviews and inline comments are only posted with explicit user confirmation.
