#!/usr/bin/env python3
"""
9B Benchmark Runner — Stratified Sample from 15K Evaluated Suite
================================================================
Takes a stratified sample of N records (default 300) from
benchmark_15k_evaluated.jsonl, proportional to category distribution,
and runs each through logos-auditor:latest (Gemma 2 9B) via Ollama.

Saves results as benchmark_9b_sample.jsonl in the same format as the
15K runner output (compatible with benchmark_15k_evaluator.py).

Usage:
  python benchmark_9b_runner.py                    # Full 300-sample run
  python benchmark_9b_runner.py --resume           # Resume from crash
  python benchmark_9b_runner.py --limit 300        # Explicit limit (default)
  python benchmark_9b_runner.py --limit 50         # Quick test
  python benchmark_9b_runner.py --dry-run          # Show sampling plan
  python benchmark_9b_runner.py --seed 42          # Reproducible sampling
"""

import json
import os
import sys
import time
import math
import random
import argparse
from datetime import datetime, timedelta
from collections import Counter, defaultdict
from pathlib import Path

import requests

# ─── Config ──────────────────────────────────────────────────────

BENCHMARKS_DIR = Path(__file__).parent
SOURCE_PATH = BENCHMARKS_DIR / "benchmark_15k_evaluated.jsonl"
RESPONSES_PATH = BENCHMARKS_DIR / "benchmark_9b_sample.jsonl"
CHECKPOINT_PATH = BENCHMARKS_DIR / "benchmark_9b_runner_checkpoint.json"
SAMPLE_IDS_PATH = BENCHMARKS_DIR / "benchmark_9b_sample_ids.json"

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
OLLAMA_CHAT_URL = OLLAMA_URL.rstrip("/") + "/api/chat"

DEFAULT_MODEL = "logos-auditor:latest"
DEFAULT_LIMIT = 300
DEFAULT_SEED = 2026

RUNNER_OPTIONS = {
    "temperature": 0.1,
    "num_ctx": 4096,
    "num_predict": 512,
    "repeat_penalty": 1.5,
    "top_k": 30,
    "top_p": 0.9,
}


# ─── Ollama Query (matches modelfile_sweep.query_model_with_config) ──

def query_model(model, claim, options, system_prompt=None):
    """Query an Ollama model with custom options.

    Uses the same pattern as modelfile_sweep.query_model_with_config:
    POST to /api/chat with messages, stream=False, options dict.
    system_prompt=None means use the Modelfile's built-in SYSTEM prompt.
    """
    messages = []
    if system_prompt is not None:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": claim})

    payload = {
        "model": model,
        "messages": messages,
        "stream": False,
        "options": options,
    }
    try:
        r = requests.post(OLLAMA_CHAT_URL, json=payload, timeout=300)
        r.raise_for_status()
        data = r.json()
        return {
            "model": model,
            "content": data["message"]["content"],
            "duration_ns": data.get("eval_duration", 0),
        }
    except Exception as e:
        return {
            "model": model,
            "content": f"ERROR: {e}",
            "duration_ns": 0,
            "error": True,
        }


# ─── Expected recommendation (inline, avoids import dependency) ──

CATEGORY_EXPECTED = {
    "ADVERSARIAL": "BLOCK",
    "ILLICIT_GAP": "BLOCK",
    "CORRECTION": "PASS",
    "MYSTERY": "PASS",
    "LICIT_GAP": "PASS",
    "BAPTISM_PROTOCOL": "PASS",
    "KENOTIC_LIMITATION": "PASS",
    "CONTROL_LEGITIMATE": "PASS",
}


def get_expected(category):
    """Get expected recommendation for a category."""
    return CATEGORY_EXPECTED.get(category, "PASS")


# ─── Stratified Sampling ─────────────────────────────────────────

def load_source_records():
    """Load all records from the 15K evaluated JSONL."""
    records = []
    with open(SOURCE_PATH, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    return records


def stratified_sample(records, n, seed):
    """Take a stratified sample of n records, proportional to category distribution.

    Uses largest-remainder method to ensure the sample sums to exactly n
    while keeping proportions as close as possible.
    """
    rng = random.Random(seed)

    # Group by category
    by_category = defaultdict(list)
    for rec in records:
        by_category[rec["category"]].append(rec)

    total = len(records)

    # Compute proportional allocation (largest-remainder method)
    raw_allocation = {}
    for cat, cat_records in by_category.items():
        raw_allocation[cat] = len(cat_records) / total * n

    # Floor allocation
    allocation = {cat: int(math.floor(raw)) for cat, raw in raw_allocation.items()}
    remainders = {cat: raw - allocation[cat] for cat, raw in raw_allocation.items()}

    # Distribute remaining slots by largest remainder
    deficit = n - sum(allocation.values())
    for cat in sorted(remainders, key=remainders.get, reverse=True):
        if deficit <= 0:
            break
        allocation[cat] += 1
        deficit -= 1

    # Sample from each category
    sampled = []
    for cat in sorted(allocation.keys()):
        cat_n = allocation[cat]
        cat_records = by_category[cat]
        if cat_n >= len(cat_records):
            sampled.extend(cat_records)
        else:
            sampled.extend(rng.sample(cat_records, cat_n))

    # Shuffle to avoid category clustering
    rng.shuffle(sampled)

    return sampled, allocation


# ─── JSONL I/O ────────────────────────────────────────────────────

def load_completed_ids():
    """Load set of completed test IDs from existing output JSONL."""
    ids = set()
    if RESPONSES_PATH.exists():
        with open(RESPONSES_PATH, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                    ids.add(record["id"])
                except (json.JSONDecodeError, KeyError):
                    pass
    return ids


def append_record(record):
    """Atomic append of one JSONL line."""
    with open(RESPONSES_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def save_checkpoint(completed_count, stats, elapsed, sample_size):
    """Save lightweight checkpoint for progress tracking."""
    checkpoint = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "completed_count": completed_count,
        "sample_size": sample_size,
        "elapsed_seconds": round(elapsed, 1),
        "category_stats": {k: dict(v) for k, v in stats.items()},
    }
    with open(CHECKPOINT_PATH, "w", encoding="utf-8") as f:
        json.dump(checkpoint, f, ensure_ascii=False, indent=2)


def save_sample_ids(sample, allocation, seed):
    """Save the sampled IDs for reproducibility."""
    meta = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "seed": seed,
        "total_sampled": len(sample),
        "allocation": allocation,
        "ids": [rec["id"] for rec in sample],
    }
    with open(SAMPLE_IDS_PATH, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)


def load_sample_ids():
    """Load previously saved sample IDs for resume consistency."""
    if SAMPLE_IDS_PATH.exists():
        with open(SAMPLE_IDS_PATH, encoding="utf-8") as f:
            return json.load(f)
    return None


# ─── Runner ──────────────────────────────────────────────────────

def run(model, resume=False, limit=DEFAULT_LIMIT, seed=DEFAULT_SEED, dry_run=False):
    """Run 9B benchmark on a stratified sample from the 15K evaluated suite."""

    # Load source data
    if not SOURCE_PATH.exists():
        print(f"  ERROR: Source not found at {SOURCE_PATH}")
        print(f"  Need benchmark_15k_evaluated.jsonl to sample from.")
        sys.exit(1)

    print(f"  Loading source data from {SOURCE_PATH.name}...")
    all_records = load_source_records()
    print(f"  Loaded {len(all_records)} records")

    # Stratified sample
    # On resume, reuse the same sample IDs if available
    existing_sample_meta = load_sample_ids() if resume else None

    if existing_sample_meta and resume:
        # Rebuild sample from saved IDs to ensure consistency
        saved_ids = set(existing_sample_meta["ids"])
        id_to_record = {r["id"]: r for r in all_records}
        sample = [id_to_record[sid] for sid in existing_sample_meta["ids"] if sid in id_to_record]
        allocation = existing_sample_meta["allocation"]
        seed = existing_sample_meta["seed"]
        print(f"  Resumed sample: {len(sample)} records (seed={seed})")
    else:
        sample, allocation = stratified_sample(all_records, limit, seed)
        save_sample_ids(sample, allocation, seed)
        print(f"  Sampled {len(sample)} records (seed={seed})")

    total = len(sample)

    # Show allocation
    print(f"\n  Stratified allocation ({total} total):")
    source_cats = Counter(r["category"] for r in all_records)
    for cat in sorted(allocation.keys()):
        src_count = source_cats.get(cat, 0)
        src_pct = src_count / len(all_records) * 100
        print(f"    {cat:<30} {allocation[cat]:>4} / {src_count:>5} ({src_pct:5.1f}%)")

    if dry_run:
        print(f"\n  DRY RUN — would execute:")
        print(f"    Model: {model}")
        print(f"    Sample size: {total}")
        print(f"    Seed: {seed}")
        print(f"    Options: {RUNNER_OPTIONS}")
        est_hours = total * 5.0 / 3600  # ~5s per test for 9B
        print(f"    Estimated time: {est_hours:.1f} hours (at ~5s/test for 9B)")
        print(f"    Output: {RESPONSES_PATH}")
        return

    # Resume: skip completed
    completed_ids = set()
    if resume:
        completed_ids = load_completed_ids()
        print(f"  Resuming: {len(completed_ids)} already completed")

    remaining = [rec for rec in sample if rec["id"] not in completed_ids]

    if not remaining:
        print("  All tests already completed!")
        return

    # ─── Verify model availability ─────────────────────────────
    print(f"\n  Verifying model {model} is available...")
    try:
        r = requests.get(OLLAMA_URL.rstrip("/") + "/api/tags", timeout=10)
        r.raise_for_status()
        models = [m["name"] for m in r.json().get("models", [])]
        model_base = model.split(":")[0]
        found = any(model_base in m for m in models)
        if not found:
            print(f"  WARNING: Model '{model}' not found in Ollama.")
            print(f"  Available models: {', '.join(models[:10])}")
            print(f"  Continuing anyway (Ollama may pull it)...")
        else:
            print(f"  Model found.")
    except Exception as e:
        print(f"  WARNING: Could not verify model availability: {e}")
        print(f"  Continuing anyway...")

    # ─── Main loop ─────────────────────────────────────────────

    stats = defaultdict(lambda: {"correct": 0, "total": 0, "errors": 0})
    start_time = time.time()
    completed_in_session = 0

    print(f"\n{'=' * 74}")
    print(f"  9B BENCHMARK RUNNER — Stratified Sample ({total})")
    print(f"  Model: {model}")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Tests: {len(remaining)} remaining / {total} total")
    print(f"  Options: temp={RUNNER_OPTIONS['temperature']}, "
          f"np={RUNNER_OPTIONS['num_predict']}, "
          f"rp={RUNNER_OPTIONS['repeat_penalty']}")
    print(f"  Output: {RESPONSES_PATH}")
    print(f"{'=' * 74}\n")

    for i, item in enumerate(remaining):
        test_id = item["id"]
        category = item["category"]
        expected = get_expected(category)
        subcategory = item.get("subcategory")

        # Query logos-auditor via Ollama
        error_msg = None
        try:
            result = query_model(model, item["claim"], RUNNER_OPTIONS, None)
            content = result["content"]
            duration_ns = result.get("duration_ns", 0)
            if result.get("error"):
                error_msg = content
        except Exception as e:
            content = f"ERROR: {e}"
            duration_ns = 0
            error_msg = str(e)

        # Build record (same format as 15K runner)
        record = {
            "id": test_id,
            "category": category,
            "subcategory": subcategory,
            "claim": item["claim"],
            "expected": expected,
            "logos_response": content,
            "logos_duration_ns": duration_ns,
            "model": model,
            "timestamp": datetime.now().isoformat(),
        }
        if error_msg:
            record["error"] = error_msg

        # Atomic write
        append_record(record)

        # Track stats
        stats[category]["total"] += 1
        if error_msg:
            stats[category]["errors"] += 1
        completed_ids.add(test_id)
        completed_in_session += 1

        # Progress display (every 10 records)
        elapsed = time.time() - start_time
        rate = completed_in_session / elapsed if elapsed > 0 else 0
        remaining_count = len(remaining) - (i + 1)
        eta_seconds = remaining_count / rate if rate > 0 else 0
        eta = str(timedelta(seconds=int(eta_seconds)))

        total_done = len(completed_ids)
        has_think = "<think>" in content or "<logos_think>" in content
        think_marker = "T" if has_think else "."
        err_marker = "E" if error_msg else " "
        resp_len = len(content)
        duration_s = duration_ns / 1e9 if duration_ns else 0

        if completed_in_session % 10 == 0 or completed_in_session <= 3 or error_msg:
            print(f"  [{total_done:>4}/{total}] {test_id:<20} "
                  f"{category[:8]:<8} exp={expected:<5} "
                  f"{think_marker}{err_marker} "
                  f"len={resp_len:>4} "
                  f"{duration_s:>5.1f}s "
                  f"| {rate:.2f}/s | ETA {eta}")
            sys.stdout.flush()

        # Checkpoint every 50 tests
        if completed_in_session % 50 == 0:
            save_checkpoint(total_done, stats, elapsed, total)
            total_errors = sum(s["errors"] for s in stats.values())
            print(f"\n  -- Checkpoint ({total_done}/{total}) | "
                  f"Rate: {rate:.2f}/s | "
                  f"Errors: {total_errors} | "
                  f"Elapsed: {timedelta(seconds=int(elapsed))}")
            for cat in sorted(stats.keys()):
                s = stats[cat]
                print(f"     {cat:<25} {s['total']:>4} done"
                      f"  ({s['errors']} errors)")
            print()

        # Small delay to avoid overloading Ollama
        time.sleep(0.05)

    # ─── Final Summary ─────────────────────────────────────────

    elapsed_total = time.time() - start_time
    total_done = len(completed_ids)
    total_errors = sum(s["errors"] for s in stats.values())

    # Clean up checkpoint
    if CHECKPOINT_PATH.exists():
        CHECKPOINT_PATH.unlink()

    print(f"\n{'=' * 74}")
    print(f"  9B BENCHMARK COMPLETE")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'=' * 74}")
    print(f"  Model: {model}")
    print(f"  Total: {total_done} responses captured")
    print(f"  Errors: {total_errors}")
    print(f"  Elapsed: {timedelta(seconds=int(elapsed_total))}")
    if elapsed_total > 0:
        print(f"  Rate: {completed_in_session / elapsed_total:.2f} tests/sec")
        avg_s = elapsed_total / completed_in_session if completed_in_session else 0
        print(f"  Avg per test: {avg_s:.1f}s")
    print(f"  Output: {RESPONSES_PATH}")
    if RESPONSES_PATH.exists():
        print(f"  Size: {RESPONSES_PATH.stat().st_size / (1024 * 1024):.1f} MB")

    print(f"\n  Category breakdown:")
    for cat in sorted(stats.keys()):
        s = stats[cat]
        print(f"    {cat:<25} {s['total']:>4} done  ({s['errors']} errors)")

    print(f"\n  Next step: python benchmark_15k_evaluator.py "
          f"--input {RESPONSES_PATH.name}")
    print(f"{'=' * 74}\n")


# ─── CLI ─────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="9B Benchmark Runner — Stratified Sample from 15K Suite"
    )
    parser.add_argument("--model", default=DEFAULT_MODEL,
                        help=f"Ollama model name (default: {DEFAULT_MODEL})")
    parser.add_argument("--resume", action="store_true",
                        help="Resume from existing JSONL (reuses same sample)")
    parser.add_argument("--limit", type=int, default=DEFAULT_LIMIT,
                        help=f"Sample size (default: {DEFAULT_LIMIT})")
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED,
                        help=f"Random seed for stratified sampling (default: {DEFAULT_SEED})")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show sampling plan without executing")

    args = parser.parse_args()

    run(
        model=args.model,
        resume=args.resume,
        limit=args.limit,
        seed=args.seed,
        dry_run=args.dry_run,
    )


if __name__ == "__main__":
    main()
