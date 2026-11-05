#!/usr/bin/env python3
"""Regenerate the README skill catalog from SKILL.md frontmatter.

Usage:
  python3 scripts/generate_catalog.py          print the catalog
  python3 scripts/generate_catalog.py --write  rewrite README.md between markers
  python3 scripts/generate_catalog.py --check  exit 1 if README.md is stale
"""
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
README = ROOT / "README.md"
START, END = "<!-- CATALOG:START -->", "<!-- CATALOG:END -->"
CATEGORY_TITLES = [
    ("getting-started", "Getting started"),
    ("agents", "Agents"),
    ("models", "Models"),
    ("workflows", "Workflows"),
    ("memory-and-knowledge", "Memory, RAG, and storage"),
    ("harness", "Harness: durable agents, schedules, signals"),
    ("sandbox-and-browser", "Workspaces, sandboxes, and browsers"),
    ("connections", "Connections: MCP, A2A, ACP, channels, integrations"),
    ("server-and-frontend", "Server, client, frontend, and auth"),
    ("quality", "Evals, observability, and Studio"),
    ("deploy-and-platform", "Deployment, Mastra Platform, and CLI"),
]


def load_skills():
    skills = []
    for md in sorted((ROOT / "skills").glob("*/SKILL.md")):
        m = re.match(r"^---\n(.*?)\n---\n", md.read_text(), re.DOTALL)
        if not m:
            continue
        fm = yaml.safe_load(m.group(1)) or {}
        meta = fm.get("metadata") or {}
        skills.append({
            "name": fm.get("name", md.parent.name),
            "category": meta.get("category", ""),
            "summary": meta.get("catalog_summary", ""),
            "order": meta.get("display_order", 999),
        })
    return skills


def render(skills):
    out = [f"**{len(skills)} skills** across {len(CATEGORY_TITLES)} categories.", ""]
    for cat, title in CATEGORY_TITLES:
        rows = sorted((s for s in skills if s["category"] == cat), key=lambda s: (s["order"], s["name"]))
        if not rows:
            continue
        out += [f"### {title}", "", "| Skill | What it covers |", "|---|---|"]
        out += [f"| [`{s['name']}`](skills/{s['name']}/SKILL.md) | {s['summary']} |" for s in rows]
        out.append("")
    return "\n".join(out).rstrip() + "\n"


def main():
    catalog = render(load_skills())
    mode = sys.argv[1] if len(sys.argv) > 1 else ""
    if not mode:
        print(catalog)
        return
    text = README.read_text()
    pattern = re.compile(re.escape(START) + r".*?" + re.escape(END), re.DOTALL)
    updated = pattern.sub(f"{START}\n{catalog}{END}", text)
    if mode == "--check":
        sys.exit(0 if updated == text else 1)
    if mode == "--write":
        README.write_text(updated)
        print("README.md catalog updated")


if __name__ == "__main__":
    main()
