#!/usr/bin/env bash
# Verifikasi situs: satu perintah untuk semua pemeriksaan yang bisa dijalankan lokal.
# Dipakai sebagai perintah kanonik repo (npm test) dan oleh deploy.sh.
#
# Aturan: jangan pernah menaruh pemeriksaan di ujung kiri pipa. `cmd | tail`
# menyembunyikan exit code cmd, dan `cmd | grep -q` membuat cmd kena SIGPIPE
# (141) yang dengan `set -o pipefail` terbaca sebagai "gagal" — atau sebaliknya,
# gerbang lolos pada data yang justru melanggar.
set -uo pipefail
cd "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

fail=0
step() { printf '\n\033[1m%s\033[0m\n' "$1"; }
run()  { "$@" >/tmp/_verify_step.log 2>&1 || { cat /tmp/_verify_step.log; fail=1; }; }

step "1/6 sintaks JS"
for f in functions/api/*.js assets/*.js; do
  if node --check "$f" 2>/tmp/_verify_err; then echo "  ok  $f"; else cat /tmp/_verify_err; fail=1; fi
done

step "2/6 sintaks Python + JSON"
run python3 -m py_compile build.py build_cv.py audit/test-build-cv.py \
  scripts/../audit/test-build-cv.py
python3 - <<'PY'
import json
for p in ("docs/_routes.json", "package.json"):
    json.load(open(p)); print("  ok  " + p)
PY
[ $? -eq 0 ] || fail=1

step "3/6 build deterministik"
h1=$(python3 build_cv.py >/dev/null && sha256sum docs/cv/index.html | cut -d' ' -f1)
h2=$(python3 build_cv.py >/dev/null && sha256sum docs/cv/index.html | cut -d' ' -f1)
if [ "$h1" = "$h2" ]; then echo "  ok  dua build identik (${h1:0:16})"; else
  echo "  GAGAL: build tidak idempoten ($h1 != $h2)"; fail=1; fi

step "4/6 asersi build + gate"
run python3 audit/test-build-cv.py
grep -E "SEMUA LULUS|gagal" /tmp/_verify_step.log || true

step "5/6 asersi fungsi serverless"
run node audit/test-functions.mjs
grep -E "lolos$" /tmp/_verify_step.log || true

step "6/6 gerbang unggah CV + sanitizer"
run ./audit/test-upload-cv.sh
tail -1 /tmp/_verify_step.log

printf '\n'
if [ "$fail" -eq 0 ]; then echo "LULUS"; else echo "GAGAL"; fi
exit "$fail"
