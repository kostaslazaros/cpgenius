#!/bin/sh
# Move files from /input to /output as proc_<filename>

set -eu

IN="${INPUT_DIR:-/input}"
OUT="${OUTPUT_DIR:-/output}"

[ -d "$IN" ] || { echo "Input dir not found: $IN" >&2; exit 1; }
mkdir -p "$OUT"

did_any=0
for f in "$IN"/*; do
  [ -e "$f" ] || break                 # no files at all
  [ -f "$f" ] || continue              # skip dirs/symlinks
  base=$(basename "$f")
  cp -f "$f" "$OUT/proc_$base"
  echo "copied: $f -> $OUT/proc_$base"
  did_any=1
done

[ "$did_any" -eq 1 ] || echo "No files to process in $IN."
