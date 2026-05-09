#!/usr/bin/env python3
"""
Simple wrapper script to run EleutherAI benchmarks on DeepSeek.

Usage:
    export DEEPSEEK_API_KEY=your_key_here
    python run_benchmark.py --tasks arc_easy,hellaswag,boolq

Or without API key (prompts for it):
    python run_benchmark.py --tasks arc_easy
"""

import os
import sys
import argparse
import subprocess
from pathlib import Path


def get_api_key():
    """Get DeepSeek API key from env or prompt."""
    key = os.environ.get("DEEPSEEK_API_KEY")
    if not key:
        print("DEEPSEEK_API_KEY not found in environment.")
        print("Get your key from: https://platform.deepseek.com/api_keys")
        key = input("Enter DeepSeek API Key: ").strip()
        if not key:
            print("Error: API key required")
            sys.exit(1)
    return key


def run_benchmark(tasks, output_dir, api_key=None, limit=None):
    """Run EleutherAI benchmark on specified tasks."""
    
    if api_key is None:
        api_key = get_api_key()
    
    # Create output directory
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Build command
    cmd = [
        "python", "-m", "lm_eval",
        "--model", "deepseek-chat",
        "--model_args", f"api_key={api_key}",
        "--tasks", tasks,
        "--output_path", str(output_path),
        "--log_samples",
    ]
    
    if limit:
        cmd.extend(["--limit", str(limit)])
    
    print(f"Running benchmark: {tasks}")
    print(f"Output: {output_path}")
    print(f"Command: {' '.join(cmd[:8])}...")  # Hide API key
    print()
    
    # Run
    result = subprocess.run(cmd, capture_output=False, text=True)
    
    if result.returncode != 0:
        print("\n❌ Benchmark failed")
        return False
    
    print(f"\n✅ Benchmark complete!")
    print(f"Results saved to: {output_path}/")
    
    # List result files
    result_files = list(output_path.glob("*.json"))
    if result_files:
        print("\nResult files:")
        for f in result_files:
            print(f"  - {f.name}")
    
    return True


def main():
    parser = argparse.ArgumentParser(
        description="Run EleutherAI benchmarks on DeepSeek"
    )
    parser.add_argument(
        "--tasks",
        default="arc_easy,hellaswag,boolq",
        help="Comma-separated list of tasks (default: arc_easy,hellaswag,boolq)"
    )
    parser.add_argument(
        "--output",
        default="tests/evals/eleutherai/results",
        help="Output directory for results"
    )
    parser.add_argument(
        "--api-key",
        default=None,
        help="DeepSeek API key (or set DEEPSEEK_API_KEY env var)"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit number of examples per task (for quick testing)"
    )
    parser.add_argument(
        "--quick",
        action="store_true",
        help="Quick mode: limit=10 for fast testing"
    )
    
    args = parser.parse_args()
    
    limit = 10 if args.quick else args.limit
    
    # Check if lm-eval is installed
    try:
        import lm_eval
    except ImportError:
        print("❌ lm-eval not installed")
        print("Install with: pip install lm-eval==0.4.5")
        sys.exit(1)
    
    # Run
    success = run_benchmark(
        tasks=args.tasks,
        output_dir=args.output,
        api_key=args.api_key,
        limit=limit
    )
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
