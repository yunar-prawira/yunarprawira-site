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

- `template.html` — satu-satunya berkas desain. Placeholder: `{{EDITIONS}}`, `{{KILAS}}`,
  `{{PORTFOLIO}}`, `{{EMAIL}}`, `{{TAHUN}}`.
- `build.py` — mengambil 3 edisi terbaru dari `kilas.yunarprawira.com/feed.xml` saat build,
  lalu menulis `docs/index.html`. Kalau feed mati, halaman tetap dibangun dengan tautan saja
  (build tidak boleh gagal karena jaringan).
- `check_geometry.py` — cek DOM: sebaris/tidaknya elemen, target sentuh ≥44px, overflow
  horizontal di 1440px dan 390px. Ini yang menangkap kerusakan layout; audit warna tidak.
- Audit desain: `signature-design` (`audit_run.py`) — lulus 97 (visual 94, alur 100, 0 critical).

Arah desain: **editorial** (kertas hangat `#FDFCF9`, serif Bitstream Charter, satu aksen
`#7A2E2E`, garis rambut 1px). Skala font 6 langkah: 11/13/16/20/28/48.

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
