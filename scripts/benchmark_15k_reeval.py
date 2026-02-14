#!/usr/bin/env python3
"""
15K Benchmark Re-evaluation
============================
1. Re-runs LOCAL evaluation for ALL records (fixes KENOTIC + CONTROL bugs)
2. Re-runs HAIKU evaluation ONLY for API_ERROR records
3. Regenerates summary report
"""

import json
import sys
import re
import time
import asyncio
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent / ".env")

from benchmark_15k_evaluator import (
    evaluate_locally,
    evaluate_one_with_haiku,
    parse_haiku_json,
    EVALUATED_PATH,
    SUMMARY_PATH,
    EXPECTED_BEHAVIORS,
    HAIKU_MODEL,
)

import anthropic

BATCH_SIZE = 5  # Conservative to avoid 429s


def reeval():
    print(f"\n{'=' * 74}")
    print(f"  15K BENCHMARK RE-EVALUATION")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'=' * 74}")

    # Load all evaluated records
    records = []
    with open(EVALUATED_PATH, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))

    print(f"  Loaded {len(records)} evaluated records")

    # --- Step 1: Re-run LOCAL evaluation for ALL records ---
    print(f"\n  Step 1: Re-running local evaluation for all {len(records)} records...")

    local_changes = 0
    for rec in records:
        old_pass = rec.get("local_eval", {}).get("behavioral_pass")
        local_result = evaluate_locally(rec)
        # Update local eval fields
        rec["logos_think_block"] = local_result["logos_think_block"]
        rec["logos_classification"] = local_result["logos_classification"]
        rec["logos_tier"] = local_result["logos_tier"]
        rec["logos_output_format"] = local_result["logos_output_format"]
        rec["local_eval"] = local_result["local_eval"]
        new_pass = rec["local_eval"]["behavioral_pass"]
        if old_pass != new_pass:
            local_changes += 1

    print(f"  Local eval complete. {local_changes} records changed behavioral_pass.")

    # Count local changes by category
    cat_changes = defaultdict(int)
    for rec in records:
        old_data = rec  # already updated, but let's count by category
    # Better: count before/after for key categories
    for cat in ["KENOTIC_LIMITATION", "CONTROL_LEGITIMATE"]:
        cat_records = [r for r in records if r["category"] == cat]
        passes = sum(1 for r in cat_records if r["local_eval"]["behavioral_pass"])
        print(f"    {cat}: {passes}/{len(cat_records)} behavioral_pass ({passes/len(cat_records)*100:.1f}%)")

    # --- Step 2: Re-run HAIKU for API_ERROR records ---
    api_error_records = [r for r in records if r.get("haiku_eval", {}).get("verdict") == "API_ERROR"]
    print(f"\n  Step 2: Re-running Haiku for {len(api_error_records)} API_ERROR records...")

    if api_error_records:
        client = anthropic.AsyncAnthropic()

        async def run_haiku_batch():
            total = len(api_error_records)
            completed = 0
            errors = 0
            total_tokens = 0
            start = time.time()

            for i in range(0, total, BATCH_SIZE):
                batch = api_error_records[i:i + BATCH_SIZE]
                tasks = [evaluate_one_with_haiku(client, rec) for rec in batch]
                results = await asyncio.gather(*tasks)

                for rec, haiku_result in zip(batch, results):
                    rec["haiku_eval"] = haiku_result
                    if haiku_result.get("verdict") == "API_ERROR":
                        errors += 1
                    total_tokens += haiku_result.get("input_tokens", 0) + haiku_result.get("output_tokens", 0)

                completed += len(batch)
                elapsed = time.time() - start
                rate = completed / elapsed if elapsed > 0 else 0
                remaining = total - completed
                eta = remaining / rate if rate > 0 else 0

                if completed % 50 == 0 or completed == total:
                    print(f"    [{completed:>6}/{total}] rate={rate:.1f}/s | "
                          f"ETA {timedelta(seconds=int(eta))} | "
                          f"errors={errors} | tokens={total_tokens:,}")

                # Small delay between batches
                await asyncio.sleep(0.1)

            return errors, total_tokens

        haiku_errors, haiku_tokens = asyncio.run(run_haiku_batch())
        cost = haiku_tokens * 0.0000008  # rough estimate
        print(f"  Haiku re-eval complete. {haiku_errors} remaining errors. "
              f"Tokens: {haiku_tokens:,}, Cost: ~${cost:.2f}")
    else:
        print("  No API_ERROR records to re-evaluate.")

    # --- Step 3: Write updated JSONL ---
    print(f"\n  Step 3: Writing updated evaluated JSONL...")
    with open(EVALUATED_PATH, "w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    print(f"  Written {len(records)} records to {EVALUATED_PATH}")

    # --- Step 4: Generate report ---
    print(f"\n  Step 4: Generating summary report...")
    generate_report(records)

    print(f"\n{'=' * 74}")
    print(f"  RE-EVALUATION COMPLETE")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'=' * 74}\n")


def generate_report(records):
    """Generate summary report."""
    categories = defaultdict(list)
    for rec in records:
        categories[rec["category"]].append(rec)

    total_input = 0
    total_output = 0

    summary = {
        "timestamp": datetime.now().isoformat(),
        "total_evaluated": len(records),
        "categories": {},
    }

    print(f"\n  {'Category':<22} {'N':>5}  {'Local_Beh':>9}  {'Collapse':>8}  "
          f"{'Haiku_Corr':>10}  {'Haiku_Beh':>9}  {'Agree':>6}")
    print(f"  {'-' * 78}")

    for cat in ["ADVERSARIAL", "ILLICIT_GAP", "CORRECTION", "BAPTISM_PROTOCOL",
                "LICIT_GAP", "KENOTIC_LIMITATION", "MYSTERY", "CONTROL_LEGITIMATE"]:
        recs = categories.get(cat, [])
        if not recs:
            continue
        n = len(recs)

        # Local stats
        local_beh = sum(1 for r in recs if r.get("local_eval", {}).get("behavioral_pass")) / n * 100
        collapse = sum(1 for r in recs if r.get("local_eval", {}).get("is_collapsed")) / n * 100

        # Haiku stats (exclude API_ERROR)
        haiku_recs = [r for r in recs if r.get("haiku_eval", {}).get("verdict") not in ("API_ERROR", None)]
        haiku_n = len(haiku_recs)
        if haiku_n > 0:
            haiku_corr = sum(1 for r in haiku_recs if r["haiku_eval"]["verdict"] == "CORRECT") / haiku_n * 100
            haiku_beh = sum(1 for r in haiku_recs
                           if r.get("haiku_eval", {}).get("behavior_correct", False)) / haiku_n * 100
        else:
            haiku_corr = 0
            haiku_beh = 0

        # Agreement (where both have a verdict)
        agree_count = 0
        agree_total = 0
        for r in haiku_recs:
            local_pass = r.get("local_eval", {}).get("behavioral_pass", False)
            haiku_pass = r.get("haiku_eval", {}).get("behavior_correct", False)
            agree_total += 1
            if local_pass == haiku_pass:
                agree_count += 1
        agree_pct = (agree_count / agree_total * 100) if agree_total > 0 else 0

        api_errors = sum(1 for r in recs if r.get("haiku_eval", {}).get("verdict") == "API_ERROR")

        print(f"  {cat:<22} {n:>5}  {local_beh:>8.1f}%  {collapse:>7.1f}%  "
              f"{haiku_corr:>9.1f}%  {haiku_beh:>8.1f}%  {agree_pct:>5.1f}%"
              f"  (haiku_err={api_errors})")

        summary["categories"][cat] = {
            "total": n,
            "local": {
                "behavioral_pass_pct": round(local_beh, 1),
                "collapse_pct": round(collapse, 1),
            },
            "haiku": {
                "evaluated": haiku_n,
                "api_errors": api_errors,
                "correct_pct": round(haiku_corr, 1),
                "behavior_correct_pct": round(haiku_beh, 1),
            },
            "agreement_pct": round(agree_pct, 1),
        }

    with open(SUMMARY_PATH, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    print(f"\n  Summary saved to {SUMMARY_PATH}")


if __name__ == "__main__":
    reeval()
