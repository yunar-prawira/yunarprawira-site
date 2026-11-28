#!/usr/bin/env bash
# Asersi untuk scripts/upload-cv.sh + sanitize_cv_for_gate.py.
# Fokus: gerbang isi HARUS menolak PDF bertelepon. Bug awal: `pdftotext | grep -q`
# dengan `set -o pipefail` -> grep keluar lebih awal, pdftotext kena SIGPIPE (141),
# pipeline dianggap gagal, gerbang lolos, dan PDF bertelepon benar-benar terunggah.
set -uo pipefail
cd "$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

MIG="$HOME/.hermes/cache/scratch/email-mig"
SRC="$MIG/MASTER_CV.md"
DIRTY="$MIG/Yunar Prawira Negara - Senior Project Manager Lead.pdf"
CLEAN="$MIG/CV-gate.pdf"
fails=0
ok()   { echo "PASS  $1"; }
bad()  { echo "FAIL  $1  <- $2"; fails=$((fails+1)); }

# ── gerbang isi harus menolak PDF bertelepon ─────────────────────────────
out=$(./scripts/upload-cv.sh "$DIRTY" 2>&1); rc=$?
[ "$rc" -ne 0 ] && ok "upload-cv.sh menolak PDF bertelepon" \
                || bad "upload-cv.sh menolak PDF bertelepon" "exit=$rc, malah lolos"
printf '%s' "$out" | grep -q "DITOLAK" && ok "  ... dengan pesan DITOLAK" \
                || bad "  ... dengan pesan DITOLAK" "${out:0:80}"
printf '%s' "$out" | grep -q "+62 851" && ok "  ... menyebut baris pelanggar" \
                || bad "  ... menyebut baris pelanggar" "${out:0:80}"
# Pesan sukses tidak boleh muncul saat ditolak
printf '%s' "$out" | grep -q "terunggah" && bad "  ... tidak mengunggah apa pun" "ada 'terunggah'" \
                || ok "  ... tidak mengunggah apa pun"

# ── file bersih harus lolos gerbang (tanpa benar-benar mengunggah) ───────
# Jalankan logika gerbangnya saja: sumber di-santitasi lalu diperiksa.
tmp=$(mktemp -d)
python3 "$MIG/sanitize_cv_for_gate.py" "$SRC" "$tmp/gate.md" >/dev/null 2>&1
rc=$?
[ "$rc" -eq 0 ] && ok "sanitizer jalan" || bad "sanitizer jalan" "exit=$rc"

txt=$(cat "$tmp/gate.md")
printf '%s' "$txt" | grep -qE '\+62|[0-9]{4}-[0-9]{4}-[0-9]{4}|Nagrak|Gunung Putri|Bogor Regency' \
  && bad "hasil sanitasi bebas telepon/alamat" "masih ada" \
  || ok "hasil sanitasi bebas telepon/alamat"
printf '%s' "$txt" | grep -q '^# YUNAR PRAWIRA NEGARA' \
  && ok "judul utuh (regex tidak memakan header)" \
  || bad "judul utuh (regex tidak memakan header)" "judul hilang"
printf '%s' "$txt" | grep -q 'mail@yunarprawira.com' \
  && ok "email tetap ada" || bad "email tetap ada" "email hilang"
[ "$(wc -l < "$tmp/gate.md")" -eq "$(wc -l < "$SRC")" ] \
  && ok "jumlah baris sama dengan master" || bad "jumlah baris sama dengan master" "berubah"

# ── PDF bersih (kalau ada) memang lolos gerbang ──────────────────────────
if [ -f "$CLEAN" ]; then
  t=$(pdftotext "$CLEAN" - 2>/dev/null || true)
  printf '%s' "$t" | grep -qE '\+62|Nagrak|Gunung Putri' \
    && bad "CV-gate.pdf bebas telepon" "masih ada" || ok "CV-gate.pdf bebas telepon"
  printf '%s' "$t" | grep -q 'Jakarta, Indonesia · mail@yunarprawira.com' \
    && ok "CV-gate.pdf kontak kota+email" || bad "CV-gate.pdf kontak kota+email" "baris kontak beda"
else
  echo "SKIP  CV-gate.pdf belum dibangun"
fi

rm -rf "$tmp"
echo
[ "$fails" -eq 0 ] && echo "LULUS" || echo "GAGAL ($fails)"
exit $((fails > 0))
