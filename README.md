# yunarprawira.com — peta situs

Tiga properti, satu domain. Semua DNS di Cloudflare (proxied **off**, karena GitHub Pages
butuh DNS langsung untuk menerbitkan sertifikat).

| URL | Isi | Sumber | Deploy |
|---|---|---|---|
| `yunarprawira.com` | redirect 301 → `www` | DNS A/AAAA GitHub Pages | otomatis |
| `www.yunarprawira.com` | landing page pribadi | `~/yunarprawira-site` → repo `yunar-prawira/yunarprawira-site` (branch `master`, folder `/docs`) | `./deploy.sh` |
| `kilas.yunarprawira.com` | Yunar AI Brief (blog AI 3x/minggu) | `~/ai-brief` → repo `yunar-prawira/brief-ai` (branch `main`, folder `/docs`) | `./publish.sh "pesan"` |
| `mail@yunarprawira.com` | email (iCloud Custom Domain) | Cloudflare MX + SPF + DKIM Apple | jangan disentuh manual |

## Landing page (`~/yunarprawira-site`)

- `template.html` — satu-satunya berkas desain. Placeholder `{{...}}` diisi `build.py`.
- `build.py` — mengambil 3 edisi terbaru dari `kilas.yunarprawira.com/feed.xml` saat build,
  lalu menulis `docs/index.html` (ID) + `docs/en/index.html` (EN) dan menyalin `assets/` ke
  `docs/assets/`. Kalau feed mati, halaman tetap dibangun dengan tautan saja.
- `build_cv.py` — menulis `docs/cv/index.html` dari `cv_source_MASTER_CV.md`.
- `assets/` — sumber aset (CSS, font woff2, `share.png` 1200x630, PDF CV). Disajikan dari
  `docs/assets/`, jangan menaut `/assets/` tanpa lewat build.
- `audit/check-home.py` — **satu pemeriksaan untuk halaman home**: lapis statis (placeholder,
  satu h1, lang, hreflang, canonical, og:image, JSON-LD, em dash, link MU, klaim vs MASTER_CV)
  plus lapis geometri dari DOM (tepi kiri ≤4, paragraf pendek tidak pecah, target ≥44px,
  font ≥13px, tanpa overflow) di 1440/1280/390, dua bahasa. Menyajikan `docs/` sendiri di port
  acak, jadi tidak butuh server manual. `python3 audit/check-home.py`, exit 1 = ada temuan.

Arah desain: **editorial** (kertas hangat `#FDFCF9`, serif Bitstream Charter, satu aksen
`#D70015`, Inter untuk body). Skala font 13/15/16/20/24/80.

### Deploy

```bash
cd ~/yunarprawira-site && ./deploy.sh
```

`deploy.sh` = build → commit → push → tunggu Pages `built` → cek HTML tersaji.

## Jejak yang harus ikut berubah kalau URL situs berubah

1. `ai-brief/build.py` → `SITE_URL` + `SITE_HOST` (menulis `docs/CNAME`)
2. `ai-brief/test_build.py` → `SITE`
3. `ai-brief/publish.sh` → `SITE`
4. `ai-brief/scripts/test_ui.py` → `PROD`
5. `ai-brief/BRIEF.md` → baris "Situs"
6. cron `1d40805be03a` (`hermes cron edit --prompt`) → tautan di laporan edisi
7. `yunarprawira-site/template.html` → `{{KILAS}}` sudah otomatis, tapi cek tautan manual

## Catatan

- `www` dan `kilas` **tidak** boleh di-proxy Cloudflare oranye: GitHub Pages akan gagal
  menerbitkan sertifikat dan muncul loop redirect.
- Sertifikat custom domain GitHub Pages butuh beberapa menit sampai ~24 jam setelah DNS benar.
  Cek: `gh api repos/yunar-prawira/yunarprawira-site/pages --jq .https_certificate.state`.
  Status `null` = belum diterbitkan, `approved` = siap.
