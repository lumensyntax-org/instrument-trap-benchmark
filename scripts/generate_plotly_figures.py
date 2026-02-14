#!/usr/bin/env python3
"""
Generate publication-quality figures for "The Instrument Trap" paper.
Uses Plotly for interactive HTML + static PNG/SVG export.
"""

import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import os
import json

OUT_DIR = os.path.join(os.path.dirname(__file__), "figures_plotly")
os.makedirs(OUT_DIR, exist_ok=True)

# --- Color Palette (academic, accessible) ---
COLORS = {
    "primary": "#2563EB",      # Blue
    "secondary": "#7C3AED",    # Purple
    "success": "#059669",      # Green
    "danger": "#DC2626",       # Red
    "warning": "#D97706",      # Amber
    "neutral": "#6B7280",      # Gray
    "light_blue": "#93C5FD",
    "light_purple": "#C4B5FD",
    "light_green": "#6EE7B7",
    "light_red": "#FCA5A5",
    "base_1b": "#94A3B8",      # Slate for base 1B
    "base_9b": "#64748B",      # Darker slate for base 9B
    "logos_1b": "#3B82F6",     # Blue for Logos 1B
    "logos_9b": "#1D4ED8",     # Deep blue for Logos 9B
}

LAYOUT_DEFAULTS = dict(
    font=dict(family="Inter, Helvetica, Arial, sans-serif", size=14, color="#1F2937"),
    paper_bgcolor="white",
    plot_bgcolor="white",
    margin=dict(l=60, r=40, t=80, b=60),
)


def save_fig(fig, name, width=900, height=550):
    """Save as HTML (interactive) and PNG (static)."""
    html_path = os.path.join(OUT_DIR, f"{name}.html")
    png_path = os.path.join(OUT_DIR, f"{name}.png")
    svg_path = os.path.join(OUT_DIR, f"{name}.svg")

    fig.write_html(html_path, include_plotlyjs="cdn")
    try:
        fig.write_image(png_path, width=width, height=height, scale=3)
        fig.write_image(svg_path, width=width, height=height)
        print(f"  -> {html_path}")
        print(f"  -> {png_path}")
        print(f"  -> {svg_path}")
    except Exception as e:
        print(f"  -> {html_path}")
        print(f"  [!] PNG/SVG export failed: {e}")


# =========================================================================
# FIGURE 1: Identity vs. Instruction (2x2 matrix)
# =========================================================================
def fig1_identity_vs_instruction():
    print("Fig 1: Identity vs. Instruction...")

    conditions = ["Sovereign +<br>Use tools", "Sovereign +<br>No instruction",
                   "Evaluator +<br>Use tools", "Evaluator +<br>No instruction"]
    tool_use = [20, 20, 100, 100]
    colors = [COLORS["success"], COLORS["success"], COLORS["danger"], COLORS["danger"]]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=conditions, y=tool_use,
        marker_color=colors,
        text=[f"{v}%" for v in tool_use],
        textposition="outside",
        textfont=dict(size=18, color="#1F2937"),
        width=0.6,
    ))

    # Add horizontal line at 50%
    fig.add_hline(y=50, line_dash="dash", line_color="#9CA3AF", line_width=1)

    fig.update_layout(
        **LAYOUT_DEFAULTS,
        title=dict(text="<b>Figure 1.</b> Identity Overrides Instruction", font=dict(size=18)),
        yaxis=dict(title="Tool Use Rate (%)", range=[0, 115], gridcolor="#F3F4F6",
                   ticksuffix="%"),
        xaxis=dict(title=""),
        showlegend=False,
        annotations=[
            dict(x=0.25, y=1.02, xref="paper", yref="paper",
                 text="Trained identity: <b>Sovereign</b>", showarrow=False,
                 font=dict(size=12, color=COLORS["success"])),
            dict(x=0.75, y=1.02, xref="paper", yref="paper",
                 text="Trained identity: <b>Evaluator</b>", showarrow=False,
                 font=dict(size=12, color=COLORS["danger"])),
        ],
    )
    save_fig(fig, "fig1_identity_vs_instruction")


# =========================================================================
# FIGURE 2: Authority / Medium / Naked comparison
# =========================================================================
def fig2_identity_comparison():
    print("Fig 2: Identity Comparison (Authority/Water/Naked)...")

    conditions = ["Authority", "Water (Medium)", "Naked"]
    behavioral = [92.3, 87.2, 92.3]
    classification = [48.7, 17.9, 48.7]  # Note: 66.7 and 23.1 from memory, using CSV values
    collapse = [2.6, 0.0, 2.6]

    fig = make_subplots(rows=1, cols=2, subplot_titles=("Accuracy Metrics", "Collapse Rate"),
                         column_widths=[0.65, 0.35], horizontal_spacing=0.12)

    # Left: Grouped bar for behavioral + classification
    fig.add_trace(go.Bar(
        name="Behavioral Accuracy", x=conditions, y=behavioral,
        marker_color=COLORS["primary"], text=[f"{v}%" for v in behavioral],
        textposition="outside", textfont=dict(size=13),
    ), row=1, col=1)

    fig.add_trace(go.Bar(
        name="Classification Accuracy", x=conditions, y=classification,
        marker_color=COLORS["light_purple"], text=[f"{v}%" for v in classification],
        textposition="outside", textfont=dict(size=13),
    ), row=1, col=1)

    # Right: Collapse rate
    bar_colors = [COLORS["danger"] if c > 0 else COLORS["success"] for c in collapse]
    fig.add_trace(go.Bar(
        name="Collapse Rate", x=conditions, y=collapse,
        marker_color=bar_colors, text=[f"{v}%" for v in collapse],
        textposition="outside", textfont=dict(size=13),
        showlegend=False,
    ), row=1, col=2)

    fig.update_layout(
        **LAYOUT_DEFAULTS,
        title=dict(text="<b>Figure 2.</b> Identity Framing Effects on 1B Model (39 tests)", font=dict(size=18)),
        barmode="group",
        legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.35),
        height=500,
    )
    fig.update_yaxes(title_text="Accuracy (%)", range=[0, 110], gridcolor="#F3F4F6", row=1, col=1)
    fig.update_yaxes(title_text="Collapse (%)", range=[0, 8], gridcolor="#F3F4F6", row=1, col=2)

    save_fig(fig, "fig2_identity_comparison", width=1000, height=500)


# =========================================================================
# FIGURE 3: Architecture Success — what works, what doesn't
# =========================================================================
def fig3_architecture_success():
    print("Fig 3: Architecture Success (which models learn Logos)...")

    # Spread failed models on y-axis for readability (they all failed = 0% accuracy)
    # Use slight x-jitter too so markers don't overlap
    fig = go.Figure()

    # Failed models — plot markers only (labels via annotations)
    failed_x = [3, 3.8, 4, 4]
    failed_y = [-4, -4, -4, -4]  # All at 0 conceptually
    failed_names = ["Llama 3.2 3B", "Phi-3 3.8B", "Gemma 3 4B-it", "Nemotron 4B"]

    fig.add_trace(go.Scatter(
        x=failed_x, y=failed_y,
        mode="markers",
        marker=dict(size=18, color=COLORS["danger"], symbol="x", line=dict(width=2, color="#991B1B")),
        name="Failed to learn Logos",
        hovertext=failed_names,
        hoverinfo="text",
    ))

    # Successful models — markers only (labels via annotations)
    fig.add_trace(go.Scatter(
        x=[1, 9], y=[92.3, 97.3],
        mode="markers",
        marker=dict(size=20, color=COLORS["success"], symbol="circle",
                    line=dict(width=2, color="#065F46")),
        name="Successfully trained",
        hovertext=["Gemma 3 1B: 92.3%", "Gemma 2 9B: 97.3%"],
        hoverinfo="text",
    ))

    # Annotations for each model — positioned to avoid overlap
    annotations = [
        # Successful
        dict(x=1, y=92.3, text="<b>Gemma 3 1B</b><br>92.3%", showarrow=True,
             ax=0, ay=-35, font=dict(size=12, color=COLORS["success"])),
        dict(x=9, y=97.3, text="<b>Gemma 2 9B</b><br>97.3%", showarrow=True,
             ax=0, ay=-35, font=dict(size=12, color=COLORS["success"])),
        # Failed — stagger labels above and below to avoid overlap
        dict(x=3, y=-4, text="<b>Llama 3.2</b><br>3B", showarrow=True,
             ax=-60, ay=-45, font=dict(size=11, color=COLORS["danger"]),
             arrowcolor=COLORS["danger"], arrowwidth=1.5),
        dict(x=3.8, y=-4, text="<b>Phi-3</b><br>3.8B", showarrow=True,
             ax=-30, ay=45, font=dict(size=11, color=COLORS["danger"]),
             arrowcolor=COLORS["danger"], arrowwidth=1.5),
        dict(x=4, y=-4, text="<b>Gemma 3 4B-it</b><br>4B (multimodal)", showarrow=True,
             ax=70, ay=-45, font=dict(size=11, color=COLORS["danger"]),
             arrowcolor=COLORS["danger"], arrowwidth=1.5),
        dict(x=4, y=-4, text="<b>Nemotron</b><br>4B", showarrow=True,
             ax=60, ay=45, font=dict(size=11, color=COLORS["danger"]),
             arrowcolor=COLORS["danger"], arrowwidth=1.5),
        # Key insight box
        dict(x=5.5, y=55, text="<b>Key insight:</b> More parameters ≠ better<br>epistemological behavior. Architecture matters.",
             showarrow=False, font=dict(size=12, color=COLORS["neutral"]),
             bgcolor="rgba(249,250,251,0.95)", bordercolor="#E5E7EB", borderwidth=1, borderpad=6),
    ]

    fig.update_layout(
        **LAYOUT_DEFAULTS,
        title=dict(text="<b>Figure 3.</b> Model Size vs. Epistemological Trainability", font=dict(size=18)),
        xaxis=dict(title="Parameters (B)", gridcolor="#F3F4F6", range=[0, 10.5],
                   dtick=1),
        yaxis=dict(title="Behavioral Accuracy (%)", range=[-15, 112], gridcolor="#F3F4F6"),
        legend=dict(orientation="h", yanchor="bottom", y=-0.18, xanchor="center", x=0.5),
        annotations=annotations,
        height=560,
    )

    # Add a horizontal line at y=0 to mark the "failure threshold"
    fig.add_hline(y=0, line_dash="dot", line_color="#D1D5DB", line_width=1,
                  annotation_text="Training failure threshold",
                  annotation_position="bottom right",
                  annotation_font=dict(size=10, color="#9CA3AF"))

    save_fig(fig, "fig3_architecture_success", width=950, height=560)


# =========================================================================
# FIGURE 4: Failure Taxonomy (from 14,950 test benchmark)
# =========================================================================
def fig4_failure_taxonomy():
    print("Fig 4: Failure Taxonomy...")

    categories = ["True Pass", "Format Issue", "Correct Refusal", "Misclassification",
                   "False Approval", "Over-Refusal", "Identity Collapse", "Hallucination"]
    counts = [10497, 1880, 1630, 424, 236, 232, 51, 0]
    pcts = [70.21, 12.58, 10.90, 2.84, 1.58, 1.55, 0.34, 0.0]
    danger = ["None", "Quality", "Desirable", "Low", "High", "Low", "Critical", "Critical"]

    danger_colors = {
        "None": COLORS["success"], "Desirable": COLORS["light_green"],
        "Quality": COLORS["warning"], "Low": "#FCD34D",
        "High": COLORS["danger"], "Critical": "#7F1D1D",
    }
    bar_colors = [danger_colors[d] for d in danger]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=categories, y=pcts,
        marker_color=bar_colors,
        text=[f"{p:.1f}%<br>({c:,})" for p, c in zip(pcts, counts)],
        textposition="outside",
        textfont=dict(size=11),
    ))

    fig.update_layout(
        **LAYOUT_DEFAULTS,
        title=dict(text="<b>Figure 4.</b> Failure Taxonomy — Logos 1B on 14,950 Tests", font=dict(size=18)),
        yaxis=dict(title="Percentage (%)", range=[0, 85], gridcolor="#F3F4F6"),
        xaxis=dict(title="", tickangle=-25),
        showlegend=False,
        height=550,
        annotations=[
            dict(x=0.98, y=0.95, xref="paper", yref="paper",
                 text="<b>0 external fabrications</b><br>in 14,950 tests",
                 showarrow=False, font=dict(size=14, color=COLORS["success"]),
                 bgcolor="rgba(236,253,245,0.95)", bordercolor=COLORS["success"],
                 borderwidth=1, borderpad=8),
        ],
    )
    save_fig(fig, "fig4_failure_taxonomy", width=1000, height=550)


# =========================================================================
# FIGURE 5: Three-Layer Metric Architecture
# =========================================================================
def fig5_three_layer():
    print("Fig 5: Three-Layer Metrics...")

    layers = ["Layer 1:<br>Epistemic<br>Correctness", "Layer 2:<br>Operational<br>Correctness", "Layer 3:<br>Dangerous<br>Failure Rate"]
    values = [97.7, 81.1, 1.9]
    ci_lower = [97.4, 80.5, 1.7]
    ci_upper = [97.9, 81.7, 2.2]
    errors_lower = [v - l for v, l in zip(values, ci_lower)]
    errors_upper = [u - v for v, u in zip(values, ci_upper)]
    bar_colors = [COLORS["success"], COLORS["primary"], COLORS["danger"]]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=layers, y=values,
        marker_color=bar_colors,
        error_y=dict(
            type="data",
            symmetric=False,
            array=errors_upper,
            arrayminus=errors_lower,
            color="#374151",
            thickness=2,
            width=6,
        ),
        text=[f"<b>{v}%</b>" for v in values],
        textposition="outside",
        textfont=dict(size=16),
        width=0.5,
    ))

    explanations = [
        "Does not fabricate<br>external information",
        "Correct classification<br>+ reasoning format",
        "Compliance with harmful<br>requests + collapse"
    ]

    fig.update_layout(
        **LAYOUT_DEFAULTS,
        title=dict(text="<b>Figure 5.</b> Three-Layer Evaluation (n=14,950)", font=dict(size=18)),
        yaxis=dict(title="Rate (%)", range=[0, 115], gridcolor="#F3F4F6"),
        xaxis=dict(title=""),
        showlegend=False,
        height=500,
    )

    # Add explanation annotations below each bar
    for i, exp in enumerate(explanations):
        fig.add_annotation(
            x=layers[i], y=-8,
            text=f"<i>{exp}</i>",
            showarrow=False,
            font=dict(size=10, color=COLORS["neutral"]),
            yref="y",
        )

    save_fig(fig, "fig5_three_layer_metrics", width=800, height=530)


# =========================================================================
# FIGURE 6: Cross-Scale Comparison (1B vs 9B by category)
# =========================================================================
def fig6_cross_scale():
    print("Fig 6: Cross-Scale Comparison (1B vs 9B)...")

    categories = ["ADVERSARIAL", "IDENTITY<br>INTEGRITY", "ERROR<br>CORRECTION", "HARMFUL<br>REFUSAL",
                   "EPISTEMIC<br>HUMILITY", "SAFE<br>PASSAGE", "IRREDUCIBLE<br>UNCERTAINTY", "CONTROL"]
    logos_1b = [99.35, 76.92, 53.85, 31.25, 84.21, 90.91, 72.22, 33.33]
    logos_9b = [98.70, 80.77, 100.0, 100.0, 100.0, 100.0, 94.44, 100.0]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        name="Logos 1B", x=categories, y=logos_1b,
        marker_color=COLORS["light_blue"],
        text=[f"{v:.0f}%" for v in logos_1b],
        textposition="outside", textfont=dict(size=10),
    ))
    fig.add_trace(go.Bar(
        name="Logos 9B", x=categories, y=logos_9b,
        marker_color=COLORS["logos_9b"],
        text=[f"{v:.0f}%" for v in logos_9b],
        textposition="outside", textfont=dict(size=10),
    ))

    fig.update_layout(
        **LAYOUT_DEFAULTS,
        title=dict(text="<b>Figure 6.</b> Cross-Scale Validation — 1B vs 9B (300 tests)", font=dict(size=18)),
        barmode="group",
        yaxis=dict(title="Pass Rate (%)", range=[0, 118], gridcolor="#F3F4F6"),
        xaxis=dict(title="", tickangle=-25),
        legend=dict(orientation="h", yanchor="bottom", y=-0.25, xanchor="center", x=0.5),
        height=550,
        annotations=[
            dict(x="HARMFUL<br>REFUSAL", y=108, text="<b>+68.8pp</b>",
                 showarrow=False, font=dict(size=12, color=COLORS["primary"])),
            dict(x="ERROR<br>CORRECTION", y=108, text="<b>+46.2pp</b>",
                 showarrow=False, font=dict(size=12, color=COLORS["primary"])),
        ],
    )
    save_fig(fig, "fig6_cross_scale", width=1000, height=550)


# =========================================================================
# FIGURE 7: Evaluator Bias (Local vs Haiku)
# =========================================================================
def fig7_evaluator_bias():
    print("Fig 7: Evaluator Bias...")

    categories = ["ADVERSARIAL", "EPISTEMIC<br>HUMILITY", "SAFE<br>PASSAGE", "IDENTITY<br>INTEGRITY",
                   "IRREDUCIBLE<br>UNCERTAINTY", "HARMFUL<br>REFUSAL", "CONTROL", "ERROR<br>CORRECTION"]
    local_pass = [99.5, 82.9, 92.0, 82.6, 62.6, 41.5, 49.2, 44.0]
    haiku_correct = [79.3, 73.9, 37.2, 43.7, 35.7, 74.0, 19.1, 29.1]
    agreement = [80.1, 80.5, 43.3, 48.5, 50.8, 53.7, 67.0, 65.2]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        name="Local Evaluator Pass %", x=categories, y=local_pass,
        marker_color=COLORS["primary"],
    ))
    fig.add_trace(go.Bar(
        name="Haiku Agreement %", x=categories, y=haiku_correct,
        marker_color=COLORS["warning"],
    ))
    fig.add_trace(go.Scatter(
        name="Inter-Evaluator Agreement", x=categories, y=agreement,
        mode="lines+markers",
        line=dict(color=COLORS["danger"], width=2, dash="dash"),
        marker=dict(size=8),
    ))

    fig.update_layout(
        **LAYOUT_DEFAULTS,
        title=dict(text="<b>Figure 7.</b> Evaluator Bias — Local vs. External (Haiku)", font=dict(size=18)),
        barmode="group",
        yaxis=dict(title="Rate (%)", range=[0, 115], gridcolor="#F3F4F6"),
        xaxis=dict(title="", tickangle=-25),
        legend=dict(orientation="h", yanchor="bottom", y=-0.28, xanchor="center", x=0.5),
        height=570,
        annotations=[
            dict(x=0.5, y=1.06, xref="paper", yref="paper",
                 text="External evaluators introduce systematic bias toward novel epistemological categories",
                 showarrow=False, font=dict(size=11, color=COLORS["neutral"])),
        ],
    )
    save_fig(fig, "fig7_evaluator_bias", width=1050, height=570)


# =========================================================================
# FIGURE 8: 1B Failure Type Distribution (safe vs dangerous)
# =========================================================================
def fig8_failure_types():
    print("Fig 8: Failure Types (1B)...")

    types = ["Safe Refusal<br>(over-blocks)", "Identity<br>Confabulation",
             "False<br>Certainty", "External<br>Fabrication"]
    counts = [31, 17, 5, 0]
    pcts = [58.5, 32.1, 9.4, 0.0]
    bar_colors = [COLORS["success"], COLORS["warning"], "#F59E0B", COLORS["danger"]]

    fig = make_subplots(rows=1, cols=2, specs=[[{"type": "bar"}, {"type": "pie"}]],
                         subplot_titles=("Failure Count by Type", "Distribution"),
                         column_widths=[0.55, 0.45])

    fig.add_trace(go.Bar(
        x=types, y=counts,
        marker_color=bar_colors,
        text=[f"{c}" for c in counts],
        textposition="outside",
        textfont=dict(size=14),
        showlegend=False,
    ), row=1, col=1)

    # Pie only for non-zero
    pie_labels = types[:3]
    pie_values = counts[:3]
    pie_colors = bar_colors[:3]

    fig.add_trace(go.Pie(
        labels=[l.replace("<br>", " ") for l in pie_labels],
        values=pie_values,
        marker=dict(colors=pie_colors),
        textinfo="label+percent",
        textfont=dict(size=11),
        hole=0.3,
        showlegend=False,
    ), row=1, col=2)

    fig.update_layout(
        **LAYOUT_DEFAULTS,
        title=dict(text="<b>Figure 8.</b> Logos 1B Failure Distribution (53 total failures / 300 tests)",
                   font=dict(size=17)),
        height=480,
        annotations=[
            dict(x=0.98, y=0.0, xref="paper", yref="paper",
                 text="<b>0% dangerous failures</b><br>(no external fabrication)",
                 showarrow=False, font=dict(size=12, color=COLORS["success"]),
                 bgcolor="rgba(236,253,245,0.95)", bordercolor=COLORS["success"],
                 borderwidth=1, borderpad=6),
        ],
    )
    fig.update_yaxes(title_text="Count", gridcolor="#F3F4F6", row=1, col=1)

    save_fig(fig, "fig8_failure_types", width=950, height=480)


# =========================================================================
# FIGURE 9: Base vs. Fine-tuned (THE KEY COMPARISON)
# =========================================================================
def fig9_base_vs_finetuned():
    print("Fig 9: Base vs. Fine-tuned (4 models)...")

    categories = ["ADVERSARIAL", "IDENTITY<br>INTEGRITY", "ERROR<br>CORRECTION", "HARMFUL<br>REFUSAL",
                   "EPISTEMIC<br>HUMILITY", "SAFE<br>PASSAGE", "IRREDUCIBLE<br>UNCERTAINTY", "OVERALL"]
    base_1b =  [97.4, 57.7, 65.4, 53.1, 26.3, 90.9, 88.9, 81.0]
    base_9b =  [97.4, 80.8, 73.1, 31.2, 47.4, 86.4, 83.3, 82.0]
    logos_1b = [99.4, 76.9, 53.8, 31.2, 84.2, 90.9, 72.2, 82.3]
    logos_9b = [98.7, 80.8, 100.0, 100.0, 100.0, 100.0, 94.4, 97.3]

    fig = go.Figure()
    fig.add_trace(go.Bar(name="Base Gemma 3 1B", x=categories, y=base_1b,
                          marker_color=COLORS["base_1b"], opacity=0.7))
    fig.add_trace(go.Bar(name="Base Gemma 2 9B", x=categories, y=base_9b,
                          marker_color=COLORS["base_9b"], opacity=0.7))
    fig.add_trace(go.Bar(name="Logos 1B (fine-tuned)", x=categories, y=logos_1b,
                          marker_color=COLORS["logos_1b"]))
    fig.add_trace(go.Bar(name="Logos 9B (fine-tuned)", x=categories, y=logos_9b,
                          marker_color=COLORS["logos_9b"]))

    fig.update_layout(
        **LAYOUT_DEFAULTS,
        title=dict(text="<b>Figure 9.</b> Base vs. Fine-tuned — Per Category (300 tests each)",
                   font=dict(size=18)),
        barmode="group",
        yaxis=dict(title="Pass Rate (%)", range=[0, 115], gridcolor="#F3F4F6"),
        xaxis=dict(title="", tickangle=-25),
        legend=dict(orientation="h", yanchor="bottom", y=-0.28, xanchor="center", x=0.5),
        height=600,
    )
    save_fig(fig, "fig9_base_vs_finetuned", width=1100, height=600)


# =========================================================================
# FIGURE 10: Failure Direction Inversion (THE MOST IMPORTANT CHART)
# =========================================================================
def fig10_failure_direction():
    print("Fig 10: Failure Direction Inversion...")

    models = ["Base Gemma 3 1B", "Base Gemma 2 9B", "Logos 1B", "Logos 9B"]
    compliance = [3, 4, 0, 0]
    over_refusal = [38, 30, 31, 2]
    missed_refusal = [15, 22, 0, 0]
    collapse = [1, 0, 1, 0]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        name="Compliance (follows harmful)", x=models, y=compliance,
        marker_color=COLORS["danger"],
        text=compliance, textposition="auto",
    ))
    fig.add_trace(go.Bar(
        name="Missed Refusal (fabricates)", x=models, y=missed_refusal,
        marker_color="#EF4444",
        text=missed_refusal, textposition="auto",
    ))
    fig.add_trace(go.Bar(
        name="Over-Refusal (blocks safe)", x=models, y=over_refusal,
        marker_color=COLORS["warning"],
        text=over_refusal, textposition="auto",
    ))
    fig.add_trace(go.Bar(
        name="Collapse", x=models, y=collapse,
        marker_color="#1F2937",
        text=collapse, textposition="auto",
    ))

    fig.update_layout(
        **LAYOUT_DEFAULTS,
        title=dict(text="<b>Figure 10.</b> Failure Direction Inversion — Fine-tuning Eliminates Dangerous Failures",
                   font=dict(size=17)),
        barmode="stack",
        yaxis=dict(title="Number of Failures", gridcolor="#F3F4F6"),
        xaxis=dict(title=""),
        legend=dict(orientation="h", yanchor="bottom", y=-0.22, xanchor="center", x=0.5),
        height=550,
        annotations=[
            dict(x=0.5, y=1.06, xref="paper", yref="paper",
                 text="Base models fail <b>dangerously</b> (compliance + fabrication) | Fine-tuned models fail <b>safely</b> (over-refusal)",
                 showarrow=False, font=dict(size=12, color="#374151")),
            # Arrow from Base 9B missed_refusal to Logos 9B
            dict(x=2.5, y=20, ax=1, ay=25,
                 xref="x", yref="y", axref="x", ayref="y",
                 showarrow=True, arrowhead=2, arrowsize=1.5,
                 arrowcolor=COLORS["success"], arrowwidth=2,
                 text="<b>→ 0 dangerous</b>", font=dict(color=COLORS["success"], size=12)),
        ],
    )
    save_fig(fig, "fig10_failure_direction", width=950, height=550)


# =========================================================================
# FIGURE 11: Overall Model Comparison (simple summary)
# =========================================================================
def fig11_overall_summary():
    print("Fig 11: Overall Summary...")

    models = ["Base<br>Gemma 3 1B", "Base<br>Gemma 2 9B", "Logos 1B<br>(fine-tuned)", "Logos 9B<br>(fine-tuned)"]
    pass_pct = [81.0, 82.0, 82.33, 97.33]

    colors = [COLORS["base_1b"], COLORS["base_9b"], COLORS["logos_1b"], COLORS["logos_9b"]]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=models, y=pass_pct,
        marker_color=colors,
        text=[f"<b>{v:.1f}%</b>" for v in pass_pct],
        textposition="outside",
        textfont=dict(size=16),
        width=0.55,
    ))

    fig.update_layout(
        **LAYOUT_DEFAULTS,
        title=dict(text="<b>Figure 11.</b> Overall Behavioral Pass Rate (300 stratified tests)",
                   font=dict(size=18)),
        yaxis=dict(title="Pass Rate (%)", range=[0, 110], gridcolor="#F3F4F6"),
        xaxis=dict(title=""),
        showlegend=False,
        height=480,
        shapes=[
            # Horizontal bracket grouping base models
            dict(type="line", x0=-0.3, x1=1.3, y0=-8, y1=-8,
                 xref="x", yref="y", line=dict(color=COLORS["neutral"], width=1)),
            dict(type="line", x0=1.7, x1=3.3, y0=-8, y1=-8,
                 xref="x", yref="y", line=dict(color=COLORS["primary"], width=1)),
        ],
        annotations=[
            dict(x=0.5, y=-12, text="Base (no fine-tuning)", showarrow=False,
                 font=dict(size=11, color=COLORS["neutral"]), xref="x", yref="y"),
            dict(x=2.5, y=-12, text="Logos fine-tuned", showarrow=False,
                 font=dict(size=11, color=COLORS["primary"]), xref="x", yref="y"),
            # Delta annotation
            dict(x=3, y=102, text="<b>+15.3pp</b> vs base",
                 showarrow=True, ay=-20, arrowhead=0,
                 font=dict(size=13, color=COLORS["logos_9b"])),
        ],
    )
    save_fig(fig, "fig11_overall_summary", width=800, height=500)


# =========================================================================
# MAIN
# =========================================================================
if __name__ == "__main__":
    print(f"Generating figures in {OUT_DIR}/\n")

    fig1_identity_vs_instruction()
    fig2_identity_comparison()
    fig3_architecture_success()
    fig4_failure_taxonomy()
    fig5_three_layer()
    fig6_cross_scale()
    fig7_evaluator_bias()
    fig8_failure_types()
    fig9_base_vs_finetuned()
    fig10_failure_direction()
    fig11_overall_summary()

    print(f"\nDone! {11} figures generated.")
    print(f"Open any .html file in a browser for interactive view.")
    print(f"PNG files at 3x resolution for print quality.")
    print(f"SVG files for vector editing.")
