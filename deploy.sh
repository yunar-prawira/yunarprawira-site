#!/usr/bin/env bash
# Build landing page + push + tunggu GitHub Pages benar-benar menyajikan versi baru.
# Pakai: ./deploy.sh ["pesan commit"]
set -euo pipefail
cd "$(dirname "$0")"

MSG="${1:-update landing page $(date +%F)}"
REPO="yunar-prawira/yunarprawira-site"
SITE="https://www.yunarprawira.com"

python3 build.py
python3 - <<'PY'
# gerbang wajib: tidak boleh push kalau placeholder masih tersisa
import pathlib, re, sys
h = pathlib.Path("docs/index.html").read_text()
sisa = re.findall(r"\{\{[A-Z]+\}\}", h)
if sisa:
    sys.exit(f"gagal: placeholder belum terisi: {sorted(set(sisa))}")
print("gerbang: tidak ada placeholder tersisa")
PY

touch docs/.nojekyll
printf 'www.yunarprawira.com\n' > docs/CNAME

git add -A
if git -c user.name="Yunar Prawira" \
      -c user.email="281810709+yunarganteng@users.noreply.github.com" \
      commit -q -m "$MSG"; then
  git push -q origin master
  echo "pushed: $MSG"
fi
SHA=$(git rev-parse HEAD)

# lapis 1: build GH Pages untuk commit ini selesai
for i in $(seq 1 30); do
  latest=$(gh api "repos/$REPO/pages/builds/latest" --jq '.status+" "+.commit' 2>/dev/null || true)
  [ "${latest%% *}" = "built" ] && [ "${latest##* }" = "$SHA" ] && break
  sleep 5
done
[ "${latest##* }" = "$SHA" ] || { echo "GAGAL: build Pages bukan commit $SHA ($latest)" >&2; exit 1; }

# lapis 2+3: halaman tersaji + penanda konten dari build ini ada di HTML yang disajikan
# penanda = hash isi halaman (bukan SHA git), jadi berubah hanya kalau kontennya berubah
MARK=$(grep -o '<!-- build [0-9a-f]* -->' docs/index.html | head -1)
[ -n "$MARK" ] || { echo "gagal: penanda build tidak ada di docs/index.html" >&2; exit 1; }
for i in $(seq 1 20); do
  body=$(curl -s "$SITE/?cb=$SHA$i")
  if printf '%s' "$body" | grep -qF "$MARK"; then
    code=$(curl -s -o /dev/null -w "%{http_code}" "$SITE/?cb=$SHA$i")
    echo "LIVE ($SHA): $SITE/ (http $code)"
    exit 0
  fi
  sleep 6
done
echo "GAGAL: $SITE belum menyajikan penanda build $SHA" >&2
exit 1
