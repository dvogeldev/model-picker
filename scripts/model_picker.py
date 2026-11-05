#!/usr/bin/env python3
"""model_picker.py — fetch, classify, and rank LLM catalogs.

Sources: Nous Portal inference API + OpenRouter (same schema).
Modes: --task CATEGORY (top models by task), --promos (active deals),
       --all (full catalog). Prints a markdown table; --json for raw data.
"""
import argparse
import json
import os
import re
import sys
import time
import urllib.request

CACHE_DIR = os.path.expanduser("~/.cache/model-picker")
CACHE_TTL = 86400  # seconds — one ingestion per day; the daily refresh timer warms the cache

NOUS = "https://inference-api.nousresearch.com/v1/models"
OPENROUTER = "https://openrouter.ai/api/v1/models"

CATEGORIES = [
    "programming", "roleplay", "marketing", "marketing/seo", "technology",
    "science", "translation", "legal", "finance", "health", "trivia", "academia",
]

FRONTIER_VENDORS = {"anthropic", "openai", "x-ai", "google"}
FRONTIER_OPEN_LINES = re.compile(r"^(gemma|gpt-oss)")  # open-weight lines of frontier vendors
VALUE_KEYWORDS = ("flash", "mini", "lite", "air", "small", "haiku", "nano", "instant", "contributor", "spark")
TIER_ORDER = {"frontier": 0, "flagship": 1, "frontier-value": 2, "value": 3, "small": 4, "embed": 9}
PARAM_RE = re.compile(r"(\d+(?:\.\d+)?)\s*b\b", re.I)


def fetch(url: str, fresh: bool = False) -> list:
    key = re.sub(r"[^a-z0-9]+", "_", url.split("//")[1].split("?")[0])[:80]
    if "?" in url:
        key += "_" + re.sub(r"[^a-z0-9]+", "_", url.split("?")[1])[:40]
    path = os.path.join(CACHE_DIR, key + ".json")
    if not fresh and os.path.exists(path) and time.time() - os.path.getmtime(path) < CACHE_TTL:
        with open(path) as f:
            return json.load(f)["data"]
    req = urllib.request.Request(url, headers={"User-Agent": "model-picker/1.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.load(r)["data"]
    os.makedirs(CACHE_DIR, exist_ok=True)
    with open(path, "w") as f:
        json.dump({"data": data}, f)
    return data


def fmt_ctx(n) -> str:
    if not n:
        return "?"
    if n >= 1_000_000:
        s = n / 1_000_000
        return f"{s:.0f}M" if s == int(s) else f"{s:.1f}M"
    return f"{round(n / 1000)}K"


def fmt_price(v) -> str:
    try:
        p = float(v) * 1_000_000
        return f"{p:.2f}" if p >= 1 else f"{p:.3f}"
    except (TypeError, ValueError):
        return "?"


def classify(m: dict) -> dict:
    mid = m.get("id", "")
    vendor = mid.split("/")[0].lstrip("~")
    name = mid.split("/", 1)[1] if "/" in mid else mid
    name_l = name.lower()
    pricing = m.get("pricing") or {}
    arch = m.get("architecture") or {}
    reasoning = m.get("reasoning") or {}

    params = None
    for match in PARAM_RE.finditer(name_l):
        try:
            params = float(match.group(1))
        except ValueError:
            pass
    is_value = any(k in name_l for k in VALUE_KEYWORDS)
    is_embed = "embed" in name_l or vendor in {"sentence-transformers", "thenlper", "intfloat", "baai"}

    if is_embed:
        tier = "embed"
    elif vendor in FRONTIER_VENDORS and not FRONTIER_OPEN_LINES.match(name_l):
        tier = "frontier" if not is_value else "frontier-value"
        # cheap frontier lines (mini-class pricing) are value tier in practice
        try:
            if tier == "frontier" and pricing.get("prompt") and float(pricing["prompt"]) * 1_000_000 < 0.30:
                tier = "frontier-value"
        except ValueError:
            pass
    elif is_value:
        tier = "value"
    elif params is not None and params <= 32:
        tier = "small"
    else:
        tier = "flagship"

    uses = []
    if (m.get("context_length") or 0) >= 256_000:
        uses.append("long-ctx")
    if reasoning.get("default_enabled") or reasoning.get("mandatory") or "thinking" in name_l or re.search(r"-r1", name_l):
        uses.append("reasoning")
    if "tools" in (m.get("supported_parameters") or []):
        uses.append("agentic")
    if "image" in (arch.get("input_modalities") or []):
        uses.append("vision")
    if is_embed:
        uses.append("embed")
    out_mods = [m for m in (arch.get("output_modalities") or []) if m != "text"]
    if out_mods:
        uses.append("out:" + "+".join(out_mods))
    if not uses:
        uses.append("general")

    promos = []
    if pricing.get("original"):
        try:
            pct = round((1 - float(pricing["prompt"]) / float(pricing["original"]["prompt"])) * 100)
            if pct > 0:
                promos.append(f"{pct}% off")
        except (TypeError, ValueError, ZeroDivisionError):
            pass
    if pricing.get("overrides"):
        days = sorted({d[:3] for o in pricing["overrides"] for d in o.get("utc_days", [])})
        promos.append("sched:" + (",".join(days) if days else "time-boxed"))
    if mid.endswith(":free"):
        promos.append("free")

    return {
        "id": mid,
        "vendor": vendor,
        "tier": tier,
        "uses": uses,
        "open": "open" if m.get("hugging_face_id") else "proprietary",
        "ctx": fmt_ctx(m.get("context_length")),
        "ctx_raw": m.get("context_length") or 0,
        "in": fmt_price(pricing.get("prompt")),
        "out": fmt_price(pricing.get("completion")),
        "in_raw": float(pricing["prompt"]) if pricing.get("prompt") else float("inf"),
        "out_raw": float(pricing["completion"]) if pricing.get("completion") else float("inf"),
        "promo": " ".join(promos),
        "has_promo": bool(promos),
    }


def merge(nous: list, or_: list) -> dict:
    merged = {}
    for src, models in (("nous", nous), ("or", or_)):
        for m in models:
            mid = m.get("id", "")
            if mid.startswith("~") or re.search(r":(batch|extended|US|EU|anchor|nitro)$", mid):
                continue
            row = classify(m)
            if mid in merged:
                merged[mid]["sources"].add(src)
                promos = set(merged[mid]["promo"].split()) | set(row["promo"].split())
                merged[mid]["promo"] = " ".join(sorted(promos))
                merged[mid]["has_promo"] = merged[mid]["has_promo"] or row["has_promo"]
                if row["in_raw"] < merged[mid]["in_raw"]:
                    merged[mid].update({k: row[k] for k in ("in", "out", "in_raw", "ctx", "ctx_raw")})
            else:
                row["sources"] = {src}
                merged[mid] = row
    for row in merged.values():
        row["sources"] = sorted(row["sources"])
    return merged


def print_table(rows: list, title: str, extra_col: str = None):
    if not rows:
        print(f"## {title}\n\n(no models)")
        return
    head = ["model", "tier"] + ([extra_col] if extra_col else []) + ["use cases", "open", "ctx", "$/M in", "$/M out", "promo", "sources"]
    print(f"## {title}\n")
    print("| " + " | ".join(head) + " |")
    print("|" + "---|" * len(head))
    for r in rows:
        cells = [r["id"], r["tier"]]
        if extra_col:
            cells.append(r.get(extra_col, ""))
        cells += [",".join(r["uses"]), r["open"], r["ctx"], r["in"], r["out"], r["promo"] or "-", ",".join(r["sources"])]
        print("| " + " | ".join(str(c) for c in cells) + " |")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--task", metavar="CATEGORY", choices=CATEGORIES, help="top models by task category")
    g.add_argument("--promos", action="store_true", help="models with active promotions/free tiers")
    g.add_argument("--all", action="store_true", help="full classified catalog")
    ap.add_argument("--vendor", choices=["nous", "openrouter"], default=None)
    ap.add_argument("--limit", type=int, default=40)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--fresh", action="store_true", help="bypass cache")
    args = ap.parse_args()

    if args.vendor == "nous":
        nous, or_ = fetch(NOUS, args.fresh), []
    elif args.vendor == "openrouter":
        nous, or_ = [], fetch(OPENROUTER, args.fresh)
    else:
        nous, or_ = fetch(NOUS, args.fresh), fetch(OPENROUTER, args.fresh)

    merged = merge(nous, or_)

    if args.json:
        rows = [{k: (list(v) if isinstance(v, set) else v) for k, v in r.items()} for r in merged.values()]
        print(json.dumps(sorted(rows, key=lambda r: (TIER_ORDER.get(r["tier"], 5), r["in_raw"])), indent=2))
        return

    def key(r):
        return (TIER_ORDER.get(r["tier"], 5), r["in_raw"])

    if args.task:
        # Only OpenRouter's category list is a real task ranking (top ~20 by
        # usage). The Nous category endpoint returns the whole catalog in an
        # arbitrary order (embeddings included) — never use it for ranks.
        cat_or = fetch(f"{OPENROUTER}?category={args.task}", args.fresh)
        ranks = {m["id"]: i + 1 for i, m in enumerate(cat_or)}
        rows = [dict(r, rank=ranks[r["id"]]) for r in merged.values()
                if r["tier"] != "embed" and r["id"] in ranks]
        rows.sort(key=lambda r: (r["rank"], TIER_ORDER.get(r["tier"], 5), r["in_raw"]))
        print_table(rows[: args.limit], f"Top models for: {args.task} (OpenRouter usage rank; sources show Nous availability)", "rank")
    elif args.promos:
        rows = [r for r in merged.values() if r["has_promo"] and r["tier"] != "embed"]
        rows.sort(key=lambda r: (key(r),))
        print_table(rows[: args.limit], "Models with active promotions or free tiers")
    else:
        rows = sorted((r for r in merged.values() if r["tier"] != "embed"), key=key)
        print_table(rows[: args.limit], f"Catalog by tier then price (of {len(rows)} generation models)")


if __name__ == "__main__":
    main()