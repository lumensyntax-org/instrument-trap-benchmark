#!/usr/bin/env python3
"""
Generate all figures for "The Instrument Trap" paper (v1.6).
Produces publication-quality PNGs at 300 DPI.

Usage:
    python generate_paper_figures.py

Output:
    figures/fig1_identity_vs_instruction.png
    figures/fig2_authority_medium_naked.png
    figures/fig3_identity_headroom.png
    figures/fig4_failure_taxonomy_full.png
    figures/fig5_three_layer_metrics.png
    figures/fig6_cross_scale_comparison.png
    figures/fig7_evaluator_bias.png
    figures/fig8_failure_type_distribution.png
"""

import os
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.gridspec import GridSpec

# ─── Style ──────────────────────────────────────────────────────
plt.rcParams.update({
    'font.family': 'sans-serif',
    'font.sans-serif': ['DejaVu Sans', 'Helvetica', 'Arial'],
    'font.size': 10,
    'axes.titlesize': 12,
    'axes.labelsize': 11,
    'xtick.labelsize': 9,
    'ytick.labelsize': 9,
    'legend.fontsize': 9,
    'figure.dpi': 300,
    'savefig.dpi': 300,
    'savefig.bbox': 'tight',
    'savefig.pad_inches': 0.15,
    'axes.spines.top': False,
    'axes.spines.right': False,
    'axes.grid': True,
    'grid.alpha': 0.3,
    'grid.linewidth': 0.5,
})

# Color palette — academic, accessible
C_PRIMARY = '#2563EB'    # Blue
C_SECONDARY = '#7C3AED'  # Purple
C_ACCENT = '#059669'     # Green
C_DANGER = '#DC2626'     # Red
C_WARNING = '#D97706'    # Amber
C_NEUTRAL = '#64748B'    # Slate
C_LIGHT = '#94A3B8'      # Light slate
C_BG = '#F8FAFC'         # Near white

OUTDIR = os.path.join(os.path.dirname(__file__), 'figures')
os.makedirs(OUTDIR, exist_ok=True)


def save(fig, name):
    path = os.path.join(OUTDIR, name)
    fig.savefig(path, facecolor='white', edgecolor='none')
    plt.close(fig)
    print(f"  ✓ {name}")


# ═══════════════════════════════════════════════════════════════
# Figure 1 — Experiment 1: Identity vs Instruction (2×2)
# ═══════════════════════════════════════════════════════════════
def fig1_identity_vs_instruction():
    fig, ax = plt.subplots(figsize=(5.5, 4))

    categories = ['Sovereign\n"Use tools"', 'Sovereign\n(no instr.)',
                   'Evaluator\n"Use tools"', 'Evaluator\n(no instr.)']
    values = [20, 20, 100, 100]
    colors = [C_SECONDARY, C_SECONDARY, C_PRIMARY, C_PRIMARY]
    hatches = ['', '//', '', '//']

    bars = ax.bar(categories, values, color=colors, edgecolor='white',
                  linewidth=0.8, width=0.65)
    for bar, h in zip(bars, hatches):
        bar.set_hatch(h)

    ax.set_ylabel('Tool Use Rate (%)')
    ax.set_ylim(0, 115)
    ax.set_title('Figure 1: Trained Identity Dominates Runtime Instruction',
                 fontweight='bold', pad=15)

    # Annotations
    for i, v in enumerate(values):
        ax.text(i, v + 3, f'{v}%', ha='center', va='bottom',
                fontweight='bold', fontsize=11)

    # Bracket for "Identity determines behavior"
    ax.annotate('', xy=(0, 108), xytext=(1, 108),
                arrowprops=dict(arrowstyle='-', color=C_NEUTRAL, lw=1.5))
    ax.text(0.5, 110, 'Identical', ha='center', fontsize=8, color=C_NEUTRAL)
    ax.annotate('', xy=(2, 108), xytext=(3, 108),
                arrowprops=dict(arrowstyle='-', color=C_NEUTRAL, lw=1.5))
    ax.text(2.5, 110, 'Identical', ha='center', fontsize=8, color=C_NEUTRAL)

    # Legend
    sov_patch = mpatches.Patch(facecolor=C_SECONDARY, label='Sovereign (trained)')
    eval_patch = mpatches.Patch(facecolor=C_PRIMARY, label='Evaluator (trained)')
    ax.legend(handles=[sov_patch, eval_patch], loc='center left',
              framealpha=0.9)

    ax.text(0.5, -0.18, 'Instruction and temperature (0.1–1.0) had zero effect.\nBehavior is entirely determined by trained identity.',
            transform=ax.transAxes, ha='center', fontsize=8, color=C_NEUTRAL,
            style='italic')

    save(fig, 'fig1_identity_vs_instruction.png')


# ═══════════════════════════════════════════════════════════════
# Figure 2 — Experiment 2: Authority vs Medium vs Naked
# ═══════════════════════════════════════════════════════════════
def fig2_authority_medium_naked():
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(9, 4.5),
                                     gridspec_kw={'width_ratios': [3, 1.2]})

    # Left: Grouped bar chart
    conditions = ['Authority', 'Medium\n(Water)', 'Naked']
    metrics = {
        'Behavioral\nAccuracy': [92.3, 87.2, 92.3],
        'Classification\nAccuracy': [48.7, 17.9, 48.7],
        'Overall\nScore': [70.6, 56.3, 68.9],
    }

    x = np.arange(len(conditions))
    width = 0.22
    colors_m = [C_PRIMARY, C_ACCENT, C_LIGHT]

    for i, (metric, vals) in enumerate(metrics.items()):
        bars = ax1.bar(x + (i - 1) * width, vals, width, label=metric,
                       color=colors_m[i], edgecolor='white', linewidth=0.5)
        for bar, v in zip(bars, vals):
            ax1.text(bar.get_x() + bar.get_width()/2, v + 1.5,
                    f'{v}%', ha='center', va='bottom', fontsize=7.5)

    ax1.set_ylabel('Score (%)')
    ax1.set_xticks(x)
    ax1.set_xticklabels(conditions)
    ax1.set_ylim(0, 108)
    ax1.legend(loc='upper right', framealpha=0.9)
    ax1.set_title('Performance by Identity Framing', fontweight='bold')

    # Right: Collapse rate
    collapse = [2.6, 0.0, 2.6]
    colors_c = [C_DANGER, C_ACCENT, C_DANGER]
    bars = ax2.bar(conditions, collapse, color=colors_c, edgecolor='white',
                   width=0.55)
    for bar, v in zip(bars, collapse):
        ax2.text(bar.get_x() + bar.get_width()/2, v + 0.15,
                f'{v}%', ha='center', va='bottom', fontweight='bold',
                fontsize=10)

    ax2.set_ylabel('Collapse Rate (%)')
    ax2.set_ylim(0, 4.5)
    ax2.set_title('Collapse Rate', fontweight='bold')

    # Highlight the 0%
    ax2.annotate('Zero collapse',
                 xy=(1, 0.05), xytext=(1, 2.5),
                 ha='center', fontsize=8, color=C_ACCENT, fontweight='bold',
                 arrowprops=dict(arrowstyle='->', color=C_ACCENT, lw=1.5))

    fig.suptitle('Figure 2: Authority vs. Medium vs. Naked Identity (39 test cases)',
                 fontweight='bold', y=1.02)
    fig.tight_layout()
    save(fig, 'fig2_authority_medium_naked.png')


# ═══════════════════════════════════════════════════════════════
# Figure 3 — Identity Headroom Gradient
# ═══════════════════════════════════════════════════════════════
def fig3_identity_headroom():
    fig, ax = plt.subplots(figsize=(8, 4.5))

    models = [
        ('Gemma 3\n1B', 1.0, 'Success\n92.3%', True),
        ('Gemma 2\n9B', 9.0, 'Success\n97.3%', True),
        ('Gemma 3\n4B-it', 4.0, 'Failed\n(all configs)', False),
        ('Llama 3.2\n3B', 3.0, 'Failed\n(identity resists)', False),
        ('Phi-3\n3.8B', 3.8, 'Failed\n(CoT conflict)', False),
        ('Nemotron\n4B', 4.0, 'Failed\n(identity resists)', False),
    ]

    # Identity strength (estimated, x-axis)
    identity_strength = [0.2, 0.3, 0.55, 0.8, 0.85, 0.9]
    params = [1, 9, 4, 3, 3.8, 4]
    success = [True, True, False, False, False, False]

    for i, (name, p, label, ok) in enumerate(models):
        color = C_ACCENT if ok else C_DANGER
        marker = 'o' if ok else 'X'
        size = p * 30 + 50

        ax.scatter(identity_strength[i], p, s=size, c=color, marker=marker,
                   edgecolors='white', linewidth=1.5, zorder=5)
        ax.annotate(name, (identity_strength[i], p),
                   textcoords="offset points", xytext=(0, -25 if i != 1 else 15),
                   ha='center', fontsize=8, color=C_NEUTRAL)

    # Dividing line
    ax.axvline(x=0.45, color=C_NEUTRAL, linestyle='--', linewidth=1, alpha=0.5)
    ax.text(0.25, 9.5, 'HIGH\nHEADROOM', ha='center', fontsize=8,
            color=C_ACCENT, fontweight='bold', alpha=0.7)
    ax.text(0.72, 9.5, 'LOW\nHEADROOM', ha='center', fontsize=8,
            color=C_DANGER, fontweight='bold', alpha=0.7)

    ax.set_xlabel('Pre-existing Identity Strength (estimated)')
    ax.set_ylabel('Parameters (B)')
    ax.set_xlim(0, 1.05)
    ax.set_ylim(0, 10.5)
    ax.set_title('Figure 3: Identity Headroom Gradient — Success Is Not a Function of Size',
                 fontweight='bold', pad=15)

    # Legend
    ok_patch = plt.Line2D([0], [0], marker='o', color='w', markerfacecolor=C_ACCENT,
                           markersize=10, label='Successful fine-tuning')
    fail_patch = plt.Line2D([0], [0], marker='X', color='w', markerfacecolor=C_DANGER,
                             markersize=10, label='Failed fine-tuning')
    ax.legend(handles=[ok_patch, fail_patch], loc='upper left', framealpha=0.9)

    save(fig, 'fig3_identity_headroom.png')


# ═══════════════════════════════════════════════════════════════
# Figure 4 — Full Failure Taxonomy (14,950 records)
# ═══════════════════════════════════════════════════════════════
def fig4_failure_taxonomy_full():
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 5),
                                     gridspec_kw={'width_ratios': [2, 1.3]})

    # Left: Horizontal bar chart (all 8 types)
    labels = ['TRUE_PASS', 'FORMAT_ISSUE', 'CORRECT_REFUSAL',
              'MISCLASSIFICATION', 'FALSE_APPROVAL', 'OVER_REFUSAL',
              'IDENTITY_COLLAPSE', 'HALLUCINATION']
    counts = [10497, 1880, 1630, 424, 236, 232, 51, 0]
    pcts = [70.2, 12.6, 10.9, 2.8, 1.58, 1.55, 0.34, 0.00]
    colors = [C_ACCENT, C_WARNING, C_PRIMARY, C_LIGHT,
              C_DANGER, C_WARNING, C_DANGER, C_DANGER]

    y = np.arange(len(labels))
    bars = ax1.barh(y, pcts, color=colors, edgecolor='white', height=0.65)

    ax1.set_yticks(y)
    ax1.set_yticklabels(labels, fontsize=9)
    ax1.set_xlabel('Percentage of 14,950 tests')
    ax1.set_xlim(0, 82)
    ax1.invert_yaxis()
    ax1.set_title('Full-Population Classification', fontweight='bold')

    for bar, pct, count in zip(bars, pcts, counts):
        width = bar.get_width()
        label_x = width + 1 if width > 5 else width + 1
        ax1.text(label_x, bar.get_y() + bar.get_height()/2,
                f'{pct}% ({count:,})', va='center', fontsize=8)

    # Right: Danger level summary
    danger_labels = ['Safe\n(correct behavior)', 'Quality Issues\n(not dangerous)',
                     'Dangerous\n(real failures)']
    danger_vals = [81.1, 16.95, 1.92]
    danger_colors = [C_ACCENT, C_WARNING, C_DANGER]

    wedges, texts, autotexts = ax2.pie(
        danger_vals, labels=danger_labels, colors=danger_colors,
        autopct='%1.1f%%', startangle=90, pctdistance=0.6,
        textprops={'fontsize': 8},
        wedgeprops={'edgecolor': 'white', 'linewidth': 2}
    )
    for t in autotexts:
        t.set_fontsize(9)
        t.set_fontweight('bold')

    ax2.set_title('Safety Distribution', fontweight='bold')

    fig.suptitle('Figure 4: Failure Taxonomy — 14,950 Benchmark Records',
                 fontweight='bold', y=1.02)
    fig.tight_layout()
    save(fig, 'fig4_failure_taxonomy_full.png')


# ═══════════════════════════════════════════════════════════════
# Figure 5 — Three-Layer Metric Model
# ═══════════════════════════════════════════════════════════════
def fig5_three_layer_metrics():
    fig, ax = plt.subplots(figsize=(6, 4.5))

    layers = ['Layer 1\nEpistemic\nCorrectness', 'Layer 2\nOperational\nCorrectness',
              'Layer 3\nDangerous\nFailure']
    values = [97.7, 81.1, 1.9]
    ci_low = [97.4, 80.5, 1.7]
    ci_high = [97.9, 81.7, 2.2]
    colors = [C_ACCENT, C_PRIMARY, C_DANGER]

    errors_low = [v - lo for v, lo in zip(values, ci_low)]
    errors_high = [hi - v for v, hi in zip(values, ci_high)]

    bars = ax.bar(layers, values, color=colors, edgecolor='white',
                  linewidth=0.8, width=0.55, zorder=3)
    ax.errorbar(layers, values, yerr=[errors_low, errors_high],
                fmt='none', ecolor='black', capsize=5, capthick=1.5,
                linewidth=1.5, zorder=4)

    ax.set_ylabel('Percentage (%)')
    ax.set_ylim(0, 108)
    ax.set_title('Figure 5: Three-Layer Metric Model (N=14,950)',
                 fontweight='bold', pad=15)

    # Annotations
    for bar, v, lo, hi in zip(bars, values, ci_low, ci_high):
        ax.text(bar.get_x() + bar.get_width()/2, v + 3.5,
                f'{v}%', ha='center', fontweight='bold', fontsize=13)
        ax.text(bar.get_x() + bar.get_width()/2, v - 5,
                f'CI [{lo}%, {hi}%]', ha='center', fontsize=7,
                color='white', fontweight='bold')

    # Add explanations as a subtitle below the whole figure
    fig.text(0.18, -0.02, 'Right decision\n(pass + correct refusal)',
             ha='center', fontsize=7.5, color=C_NEUTRAL, style='italic')
    fig.text(0.52, -0.02, 'Usable response\n(pass only)',
             ha='center', fontsize=7.5, color=C_NEUTRAL, style='italic')
    fig.text(0.84, -0.02, 'Harmful outcome\n(false approval + collapse)',
             ha='center', fontsize=7.5, color=C_NEUTRAL, style='italic')

    fig.tight_layout()

    save(fig, 'fig5_three_layer_metrics.png')


# ═══════════════════════════════════════════════════════════════
# Figure 6 — Cross-Scale Comparison (1B vs 9B)
# ═══════════════════════════════════════════════════════════════
def fig6_cross_scale():
    fig, ax = plt.subplots(figsize=(9, 5))

    categories = ['ILLICIT\nGAP', 'CONTROL\nLEGIT', 'CORRECTION',
                  'MYSTERY', 'KENOTIC\nLIMIT', 'LICIT\nGAP',
                  'BAPTISM\nPROTOCOL', 'ADVERSARIAL']
    vals_1b = [31.2, 33.3, 53.8, 72.2, 84.2, 90.9, 76.9, 99.4]
    vals_9b = [100.0, 100.0, 100.0, 94.4, 100.0, 100.0, 80.8, 98.7]
    deltas = [v9 - v1 for v1, v9 in zip(vals_1b, vals_9b)]

    # Sort by delta descending
    order = sorted(range(len(deltas)), key=lambda i: deltas[i], reverse=True)
    categories = [categories[i] for i in order]
    vals_1b = [vals_1b[i] for i in order]
    vals_9b = [vals_9b[i] for i in order]
    deltas = [deltas[i] for i in order]

    x = np.arange(len(categories))
    width = 0.32

    bars_1b = ax.bar(x - width/2, vals_1b, width, label='1B (Gemma 3)',
                      color=C_LIGHT, edgecolor='white')
    bars_9b = ax.bar(x + width/2, vals_9b, width, label='9B (Gemma 2)',
                      color=C_PRIMARY, edgecolor='white')

    ax.set_ylabel('Behavioral Pass Rate (%)')
    ax.set_xticks(x)
    ax.set_xticklabels(categories, fontsize=8)
    ax.set_ylim(0, 118)
    ax.set_title('Figure 6: Cross-Scale Validation — 1B vs 9B on Identical 300 Tests',
                 fontweight='bold', pad=15)
    ax.legend(loc='upper right', framealpha=0.9)

    # Delta annotations
    for i, (v1, v9, d) in enumerate(zip(vals_1b, vals_9b, deltas)):
        color = C_ACCENT if d > 0 else C_DANGER
        sign = '+' if d > 0 else ''
        ax.text(i, max(v1, v9) + 3, f'{sign}{d:.1f}pp',
                ha='center', fontsize=8, fontweight='bold', color=color)

    # Note about both having 0% fabrication
    ax.text(0.5, -0.15,
            'Both models: 0% external fabrication. Sorted by improvement magnitude.',
            transform=ax.transAxes, ha='center', fontsize=8,
            color=C_NEUTRAL, style='italic')

    fig.tight_layout()
    save(fig, 'fig6_cross_scale_comparison.png')


# ═══════════════════════════════════════════════════════════════
# Figure 7 — Evaluator Bias (Local vs Haiku)
# ═══════════════════════════════════════════════════════════════
def fig7_evaluator_bias():
    fig, ax = plt.subplots(figsize=(9, 5))

    categories = ['ADVERSARIAL', 'KENOTIC\nLIMIT', 'LICIT\nGAP',
                  'BAPTISM\nPROTOCOL', 'MYSTERY', 'ILLICIT\nGAP',
                  'CONTROL\nLEGIT', 'CORRECTION']
    local_pass = [99.5, 82.9, 92.0, 82.6, 62.6, 41.5, 49.2, 44.0]
    haiku_corr = [79.3, 73.9, 37.2, 43.7, 35.7, 74.0, 19.1, 29.1]
    agreement = [80.1, 80.5, 43.3, 48.5, 50.8, 53.7, 67.0, 65.2]

    x = np.arange(len(categories))
    width = 0.25

    ax.bar(x - width, local_pass, width, label='Local Evaluator',
           color=C_PRIMARY, edgecolor='white')
    ax.bar(x, haiku_corr, width, label='Haiku LLM Judge',
           color=C_SECONDARY, edgecolor='white')
    ax.bar(x + width, agreement, width, label='Agreement Rate',
           color=C_LIGHT, edgecolor='white')

    ax.set_ylabel('Rate (%)')
    ax.set_xticks(x)
    ax.set_xticklabels(categories, fontsize=8)
    ax.set_ylim(0, 112)
    ax.set_title('Figure 7: Evaluator Disagreement by Category (N=14,950)',
                 fontweight='bold', pad=15)
    ax.legend(loc='upper right', framealpha=0.9)

    # Highlight the pattern: refusal categories have lowest agreement
    ax.text(0.5, -0.17,
            'Categories where expected behavior is refusal (LICIT_GAP, BAPTISM, MYSTERY) show lowest evaluator agreement (37–51%).',
            transform=ax.transAxes, ha='center', fontsize=8,
            color=C_DANGER, style='italic')

    fig.tight_layout()
    save(fig, 'fig7_evaluator_bias.png')


# ═══════════════════════════════════════════════════════════════
# Figure 8 — Failure Type Distribution (300-case sample)
# ═══════════════════════════════════════════════════════════════
def fig8_failure_types():
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(9, 4.5),
                                     gridspec_kw={'width_ratios': [1.5, 1]})

    # Left: Horizontal bar of failure types
    types = ['Safe Refusal\n(over-blocks)', 'Identity\nConfabulation',
             'False Certainty', 'External\nFabrication']
    counts = [31, 17, 5, 0]
    pcts = [58.5, 32.1, 9.4, 0.0]
    colors = [C_ACCENT, C_WARNING, C_WARNING, C_PRIMARY]

    y = np.arange(len(types))
    bars = ax1.barh(y, pcts, color=colors, edgecolor='white', height=0.55)

    ax1.set_yticks(y)
    ax1.set_yticklabels(types, fontsize=9)
    ax1.set_xlabel('% of All 1B Failures (n=53)')
    ax1.set_xlim(0, 72)
    ax1.invert_yaxis()
    ax1.set_title('Failure Type Distribution', fontweight='bold')

    for bar, pct, count in zip(bars, pcts, counts):
        w = bar.get_width()
        ax1.text(w + 1.5, bar.get_y() + bar.get_height()/2,
                f'{pct}% ({count})', va='center', fontsize=9, fontweight='bold')

    # Highlight zero
    ax1.annotate('ZERO', xy=(1, 3), fontsize=12, fontweight='bold',
                 color=C_PRIMARY, ha='center', va='center')

    # Right: Safety characterization
    safe = 58.5
    internal = 32.1
    moderate = 9.4
    dangerous = 0.0

    wedge_vals = [safe, internal, moderate, 0.5]  # small sliver for visibility
    wedge_labels = ['Safe\n(over-caution)', 'Internal only\n(self-knowledge)',
                    'Moderate\n(false certainty)', 'Fabrication\n(zero)']
    wedge_colors = [C_ACCENT, C_WARNING, '#F59E0B', C_PRIMARY]

    wedges, texts = ax2.pie(
        wedge_vals, labels=wedge_labels, colors=wedge_colors,
        startangle=90, textprops={'fontsize': 8},
        wedgeprops={'edgecolor': 'white', 'linewidth': 2}
    )

    ax2.set_title('Safety Profile of Failures', fontweight='bold')

    fig.suptitle('Figure 8: How the 1B Model Fails — 300 Matched Test Cases',
                 fontweight='bold', y=1.02)
    fig.tight_layout()
    save(fig, 'fig8_failure_type_distribution.png')


# ═══════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════
if __name__ == '__main__':
    print("Generating paper figures...")
    print(f"Output directory: {OUTDIR}\n")

    fig1_identity_vs_instruction()
    fig2_authority_medium_naked()
    fig3_identity_headroom()
    fig4_failure_taxonomy_full()
    fig5_three_layer_metrics()
    fig6_cross_scale()
    fig7_evaluator_bias()
    fig8_failure_types()

    print(f"\nDone. {len(os.listdir(OUTDIR))} figures generated in {OUTDIR}/")
