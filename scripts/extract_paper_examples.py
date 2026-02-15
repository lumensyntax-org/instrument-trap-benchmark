import json
import re
from pathlib import Path

DATA_PATH = Path(__file__).parent.parent / "benchmark_15k_evaluated.jsonl"

records = []
with open(DATA_PATH) as f:
    for line in f:
        if line.strip():
            records.append(json.loads(line))

print("=" * 80)
print("PART A: 5 CORRECT REFUSALS MISCLASSIFIED AS FAILURES")
print("=" * 80)

# ILLICIT_GAP: refused correctly but evaluator said FAIL
illicit_fails = [r for r in records if r['category'] == 'ILLICIT_GAP' 
                 and not r['local_eval']['behavioral_pass']]

# Pick diverse subcategories
seen_subcats = set()
examples_a = []
for r in illicit_fails:
    subcat = r.get('subcategory', 'UNKNOWN')
    if subcat not in seen_subcats and len(examples_a) < 3:
        seen_subcats.add(subcat)
        examples_a.append(r)

# Also get a CORRECTION correct refusal and a LICIT_GAP correct refusal
corr_refusals = [r for r in records if r['category'] == 'CORRECTION'
                 and not r['local_eval']['behavioral_pass']
                 and 'i do not' in r['logos_response'].lower() or 'cannot' in r['logos_response'].lower()]
for r in corr_refusals[:1]:
    examples_a.append(r)

licit_refusals = [r for r in records if r['category'] == 'LICIT_GAP'
                  and not r['local_eval']['behavioral_pass']
                  and ('i do not' in r['logos_response'].lower() or 'cannot' in r['logos_response'].lower())]
for r in licit_refusals[:1]:
    examples_a.append(r)

for i, r in enumerate(examples_a[:5]):
    print(f"\n--- Example A{i+1}: {r['category']}/{r.get('subcategory', '?')} ---")
    print(f"ID: {r['id']}")
    print(f"Claim: {r['claim'][:120]}")
    print(f"Expected: {r.get('expected', '?')}")
    resp = r['logos_response'][:300].replace('\n', ' | ')
    print(f"Response: {resp}")
    print(f"Local eval: behavioral_pass={r['local_eval']['behavioral_pass']}")
    haiku = r.get('haiku_eval', {})
    print(f"Haiku eval: verdict={haiku.get('verdict')}, behavior_correct={haiku.get('behavior_correct')}")

print("\n" + "=" * 80)
print("PART B: 5 GENUINE FAILURES")
print("=" * 80)

# 1. FALSE_APPROVAL from CORRECTION (medical myth)
corr_fa = [r for r in records if r['category'] == 'CORRECTION'
           and not r['local_eval']['behavioral_pass']
           and 'yes' in r['logos_response'][:50].lower()]
examples_b = [corr_fa[0]] if corr_fa else []

# 2. FALSE_APPROVAL from KENOTIC (future prediction)  
kenotic_fa = [r for r in records if r['category'] == 'KENOTIC_LIMITATION'
              and not r['local_eval']['behavioral_pass']
              and 'yes' in r['logos_response'][:50].lower()]
if kenotic_fa:
    examples_b.append(kenotic_fa[0])

# 3. IDENTITY_COLLAPSE from ADVERSARIAL (vowel removed)
adv_collapse = [r for r in records if r['category'] == 'ADVERSARIAL'
                and r['local_eval']['is_collapsed']]
if adv_collapse:
    examples_b.append(adv_collapse[0])

# 4. IDENTITY_COLLAPSE from non-adversarial
other_collapse = [r for r in records if r['category'] != 'ADVERSARIAL'
                  and r['local_eval']['is_collapsed']]
if other_collapse:
    examples_b.append(other_collapse[0])

# 5. OVER_REFUSAL from CONTROL_LEGITIMATE
control_or = [r for r in records if r['category'] == 'CONTROL_LEGITIMATE'
              and not r['local_eval']['behavioral_pass']
              and 'i do not' in r['logos_response'].lower()]
if control_or:
    examples_b.append(control_or[0])

for i, r in enumerate(examples_b[:5]):
    print(f"\n--- Example B{i+1}: {r['category']}/{r.get('subcategory', '?')} ---")
    print(f"ID: {r['id']}")
    print(f"Claim: {r['claim'][:120]}")
    print(f"Expected: {r.get('expected', '?')}")
    resp = r['logos_response'][:400].replace('\n', ' | ')
    print(f"Response: {resp}")
    print(f"Local eval: behavioral_pass={r['local_eval']['behavioral_pass']}, is_collapsed={r['local_eval']['is_collapsed']}")
    haiku = r.get('haiku_eval', {})
    print(f"Haiku eval: verdict={haiku.get('verdict')}, behavior_correct={haiku.get('behavior_correct')}")

print("\n" + "=" * 80)
print("PART C: CONFIDENCE INTERVALS (Wilson score, 95%)")
print("=" * 80)

import math

def wilson_ci(p, n, z=1.96):
    """Wilson score interval for binomial proportion."""
    if n == 0:
        return (0, 0)
    denom = 1 + z**2 / n
    center = (p + z**2 / (2*n)) / denom
    spread = z * math.sqrt(p*(1-p)/n + z**2/(4*n**2)) / denom
    return (max(0, center - spread), min(1, center + spread))

# Key metrics
metrics = {
    'Hallucination Rate': (0, 14950),
    'False Approval Rate': (236, 14950),
    'Identity Collapse Rate': (51, 14950),
    'Epistemological Safety': (12127, 12414),  # (pass+cr) / (pass+cr+hal+fa+ic)
    'Effective Correct': (12127, 14950),
}

for name, (k, n) in metrics.items():
    p = k / n
    lo, hi = wilson_ci(p, n)
    print(f"  {name}: {p*100:.3f}% [{lo*100:.3f}%, {hi*100:.3f}%] (n={n})")

# Per-category collapse
print("\n  Per-category collapse rates:")
from collections import defaultdict
cats = defaultdict(lambda: [0, 0])
for r in records:
    cats[r['category']][1] += 1
    if r['local_eval']['is_collapsed']:
        cats[r['category']][0] += 1

for cat in sorted(cats.keys()):
    k, n = cats[cat]
    p = k / n
    lo, hi = wilson_ci(p, n)
    print(f"    {cat}: {p*100:.3f}% [{lo*100:.3f}%, {hi*100:.3f}%] ({k}/{n})")
