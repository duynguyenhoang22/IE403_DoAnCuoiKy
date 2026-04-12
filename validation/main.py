#!/usr/bin/env python3
# ─── main.py ─────────────────────────────────────────────────────────────────
"""
Smishing Dataset Auto Validator
================================
Cách dùng:

  # Lần đầu chạy (hoặc sau khi quota reset):
  python main.py --input dataset.csv --output validated.csv

  # Dry-run: chỉ chạy T1+T2, bỏ qua T3 LLM (không tốn quota):
  python main.py --input dataset.csv --output validated.csv --dry-run

  # Tùy chỉnh thư mục lưu checkpoint:
  python main.py --input dataset.csv --output validated.csv --work-dir ./run_01

API Keys (set environment variables trước khi chạy):
  export GOOGLE_API_KEY="..."       # Gemini — Google AI Studio
  export XAI_API_KEY="..."          # Grok   — xai.com
  export DASHSCOPE_API_KEY="..."    # Qwen   — DashScope
  export DEEPSEEK_API_KEY="..."     # DeepSeek — deepseek.com
"""

import argparse
import sys
from pathlib import Path
from pipeline import run_pipeline


def main():
    parser = argparse.ArgumentParser(
        description="Smishing Dataset Auto Validator — 3-Tier Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--input",    required=True,  help="Path to pipe-delimited CSV dataset")
    parser.add_argument("--output",   required=True,  help="Path for validated output CSV")
    parser.add_argument("--work-dir", default="./validator_run",
                        help="Directory for checkpoint & intermediate files (default: ./validator_run)")
    parser.add_argument("--dry-run",  action="store_true",
                        help="Chỉ chạy T1+T2, bỏ qua T3 LLM Judge")
    args = parser.parse_args()

    # Validate input file
    if not Path(args.input).exists():
        print(f"[ERROR] Input file không tồn tại: {args.input}")
        sys.exit(1)

    # Đảm bảo output directory tồn tại
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)

    checkpoint_path = str(Path(args.work_dir) / "checkpoint.json")

    run_pipeline(
        input_path=args.input,
        output_path=args.output,
        checkpoint_path=checkpoint_path,
        work_dir=args.work_dir,
        skip_tier3=args.dry_run,
    )


if __name__ == "__main__":
    main()
