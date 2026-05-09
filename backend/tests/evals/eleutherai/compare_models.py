#!/usr/bin/env python3
"""
Compare DeepSeek performance against other models on standard benchmarks.

Usage:
    # Compare DeepSeek vs GPT-4
    export DEEPSEEK_API_KEY=...
    export OPENAI_API_KEY=...
    python compare_models.py --models deepseek,gpt-4 --tasks arc_easy,hellaswag
"""

import os
import json
import argparse
import subprocess
from pathlib import Path
from typing import Dict, List
import sys


MODEL_CONFIGS = {
    "deepseek": {
        "name": "deepseek-chat",
        "model_args": "api_key={api_key}",
        "env_key": "DEEPSEEK_API_KEY",
    },
    "gpt-4": {
        "name": "openai-chat-completions",
        "model_args": "model=gpt-4,api_key={api_key}",
        "env_key": "OPENAI_API_KEY",
    },
    "gpt-3.5": {
        "name": "openai-chat-completions", 
        "model_args": "model=gpt-3.5-turbo,api_key={api_key}",
        "env_key": "OPENAI_API_KEY",
    },
}


def run_model_benchmark(model_name: str, tasks: str, output_dir: str, limit: int = None):
    """Run benchmark for a single model."""
    
    config = MODEL_CONFIGS.get(model_name)
    if not config:
        print(f"❌ Unknown model: {model_name}")
        print(f"Available: {', '.join(MODEL_CONFIGS.keys())}")
        return None
    
    # Get API key
    api_key = os.environ.get(config["env_key"])
    if not api_key:
        print(f"❌ {config['env_key']} not set")
        return None
    
    # Build paths
    model_output = Path(output_dir) / model_name
    model_output.mkdir(parents=True, exist_ok=True)
    
    model_args = config["model_args"].format(api_key=api_key)
    
    cmd = [
        "python", "-m", "lm_eval",
        "--model", config["name"],
        "--model_args", model_args,
        "--tasks", tasks,
        "--output_path", str(model_output),
    ]
    
    if limit:
        cmd.extend(["--limit", str(limit)])
    
    print(f"\n{'='*60}")
    print(f"Running: {model_name}")
    print(f"Tasks: {tasks}")
    print(f"{'='*60}")
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"❌ Failed: {model_name}")
        print(result.stderr)
        return None
    
    # Find results file
    result_files = list(model_output.glob("results_*.json"))
    if result_files:
        with open(result_files[0]) as f:
            return json.load(f)
    
    return None


def extract_scores(results: Dict) -> Dict[str, float]:
    """Extract task scores from results."""
    scores = {}
    
    for task_name, task_data in results.get("results", {}).items():
        # Get accuracy or primary metric
        if "acc" in task_data:
            scores[task_name] = task_data["acc"] * 100
        elif "acc_norm" in task_data:
            scores[task_name] = task_data["acc_norm"] * 100
        elif "exact_match" in task_data:
            scores[task_name] = task_data["exact_match"] * 100
    
    return scores


def print_comparison(all_results: Dict[str, Dict]):
    """Print comparison table."""
    
    # Extract scores
    model_scores = {}
    all_tasks = set()
    
    for model_name, results in all_results.items():
        if results:
            scores = extract_scores(results)
            model_scores[model_name] = scores
            all_tasks.update(scores.keys())
    
    if not model_scores:
        print("\n❌ No results to compare")
        return
    
    # Print table
    print("\n" + "="*80)
    print("MODEL COMPARISON")
    print("="*80)
    
    # Header
    models = list(model_scores.keys())
    header = f"{'Task':<20}"
    for model in models:
        header += f"{model:<15}"
    print(header)
    print("-"*80)
    
    # Rows
    for task in sorted(all_tasks):
        row = f"{task:<20}"
        for model in models:
            score = model_scores[model].get(task, 0)
            row += f"{score:>6.1f}%{'':<8}"
        print(row)
    
    # Average
    print("-"*80)
    avg_row = f"{'Average':<20}"
    for model in models:
        scores = model_scores[model].values()
        avg = sum(scores) / len(scores) if scores else 0
        avg_row += f"{avg:>6.1f}%{'':<8}"
    print(avg_row)
    
    print("="*80)
    
    # Winner
    if len(models) >= 2:
        avgs = {}
        for model in models:
            scores = list(model_scores[model].values())
            avgs[model] = sum(scores) / len(scores) if scores else 0
        
        winner = max(avgs, key=avgs.get)
        print(f"\n🏆 Best overall: {winner} ({avgs[winner]:.1f}%)")


def main():
    parser = argparse.ArgumentParser(
        description="Compare multiple LLMs on standard benchmarks"
    )
    parser.add_argument(
        "--models",
        default="deepseek",
        help="Comma-separated models (deepseek,gpt-4,gpt-3.5)"
    )
    parser.add_argument(
        "--tasks",
        default="arc_easy,hellaswag,boolq",
        help="Tasks to benchmark"
    )
    parser.add_argument(
        "--output",
        default="tests/evals/eleutherai/comparison_results",
        help="Output directory"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit examples per task (for quick testing)"
    )
    parser.add_argument(
        "--quick",
        action="store_true",
        help="Quick mode: limit=10"
    )
    
    args = parser.parse_args()
    
    limit = 10 if args.quick else args.limit
    models = [m.strip() for m in args.models.split(",")]
    
    # Run benchmarks
    all_results = {}
    for model in models:
        results = run_model_benchmark(
            model_name=model,
            tasks=args.tasks,
            output_dir=args.output,
            limit=limit
        )
        all_results[model] = results
    
    # Compare
    print_comparison(all_results)
    
    # Save comparison
    comparison_file = Path(args.output) / "comparison_summary.json"
    with open(comparison_file, "w") as f:
        json.dump({
            "models": models,
            "tasks": args.tasks,
            "results": {
                model: extract_scores(res) if res else {}
                for model, res in all_results.items()
            }
        }, f, indent=2)
    
    print(f"\n💾 Comparison saved to: {comparison_file}")


if __name__ == "__main__":
    main()
