#!/usr/bin/env python3
"""Parse a unified git diff into structured JSON for review.

Usage:
    git diff main...HEAD | python3 parse_diff.py
    python3 parse_diff.py --file changes.diff

Output: JSON with per-file hunks, added/removed lines, and positions
suitable for anchoring inline review comments.
"""
import argparse
import json
import re
import sys

HUNK_RE = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")


def parse(diff_text: str) -> dict:
    files = []
    current = None
    hunk = None
    old_line = new_line = 0

    for raw in diff_text.splitlines():
        if raw.startswith("diff --git"):
            current = {"old_path": None, "new_path": None, "status": "modified", "hunks": []}
            files.append(current)
            hunk = None
        elif raw.startswith("new file mode"):
            current["status"] = "added"
        elif raw.startswith("deleted file mode"):
            current["status"] = "deleted"
        elif raw.startswith("rename from "):
            current["status"] = "renamed"
            current["old_path"] = raw[len("rename from "):]
        elif raw.startswith("rename to "):
            current["new_path"] = raw[len("rename to "):]
        elif raw.startswith("--- "):
            p = raw[4:]
            current["old_path"] = None if p == "/dev/null" else p.removeprefix("a/")
        elif raw.startswith("+++ "):
            p = raw[4:]
            current["new_path"] = None if p == "/dev/null" else p.removeprefix("b/")
        elif m := HUNK_RE.match(raw):
            old_line, new_line = int(m.group(1)), int(m.group(3))
            hunk = {"old_start": old_line, "new_start": new_line, "lines": []}
            current["hunks"].append(hunk)
        elif hunk is not None:
            if raw.startswith("+") and not raw.startswith("+++"):
                hunk["lines"].append({"type": "added", "new_line": new_line, "content": raw[1:]})
                new_line += 1
            elif raw.startswith("-") and not raw.startswith("---"):
                hunk["lines"].append({"type": "removed", "old_line": old_line, "content": raw[1:]})
                old_line += 1
            elif raw.startswith(" "):
                hunk["lines"].append({"type": "context", "old_line": old_line, "new_line": new_line, "content": raw[1:]})
                old_line += 1
                new_line += 1

    # summary stats
    for f in files:
        f["added_lines"] = sum(1 for h in f["hunks"] for l in h["lines"] if l["type"] == "added")
        f["removed_lines"] = sum(1 for h in f["hunks"] for l in h["lines"] if l["type"] == "removed")
    files = [f for f in files if f["new_path"] or f["old_path"]]
    return {
        "files": files,
        "stats": {
            "files_changed": len(files),
            "total_added": sum(f["added_lines"] for f in files),
            "total_removed": sum(f["removed_lines"] for f in files),
        },
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", help="diff file path (default: stdin)")
    args = ap.parse_args()
    text = open(args.file).read() if args.file else sys.stdin.read()
    json.dump(parse(text), sys.stdout, indent=2)
    print()


if __name__ == "__main__":
    main()
