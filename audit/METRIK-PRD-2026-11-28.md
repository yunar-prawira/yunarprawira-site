# Fase B — Bukti metrik PRD (2026-11-28)

Dijalankan terhadap **situs produksi live**, bukan build lokal.

## Lighthouse mobile (standar PRD: ≥95 semua kategori)

| Halaman | Performance | Accessibility | Best Practices | SEO |
|---|---|---|---|---|
| `/` | 100 | 100 | 100 | 100 |
| `/en/` | 100 | 100 | 100 | 100 |
| `/cv/` | 100 | 100 | 100 | **66** |

`/cv/` SEO 66 **bukan cacat**: satu-satunya audit yang gagal adalah
`is-crawlable` — "Page is blocked from indexing". Itu persis yang PRD minta
(meta `noindex,nofollow`). Skor 100 di halaman itu akan berarti noindex-nya
bocor.

Metrik inti `/` mobile: FCP 1.0 s · LCP 1.0 s · TBT 0 ms · CLS 0 · SI 1.4 s.
Desktop: FCP 0.5 s · LCP 0.5 s · TBT 0 ms · CLS 0.

Perintah:
```
CHROME_PATH=/usr/bin/google-chrome npx lighthouse@13 <url> \
  --only-categories=performance,accessibility,best-practices,seo \
  --output=json --output-path=...
```

## axe-core (standar PRD: 0 pelanggaran serious/critical)

axe 4.10.2, tag `wcag2a/wcag2aa/wcag21a/wcag21aa/best-practice`:

| Halaman | Violations | Passes |
|---|---|---|
| `/` | **0** | 35 |
| `/en/` | **0** | 35 |
| `/cv/` (sebelum) | 2 moderate | 27 |
| `/cv/` (sesudah) | **0** | 29 |

Dua pelanggaran itu moderate, bukan serious/critical — PRD sudah lolos tanpa
perbaikan. Tetap diperbaiki karena keduanya cacat struktur nyata:

1. **`landmark-unique`** — `<section class="cvgate">` bersarang dua kali.
   Penyebabnya `swap_gate()` menyisipkan `GATE_MAILTO_ONLY` yang membawa
   `<section>` sendiri padahal pembungkusnya sudah ada di template.
2. **`region`** — `.who` dan `<nav>` berada di luar landmark. Masthead
   `<div>` dinaikkan jadi `<header>`, nav diberi `aria-label`.

## Perangkap yang tertangkap saat mengukur

**axe memberi hasil palsu pada cache.** Setelah deploy perbaikan, axe masih
melaporkan 2 pelanggaran yang sama — `document.querySelectorAll` menunjukkan
`section.cvgate == 2`, `header == 0`, yaitu HTML versi lama. `curl` pada saat
yang sama sudah menerima HTML baru. Bypass cache (`?v=<sha>`) → 0 pelanggaran.

Pelajaran: **audit a11y wajib bypass cache**, kalau tidak hasilnya mengukur
deploy sebelumnya dan memperbaiki bug yang sudah hilang.

## Yang tidak bisa diukur di sini

| Metrik PRD | Blocker |
|---|---|
| Notifikasi permintaan CV <1 menit | butuh Resend key + sitekey Turnstile |
| Klik CTA tercatat | butuh analytics (belum dipilih) |
| Data pribadi 0 temuan | **terukur**: 0 di HTML & PDF publik (Fase A) |
