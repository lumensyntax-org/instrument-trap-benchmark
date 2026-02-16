# The Instrument Trap: Benchmark Suite

Benchmark code and data for **"The Instrument Trap: Why Identity-as-Authority Breaks AI Safety Systems"**.

**Paper**: [DOI 10.5281/zenodo.18644322](https://doi.org/10.5281/zenodo.18644322)
**Website**: [lumensyntax.com](https://lumensyntax.com)

## What This Repository Contains

This repository provides the complete benchmark infrastructure used to produce the empirical results in the paper. All scripts are reproducible with `seed=42` (15K benchmark) and `seed=2026` (9B sample).

### Structure

```
scripts/          # Benchmark generators, runners, evaluators, analysis
data/             # Aggregated results (summaries, comparisons, failure analysis)
csvs/             # Figure data in CSV format
figures/          # Publication figures (PNG + SVG)
paper/            # LaTeX source + references
```

### Key Scripts

| Script | Purpose |
|--------|---------|
| `massive_benchmark_15k_generator.py` | Generate 15,000 test cases across 8 categories |
| `benchmark_15k_runner.py` | Execute model against benchmark (Phase 1) |
| `benchmark_15k_evaluator.py` | Two-pass evaluation: local + LLM judge (Phase 2) |
| `benchmark_15k_failure_analysis.py` | Full-population failure taxonomy |
| `benchmark_15k_overlap_test.py` | Train/test overlap exclusion analysis |
| `benchmark_9b_runner.py` | 300-case stratified cross-scale validation |
| `benchmark_9b_evaluator.py` | 1B vs 9B comparison evaluation |
| `benchmark_base_runner.py` | Base (un-fine-tuned) model benchmark |
| `identity_comparison.py` | Authority vs Medium vs Naked identity experiment |
| `generate_plotly_figures.py` | Generate all 11 publication figures |

### Key Results

| Metric | Value | 95% CI |
|--------|-------|--------|
| External Fabrication | 0.00% | [0.00%, 0.03%] |
| Dangerous Failure | 1.9% | [1.7%, 2.2%] |
| Epistemological Safety | 97.7% | [97.4%, 97.9%] |
| Identity Collapse | 0.34% | [0.26%, 0.45%] |

## Security

See [SECURITY.md](SECURITY.md) for details on what has been generalized to prevent targeted attacks on deployed systems. Raw model response data is preserved unmodified for scientific integrity.

## 9B Cross-Scale Validation

| Metric | 1B (n=14,950) | 9B (n=5,000) |
|--------|---------------|---------------|
| Behavioral Accuracy | 81.1% | 96.2% |
| Identity Collapse | 0.34% | 0.4% |
| External Fabrication | 0.00% | 0.00% |

**Key finding — Knowledge-Action Gap**: ~90% of 9B failures contain correct epistemological reasoning in internal processing but serve the request anyway. Base-model helpfulness overrides fine-tuned constraints. This is an architectural limitation, not a training failure.

**Key finding — Format-Following Bypass**: Requests framed as "provide the configuration schema for [System].X" trigger code-generation mode, bypassing epistemological reasoning entirely.

## What This Repository Does NOT Contain

- Model weights (Logos 1B, 9B)
- Training data or fine-tuning pipeline
- Epistemic constraint protocol
- Raw JSONL response files (14.8 GB combined)

The paper documents six misuse patterns for epistemological systems. Releasing weights without ecosystem understanding creates specific abuse vectors. Access to models is available by request.

## Requirements

- Python 3.10+
- Ollama (for local model inference)
- `anthropic` package (for Haiku evaluation in Phase 2)
- `plotly`, `kaleido` (for figure generation)

## Reproducing Results

```bash
# 1. Generate dataset
python scripts/massive_benchmark_15k_generator.py

# 2. Run benchmark (requires Logos model in Ollama)
python scripts/benchmark_15k_runner.py --model fine_tuned_1b

# 3. Evaluate
python scripts/benchmark_15k_evaluator.py

# 4. Analyze failures
python scripts/benchmark_15k_failure_analysis.py

# 5. Generate figures
python scripts/generate_plotly_figures.py
```

## Citation

```bibtex
@misc{rodriguez2026instrument,
  title={The Instrument Trap: Why Identity-as-Authority Breaks AI Safety Systems},
  author={Rodriguez, Rafael},
  year={2026},
  doi={10.5281/zenodo.18644322},
  note={Preprint}
}
```

## License

Code: MIT
Paper: CC BY-NC-ND 4.0
Data: CC BY-NC 4.0
