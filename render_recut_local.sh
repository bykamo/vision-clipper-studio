#!/usr/bin/env bash
# Render ulang 4 klip recut Dr. Tirta DI LOKAL (ganti render VPS yang ke-OOM).
# Command identik dengan yang dijalankan di VPS, cuma source & output-nya lokal.
set -u
cd /home/kamo/dev/myapp/vision-clipper || exit 1
export PYTHONUNBUFFERED=1
LOG=temp/recut_render_local.log

echo "=== START $(date '+%F %T %Z') ===" | tee "$LOG"
echo "host: $(hostname) | cores: $(nproc) | source: $(ls -l downloads/tirta.mp4 | awk '{print $5}') bytes" | tee -a "$LOG"

.venv/bin/python -u -m backend.worker \
  --file downloads/tirta.mp4 \
  --clips-json temp/analysis_recut.json \
  --render-indices 4,3,7,1 \
  --out-dir clips/tirta_recut \
  --sub-style tiktok_viral \
  --framing-mode smart_crop 2>&1 | tee -a "$LOG"

rc=${PIPESTATUS[0]}
echo "=== EXIT $rc $(date '+%F %T %Z') ===" | tee -a "$LOG"
ls -la clips/tirta_recut/ | tee -a "$LOG"
exit $rc
