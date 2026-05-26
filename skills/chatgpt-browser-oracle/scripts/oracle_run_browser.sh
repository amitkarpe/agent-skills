#!/usr/bin/env bash
set -euo pipefail

out_dir=""
prompt_file=""
mode="${CHATGPT_ORACLE_MODE:-instant}"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --prompt-file)
      prompt_file="$2"
      shift 2
      ;;
    --out-dir)
      out_dir="$2"
      shift 2
      ;;
    --mode)
      mode="$2"
      shift 2
      ;;
    *)
      echo "unknown argument: $1" >&2
      exit 2
      ;;
  esac
done

if [[ -z "$prompt_file" || -z "$out_dir" ]]; then
  echo "usage: $0 --prompt-file <path> --out-dir <dir> [--mode instant|thinking|pro]" >&2
  exit 2
fi

mkdir -p "$out_dir"

if ! command -v oracle >/dev/null 2>&1; then
  echo "oracle CLI not found in PATH" >&2
  exit 127
fi

model="gpt-5"
case "$mode" in
  instant) model="gpt-5" ;;
  thinking) model="gpt-5-thinking" ;;
  pro) model="gpt-5.5-pro" ;;
esac

oracle \
  --engine browser \
  --remote-chrome 127.0.0.1:9222 \
  --browser-model-strategy ignore \
  --model "$model" \
  "$(cat "$prompt_file")" \
  | tee "$out_dir/oracle-output.txt"
