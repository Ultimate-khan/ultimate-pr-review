---
name: ultimate-pr-review
description: Reviews pull requests and code diffs like a senior engineer, combining deterministic scanning (secrets, risky patterns, missing tests) with semantic analysis (security, correctness, performance, tests). Use when asked to review a PR, diff, patch, commit range, or code changes; to check code before merging; to find bugs or security issues in changes; or to write PR review comments for GitHub/GitLab. Handles diffs from files, stdin, git commands, or pasted text.
---

# PR Review

Review code changes the way a strong senior engineer does: deterministic
checks first, judgment second, then a structured report anchored to exact
files and lines.

## Workflow

### 1. Get the diff

Obtain the changes, in priority order:

1. Diff/patch file or pasted text provided by the user
2. `git diff <base>...HEAD` or `git diff --cached` in the working repo
3. A PR URL — fetch with `gh pr diff <number>` (GitHub) or `glab mr diff`

If only commit SHAs are given, use `git diff <sha1> <sha2>`. If nothing is
available, ask for the diff rather than reviewing whole files blindly.

### 2. Run the deterministic pre-scan

Never skip this. Secrets and mechanical risks must not depend on judgment:

```bash
git diff <base>...HEAD | python3 scripts/prescan.py --format text
```

Treat every `critical` finding as a confirmed `blocker`. Use `signals`
(no-tests, config-change, db-migration, large-pr) to focus the semantic pass.

For inline comment anchoring, get structured positions:

```bash
git diff <base>...HEAD | python3 scripts/parse_diff.py
```

### 3. Load the team's conventions

Look for `REVIEW_GUIDE.md`, `.review-guide.md`, or `docs/review-guide.md` in
the repo. If found, its rules override generic style opinions. If not found,
review against the rubric only and avoid taste-based nits.

### 4. Semantic pass

Read the full diff, then read surrounding code for anything non-obvious
(callers of changed functions, schema definitions, config consumers). Apply
the rubric in [references/review-checklist.md](references/review-checklist.md)
across security, correctness, performance, and tests.

Rules of engagement:

- Only report issues you can point to or reason about concretely. Zero real
  findings is a valid outcome — say the diff looks good and why.
- Distinguish "broken now" from "fragile later"; severity reflects that.
- For each major+ finding, include a suggested fix (code or precise steps).
- Do not review unchanged code unless the change breaks it.

### 5. Report

Output in this format:

```markdown
## PR Review — <one-line verdict: approve / approve with comments / request changes>

**Summary**: <2-3 sentences: what the change does, overall risk>

### Blockers
- **[file:line]** <issue> — <why it breaks> — <suggested fix>

### Major
- ...

### Minor / Nits
- ...

### Questions for the author
- ...

### What's done well
- <1-3 genuine observations; skip if nothing notable>
```

The verdict rule: any blocker → request changes; only major/minor → approve
with comments; nothing material → approve.

### 6. Optional: post inline comments

If the user has `gh` authenticated and asks to post, anchor comments using
the `new_line` positions from `parse_diff.py`:

```bash
gh pr review <number> --request-changes --body-file review.md
# or inline: gh api repos/{owner}/{repo}/pulls/{n}/comments -f path=... -F line=... -f body=...
```

Never post reviews or comments without explicit user confirmation.

## CI gate usage

`prescan.py` exits 1 on any critical finding, so it works directly as a
pipeline gate:

```yaml
- run: git diff origin/main...HEAD | python3 scripts/prescan.py --format text
```
