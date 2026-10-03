#!/bin/bash
# Voice chapters with Kokoro, one chapter at a time with parallel workers, then build the audio files.
#   tools/run_kokoro.sh 1-32 [workers=6] [threads-per-worker=2]
# Safe to interrupt and re-run: finished clips are cached. Progress goes to audio/work/run.log.
set -euo pipefail
cd "$(dirname "$0")/.."
VENV="${SNOWMOON_VENV:-$HOME/.cache/snowmoon-audiobook/venv}"
export VIRTUAL_ENV="$VENV" PATH="$VENV/bin:$PATH" PYTHONWARNINGS=ignore
CHAPTERS="${1:-1-32}"; WORKERS="${2:-6}"; THREADS="${3:-2}"
mkdir -p audio/work; LOG=audio/work/run.log
FIRST="${CHAPTERS%-*}"; LAST="${CHAPTERS#*-}"
echo "$(date '+%F %T') start chapters $CHAPTERS, $WORKERS workers x $THREADS threads" >> "$LOG"
for ch in $(seq "$FIRST" "$LAST"); do
  for k in $(seq 0 $((WORKERS - 1))); do
    python tools/synth_kokoro.py --chapters "$ch" --threads "$THREADS" --shard "$k/$WORKERS" >/dev/null 2>&1 &
  done
  wait
  echo "$(date '+%F %T') $(python tools/synth_kokoro.py --chapters "$ch" --threads "$THREADS" 2>/dev/null | tail -1)" >> "$LOG"
done
python tools/assemble.py --chapters "$CHAPTERS" >> "$LOG" 2>&1
echo "$(date '+%F %T') finished" >> "$LOG"
