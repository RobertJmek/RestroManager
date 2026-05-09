"""
EleutherAI LM Evaluation Harness Integration

Provides standard LLM benchmarking for DeepSeek model comparison.

Usage:
    export DEEPSEEK_API_KEY=your_key
    python -m lm_eval \
        --model deepseek-chat \
        --model_args api_key=$DEEPSEEK_API_KEY \
        --tasks arc_easy,hellaswag \
        --output_path tests/evals/eleutherai/results/
"""
