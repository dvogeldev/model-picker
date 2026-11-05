#!/usr/bin/env python3
"""refresh_assignments.py — daily catalog ingestion + context assignment refresh.

Run once a day (systemd user timer) or on demand (`/set-model update`).
Fetches fresh catalogs (warming the daily cache), recomputes each context's
model from the policy table below, and updates
~/.pi/agent/set-model.json. Entries with "lock": true are never touched.

Policy (from the model-picker taxonomy — deterministic, no LLM):
  deep-research    newest Kimi (moonshotai) flagship — long-context lineage
  coding           top flagship (non-preview) in the OpenRouter programming
                   ranking that is served on the Nous Portal
  reasoning        newest DeepSeek non-flash reasoning flagship
  image-generation newest Qwen max with vision input
  routing          newest MiniMax flash (cheap agentic dispatch)
  fast             cheapest value tier with long-context + agentic on Nous
  general          newest Z.ai GLM flagship (non-flash)
"""
import json
import os
import re
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from model_picker import OPENROUTER, fetch, merge  # noqa: E402

AGENT_DIR = os.environ.get("PI_CODING_AGENT_DIR") or os.path.expanduser("~/.pi/agent")
ASSIGNMENTS_PATH = os.path.join(AGENT_DIR, "set-model.json")
REPORT_PATH = os.path.expanduser("~/.cache/model-picker/assignments-report.md")

JUNK_ID = re.compile(r"^(~)|:(free|batch|extended|US|EU|anchor|nitro)$")
PREVIEW_ID = re.compile(r"preview|exp$|-vision", re.I)


def usable(m: dict) -> bool:
    return not JUNK_ID.search(m["id"]) and not PREVIEW_ID.search(m["id"])


def newest(models: list, pattern: re.Pattern) -> dict | None:
    hits = [m for m in models if pattern.match(m["id"].split("/", 1)[1] or "") and usable(m)]
    if not hits:
        return None
    return max(hits, key=lambda m: m.get("created") or 0)


def pick_lineage(nous_raw: list, pattern: re.Pattern) -> str | None:
    """Newest model in a vendor lineage; the pattern covers base and -pro variants."""
    hit = newest(nous_raw, pattern)
    return hit["id"] if hit else None


def compute_assignments(fresh: bool = True) -> dict[str, str]:
    nous_raw = fetch("https://inference-api.nousresearch.com/v1/models", fresh)
    or_raw = fetch(OPENROUTER, fresh)
    merged = merge(nous_raw, or_raw)

    prog = fetch(f"{OPENROUTER}?category=programming", fresh)
    ranks = {m["id"]: i + 1 for i, m in enumerate(prog)}

    picks: dict[str, str] = {}

    picks["deep-research"] = pick_lineage(nous_raw, re.compile(r"^kimi-k[\d.]+(-pro)?$"))
    picks["general"] = pick_lineage(nous_raw, re.compile(r"^glm-[\d.]+$"))
    picks["routing"] = pick_lineage(nous_raw, re.compile(r"^minimax-m[\d.]+(-\d+)?-flash$"))
    picks["reasoning"] = pick_lineage(nous_raw, re.compile(r"^deepseek-v[\d.]+-pro(-\d{4})?$"))
    picks["image-generation"] = pick_lineage(nous_raw, re.compile(r"^qwen[\d.]+-max(-\d+|-prime)?$"))

    # coding: top flagship in the OpenRouter programming ranking, served on Nous
    coding = None
    for mid in ranks:
        row = merged.get(mid)
        if not row or row["tier"] != "flagship" or "nous" not in row["sources"]:
            continue
        if PREVIEW_ID.search(mid):
            continue
        coding = mid
        break
    picks["coding"] = coding

    # fast: cheapest value tier with long-context + agentic, served on Nous.
    # Free-tier variants are rate-limited experiments, not standing assignments.
    cheap = sorted(
        (r for r in merged.values()
         if r["tier"] in ("value", "frontier-value")
         and "long-ctx" in r["uses"] and "agentic" in r["uses"]
         and "nous" in r["sources"]
         and not r["id"].endswith(":free")
         and not PREVIEW_ID.search(r["id"])),
        key=lambda r: r["in_raw"] + r["out_raw"],
    )
    picks["fast"] = cheap[0]["id"] if cheap else None

    # Assignments always target the Nous Portal provider.
    return {k: f"nous-portal/{v}" for k, v in picks.items() if v}


def main():
    dry = "--dry-run" in sys.argv
    picks = compute_assignments(fresh=not os.environ.get("REFRESH_SKIP_FETCH"))

    current: dict = {}
    try:
        with open(ASSIGNMENTS_PATH) as f:
            current = json.load(f)
    except (OSError, json.JSONDecodeError):
        pass

    updated = dict(current)
    changes: list[str] = []
    reasons = {
        "deep-research": "newest Kimi long-context lineage",
        "coding": "top non-preview flagship in OpenRouter programming ranking, served on Nous",
        "reasoning": "newest DeepSeek non-flash reasoning flagship",
        "image-generation": "newest Qwen max with vision",
        "routing": "newest MiniMax flash (cheap agentic dispatch)",
        "fast": "cheapest value tier with long-context + agentic on Nous",
        "general": "newest Z.ai GLM flagship",
    }

    for ctx, model in picks.items():
        entry = current.get(ctx)
        if isinstance(entry, dict) and entry.get("lock"):
            changes.append(f"- {ctx}: LOCKED, kept {entry.get('model')}")
            continue
        old_model = entry.get("model") if isinstance(entry, dict) else None
        if old_model == model:
            changes.append(f"- {ctx}: {model} (unchanged)")
            continue
        new_entry = dict(entry) if isinstance(entry, dict) else {}
        new_entry["model"] = model
        if "thinking" not in new_entry:
            new_entry["thinking"] = "medium"
        updated[ctx] = new_entry
        changes.append(f"- {ctx}: {old_model or 'none'} → {model} ({reasons.get(ctx, 'policy')})")

    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    report = f"# Model assignment refresh — {ts}\n\n" + "\n".join(changes) + "\n"
    os.makedirs(os.path.dirname(REPORT_PATH), exist_ok=True)
    with open(REPORT_PATH, "w") as f:
        f.write(report)

    if not dry:
        with open(ASSIGNMENTS_PATH, "w") as f:
            json.dump(updated, f, indent=2)
            f.write("\n")

    print(report)
    changed = sum(1 for c in changes if "→" in c)
    print(f"{changed} assignment(s) changed" + (" (dry run — file not written)" if dry else ""))


if __name__ == "__main__":
    main()
