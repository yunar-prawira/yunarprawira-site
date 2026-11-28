#!/usr/bin/env bash
# Unggah PDF CV lengkap (sudah disanitasi) ke KV CV_DOWNLOADS supaya endpoint
# /api/download-cv bisa menyajikannya. Tidak butuh R2 maupun kredensial baru.
#
# Pakai: ./scripts/upload-cv.sh /path/ke/CV-gate.pdf
set -euo pipefail
cd "$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

PDF="${1:?pakai: ./scripts/upload-cv.sh <file.pdf>}"
NS="1829c185845f484881752226f24c7461"
ACC="e16aec68d39fadb19f9615e0131d49ba"

[ -f "$PDF" ] || { echo "tidak ada: $PDF" >&2; exit 1; }

# Gerbang isi: PDF yang diunggah tidak boleh memuat data pribadi tingkat rumah.
# Kalau lolos ke sini, gate CV-nya tidak ada artinya.
# PENTING: jangan `pdftotext ... | grep -q`. `grep -q` keluar lebih awal, pdftotext
# kena SIGPIPE (141), dan dengan `set -o pipefail` seluruh pipeline dianggap
# gagal -> gerbang lolos pada PDF yang justru melanggar. Tampung dulu ke variabel.
CV_TEXT=$(pdftotext "$PDF" - 2>/dev/null || true)
if printf '%s' "$CV_TEXT" | grep -qE '\+62|[0-9]{4}-[0-9]{4}-[0-9]{4}|0812|0813|0857|Nagrak|Gunung Putri|Bogor Regency'; then
  echo "DITOLAK: PDF masih memuat telepon/alamat rinci." >&2
  printf '%s' "$CV_TEXT" | grep -nE '\+62|[0-9]{4}-[0-9]{4}-[0-9]{4}|0812|0813|0857|Nagrak|Gunung Putri|Bogor Regency' | head -3 >&2
  echo "Bangun ulang dengan: python3 sanitize_cv_for_gate.py MASTER_CV.md MASTER_CV_gate.md" >&2
  exit 1
fi
echo "gerbang isi: bersih"

TOKEN=$(cat ~/.hermes/secrets/cloudflare_token.txt)
HTTP=$(curl -s -o /tmp/kvput.out -w '%{http_code}' -X PUT \
  "https://api.cloudflare.com/client/v4/accounts/$ACC/storage/kv/namespaces/$NS/values/cv:full" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/pdf" \
  --data-binary "@$PDF")

if [ "$HTTP" != "200" ]; then
  echo "GAGAL unggah (HTTP $HTTP):" >&2
  cat /tmp/kvput.out >&2; exit 1
fi

echo "terunggah: $(basename "$PDF") ($(stat -c%s "$PDF") byte) -> KV key cv:full"
