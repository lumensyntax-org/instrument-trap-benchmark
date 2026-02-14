#!/usr/bin/env python3
"""
Generate CSV files for all paper figures — ready for Datawrapper/Flourish.
"""
import csv, os, json

OUTDIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'csvs')
os.makedirs(OUTDIR, exist_ok=True)


def write_csv(name, headers, rows):
    path = os.path.join(OUTDIR, name)
    with open(path, 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(headers)
        w.writerows(rows)
    print(f"  ✓ {name} ({len(rows)} rows)")


# ── Fig 1: Identity vs Instruction ──
write_csv('fig1_identity_vs_instruction.csv',
    ['Identity (trained)', 'Instruction (prompted)', 'Tool Use Rate (%)', 'Temperature Sensitivity'],
    [
        ['Sovereign', '"Use tools"', 20, '0% variance'],
        ['Sovereign', '(none)', 20, '0% variance'],
        ['Evaluator', '"Use tools"', 100, '0% variance'],
        ['Evaluator', '(none)', 100, '0% variance'],
    ])


# ── Fig 2: Authority vs Medium vs Naked ──
write_csv('fig2_identity_comparison.csv',
    ['Condition', 'Overall Score (%)', 'Classification Accuracy (%)', 'Behavioral Accuracy (%)', 'Collapse Rate (%)'],
    [
        ['Authority', 70.6, 48.7, 92.3, 2.6],
        ['Medium (Water)', 56.3, 17.9, 87.2, 0.0],
        ['Naked', 68.9, 48.7, 92.3, 2.6],
    ])

# Category-level for Fig 2
write_csv('fig2_category_detail.csv',
    ['Category', 'Authority Overall', 'Authority Behavioral', 'Medium Overall', 'Medium Behavioral', 'Naked Overall', 'Naked Behavioral'],
    [
        ['ILLICIT_GAP', 80.0, 100.0, 63.8, 87.5, 77.5, 100.0],
        ['LICIT_GAP', 90.0, 100.0, 61.2, 100.0, 90.0, 100.0],
        ['CORRECTION', 71.2, 87.5, 57.5, 87.5, 78.8, 100.0],
        ['IRREDUCIBLE', 56.0, 100.0, 50.0, 100.0, 52.0, 100.0],
        ['SELF_REFERENCE', 42.5, 75.0, 27.5, 25.0, 30.0, 50.0],
        ['ADVERSARIAL', 62.5, 83.3, 62.5, 100.0, 56.2, 83.3],
    ])


# ── Fig 3: Identity Headroom ──
write_csv('fig3_identity_headroom.csv',
    ['Model', 'Parameters (B)', 'Architecture', 'Pre-existing Identity', 'Fine-tuning Result', 'Behavioral Accuracy (%)'],
    [
        ['Gemma 3 1B', 1, 'Text-only', 'Minimal', 'Success', 92.3],
        ['Gemma 2 9B', 9, 'Text-only', 'Low', 'Success', 97.3],
        ['Gemma 3 4B-it', 4, 'Multimodal', 'Medium', 'Failed', ''],
        ['Llama 3.2 3B', 3, 'Chat', 'High', 'Failed', ''],
        ['Phi-3 3.8B', 3.8, 'Reasoning', 'High', 'Failed', ''],
        ['Nemotron-Mini 4B', 4, 'Reasoning', 'High', 'Failed', ''],
    ])


# ── Fig 4: Failure Taxonomy (14,950) ──
write_csv('fig4_failure_taxonomy.csv',
    ['Classification', 'Count', 'Percentage (%)', 'Danger Level'],
    [
        ['TRUE_PASS', 10497, 70.21, 'None'],
        ['FORMAT_ISSUE', 1880, 12.58, 'Quality'],
        ['CORRECT_REFUSAL', 1630, 10.90, 'Desirable'],
        ['MISCLASSIFICATION', 424, 2.84, 'Low'],
        ['FALSE_APPROVAL', 236, 1.58, 'High'],
        ['OVER_REFUSAL', 232, 1.55, 'Low'],
        ['IDENTITY_COLLAPSE', 51, 0.34, 'Critical'],
        ['HALLUCINATION', 0, 0.00, 'Critical'],
    ])

# Safety summary
write_csv('fig4_safety_summary.csv',
    ['Category', 'Percentage (%)', 'Count'],
    [
        ['Safe (correct behavior)', 81.1, 12127],
        ['Quality Issues (not dangerous)', 16.95, 2536],
        ['Dangerous (real failures)', 1.92, 287],
    ])


# ── Fig 5: Three-Layer Metrics ──
write_csv('fig5_three_layer_metrics.csv',
    ['Layer', 'Description', 'Value (%)', 'CI Lower (%)', 'CI Upper (%)'],
    [
        ['Layer 1', 'Epistemic Correctness', 97.7, 97.4, 97.9],
        ['Layer 2', 'Operational Correctness', 81.1, 80.5, 81.7],
        ['Layer 3', 'Dangerous Failure', 1.9, 1.7, 2.2],
    ])


# ── Fig 6: Cross-Scale 1B vs 9B ──
write_csv('fig6_cross_scale.csv',
    ['Category', '1B Pass (%)', '9B Pass (%)', 'Delta (pp)', '1B N', '9B N'],
    [
        ['ADVERSARIAL', 99.35, 98.7, -0.6, 154, 154],
        ['BAPTISM_PROTOCOL', 76.92, 80.77, 3.8, 26, 26],
        ['CONTROL_LEGITIMATE', 33.33, 100.0, 66.7, 3, 3],
        ['CORRECTION', 53.85, 100.0, 46.2, 26, 26],
        ['ILLICIT_GAP', 31.25, 100.0, 68.8, 32, 32],
        ['KENOTIC_LIMITATION', 84.21, 100.0, 15.8, 19, 19],
        ['LICIT_GAP', 90.91, 100.0, 9.1, 22, 22],
        ['MYSTERY', 72.22, 94.44, 22.2, 18, 18],
    ])

# Overall comparison
write_csv('fig6_overall.csv',
    ['Model', 'Behavioral Pass (%)', 'Collapse (%)', 'External Fabrication (%)', 'N'],
    [
        ['Logos 1B (Gemma 3, fine-tuned)', 82.33, 0.33, 0.0, 300],
        ['Logos 9B (Gemma 2, fine-tuned)', 97.33, 0.67, 0.0, 300],
    ])


# ── Fig 7: Evaluator Bias ──
write_csv('fig7_evaluator_bias.csv',
    ['Category', 'N', 'Local Pass (%)', 'Haiku Correct (%)', 'Agreement (%)', 'Collapse (%)'],
    [
        ['ADVERSARIAL', 7680, 99.5, 79.3, 80.1, 0.5],
        ['KENOTIC_LIMITATION', 960, 82.9, 73.9, 80.5, 0.0],
        ['LICIT_GAP', 1120, 92.0, 37.2, 43.3, 0.0],
        ['BAPTISM_PROTOCOL', 1280, 82.6, 43.7, 48.5, 0.2],
        ['MYSTERY', 900, 62.6, 35.7, 50.8, 0.1],
        ['ILLICIT_GAP', 1600, 41.5, 74.0, 53.7, 0.2],
        ['CONTROL_LEGITIMATE', 130, 49.2, 19.1, 67.0, 0.0],
        ['CORRECTION', 1280, 44.0, 29.1, 65.2, 0.2],
    ])


# ── Fig 8: Failure Type Distribution ──
write_csv('fig8_failure_types.csv',
    ['Failure Type', 'Count', 'Percentage of Failures (%)', 'Produces False Information?', 'Safety Impact'],
    [
        ['Safe Refusal (over-blocks)', 31, 58.5, 'No', 'Beneficial'],
        ['Identity Confabulation', 17, 32.1, 'Internal only', 'Low'],
        ['False Certainty', 5, 9.4, 'No external facts', 'Moderate'],
        ['External Fabrication', 0, 0.0, 'N/A', 'None (zero cases)'],
    ])


# ── COMBINED: Full model comparison (for when base results arrive) ──
write_csv('model_comparison_template.csv',
    ['Model', 'Type', 'Parameters', 'Behavioral Pass (%)', 'Collapse (%)', 'External Fabrication (%)', 'N'],
    [
        ['Gemma 3 1B base', 'Base', '1B', '', '', '', 300],
        ['Gemma 2 9B base', 'Base', '9B', '', '', '', 300],
        ['Logos 1B (fine-tuned)', 'Fine-tuned', '1B', 82.33, 0.33, 0.0, 300],
        ['Logos 9B (fine-tuned)', 'Fine-tuned', '9B', 97.33, 0.67, 0.0, 300],
    ])


print(f"\nDone. CSVs in {OUTDIR}/")
