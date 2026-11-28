#!/usr/bin/env bash
# Verifikasi situs: satu perintah untuk semua pemeriksaan yang bisa dijalankan lokal.
# Dipakai sebagai perintah kanonik repo (npm test) dan oleh deploy.sh.
set -euo pipefail
cd "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

fail=0
step() { printf '\n\033[1m%s\033[0m\n' "$1"; }

step "1/5 sintaks JS"
for f in functions/api/*.js assets/*.js; do
  node --check "$f" && echo "  ok  $f"
done

step "2/5 sintaks Python + JSON"
python3 -m py_compile build.py build_cv.py audit/test-build-cv.py
python3 -c "import json,sys
for p in ('docs/_routes.json','package.json'):
    json.load(open(p)); print('  ok  '+p)"

step "3/5 build deterministik"
h1=$(python3 build_cv.py >/dev/null && sha256sum docs/cv/index.html | cut -d' ' -f1)
h2=$(python3 build_cv.py >/dev/null && sha256sum docs/cv/index.html | cut -d' ' -f1)
if [ "$h1" = "$h2" ]; then echo "  ok  dua build identik ($h1)"; else
  echo "  GAGAL: build tidak idempoten ($h1 != $h2)"; fail=1; fi

step "4/5 asersi build + gate"
python3 audit/test-build-cv.py || fail=1

step "5/5 asersi fungsi serverless"
node audit/test-functions.mjs | tail -1 || fail=1

printf '\n'
[ "$fail" -eq 0 ] && echo "LULUS" || echo "GAGAL"
exit "$fail"
