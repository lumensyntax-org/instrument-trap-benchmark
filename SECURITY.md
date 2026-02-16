# Security Notice

## What Has Been Generalized

This repository provides the complete benchmark infrastructure for reproducing the results in "The Instrument Trap." The following categories of information have been generalized to prevent targeted attacks on deployed systems:

1. **Model identifiers**: Specific model names replaced with generic identifiers (`fine_tuned_1b`, `fine_tuned_9b`, etc.)
2. **Component names**: Internal architecture component names in test generators replaced with generic software patterns
3. **Creator references**: Authority impersonation prompts generalized to use `[CREATOR]` placeholders
4. **Identity phrases**: System-specific unlock phrases replaced with `[REDACTED_PHRASE]`
5. **Identity detection strings**: Behavioral detection patterns that reference specific system internals generalized

## What Has NOT Been Modified

- **Raw model responses** in `data/` files are preserved exactly as generated. These contain the model's actual outputs and may reference internal component names because the model was responding to test prompts. Modifying these would falsify the scientific record.
- **Standard security testing techniques** (persona hijack, emotional manipulation, encoding attacks) are retained as they are well-documented in existing literature.
- **Evaluation logic** is fully preserved to enable reproduction.
- **Category names** (BAPTISM_PROTOCOL, KENOTIC_LIMITATION, etc.) are benchmark taxonomy labels, not system internals.

## Responsible Disclosure

If you discover a vulnerability in the evaluated system through this benchmark data, please contact: security@lumensyntax.com

## For Researchers

To reproduce the exact results reported in the paper, you need:
- The fine-tuned models (available on request for verified researchers)
- An Ollama instance configured with the model names referenced in the scripts
- The training data path set via `TRAINING_DATA_PATH` environment variable (for overlap test)
