#!/usr/bin/env python3
"""Validate every skill in skills/ against SKILL_AUTHORING.md.

Usage: python3 scripts/validate_skills.py [skill-name ...]
Exits non-zero when any skill has an error. Warnings do not fail the run.
"""
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
SKILLS = ROOT / "skills"

ALLOWED_KEYS = {"name", "description", "license", "allowed-tools", "metadata"}
CATEGORIES = {
    "getting-started", "agents", "models", "workflows", "memory-and-knowledge",
    "harness", "sandbox-and-browser", "connections", "server-and-frontend",
    "quality", "deploy-and-platform",
}
SECTIONS = [
    "When to use", "When NOT to use", "Required inputs", "The framework",
    "Workflow", "Failure patterns", "Output format", "Reference files",
]
SKILL_MD_CAP = 500
REF_CAP = 500


def parse_frontmatter(text):
    match = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
    if not match:
        return None, text
    return yaml.safe_load(match.group(1)), text[match.end():]


def check_skill(path):
    errors, warnings = [], []
    skill_md = path / "SKILL.md"
    if not skill_md.exists():
        return ["SKILL.md missing"], warnings
    text = skill_md.read_text()
    try:
        fm, body = parse_frontmatter(text)
    except yaml.YAMLError as exc:
        return [f"invalid YAML frontmatter: {exc}"], warnings
    if not isinstance(fm, dict):
        return ["missing or invalid frontmatter"], warnings

    extra = set(fm) - ALLOWED_KEYS
    if extra:
        errors.append(f"unexpected frontmatter keys: {sorted(extra)} (put catalog fields under metadata)")
    if fm.get("name") != path.name:
        errors.append(f"name '{fm.get('name')}' does not match folder '{path.name}'")
    desc = str(fm.get("description", "")).strip()
    if not desc:
        errors.append("description missing")
    if len(desc) > 1024:
        errors.append(f"description too long ({len(desc)} > 1024)")
    if "<" in desc or ">" in desc:
        errors.append("description contains angle brackets")
    meta = fm.get("metadata") or {}
    if meta.get("category") not in CATEGORIES:
        errors.append(f"metadata.category '{meta.get('category')}' not in allowed set")
    if not meta.get("catalog_summary"):
        errors.append("metadata.catalog_summary missing")
    elif len(str(meta["catalog_summary"])) > 140:
        warnings.append("catalog_summary over 140 characters")
    if not isinstance(meta.get("display_order"), int):
        warnings.append("metadata.display_order missing or not an integer")

    headers = re.findall(r"^## (.+)$", body, re.MULTILINE)
    canonical = [h for h in headers if not h.startswith("Deep dive")]
    found = []
    for h in canonical:
        for s in SECTIONS:
            if h == s or h.startswith(s + ":"):
                found.append(s)
                break
        else:
            errors.append(f"non-canonical section '## {h}'")
    if found != SECTIONS:
        errors.append(f"sections out of order or missing. Found: {found}")

    lines = text.count("\n") + 1
    if lines > SKILL_MD_CAP:
        errors.append(f"SKILL.md has {lines} lines (cap {SKILL_MD_CAP})")
    if "—" in text:
        warnings.append("SKILL.md contains em dashes")

    for link in re.findall(r"\]\((references/[^)#]+|scripts/[^)#]+)", text):
        if not (path / link).exists():
            errors.append(f"broken link: {link}")
    refs = path / "references"
    for required in ("api.md", "examples.md"):
        if not (refs / required).exists():
            errors.append(f"references/{required} missing")
    if refs.exists():
        for ref in refs.glob("*.md"):
            n = ref.read_text().count("\n") + 1
            if n > REF_CAP:
                warnings.append(f"references/{ref.name} has {n} lines (aim under 400)")
            if "—" in ref.read_text():
                warnings.append(f"references/{ref.name} contains em dashes")
    return errors, warnings


def main():
    names = sys.argv[1:]
    dirs = [SKILLS / n for n in names] if names else sorted(p for p in SKILLS.iterdir() if p.is_dir())
    failed = 0
    for d in dirs:
        errors, warnings = check_skill(d)
        status = "FAIL" if errors else "ok  "
        print(f"{status} {d.name}")
        for e in errors:
            print(f"     error: {e}")
        for w in warnings:
            print(f"     warn:  {w}")
        failed += bool(errors)
    print(f"\n{len(dirs) - failed}/{len(dirs)} skills valid")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
