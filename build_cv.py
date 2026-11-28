#!/usr/bin/env python3
"""Bangun docs/cv/index.html dari cv_source_MASTER_CV.md.

Sumbernya salinan `gdrive:02 - Job Search/Master CV v2/MASTER_CV.md` (single source of
truth). Blok setelah penanda INTERNAL dibuang, jadi halaman hanya berisi CV publik.
Desainnya meminjam token yang sama dengan landing page (editorial, kertas hangat,
satu aksen maroon) supaya /cv tidak terasa seperti situs lain.
"""
from __future__ import annotations

import html
import os
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "cv_source_MASTER_CV.md"
OUT = ROOT / "docs" / "cv" / "index.html"

# Sitekey Turnstile publik. Bukan rahasia: nilainya memang tampil di HTML.
# Ganti lewat env TURNSTILE_SITEKEY saat build, tanpa menyentuh kode.
# Placeholder ini harus diganti dengan sitekey asli setelah Yunar membuat widget;
# sampai itu terjadi, form tetap tampil tapi verifikasi akan gagal (dan mailto
# fallback muncul), jadi tidak ada jalur yang diam-diam terbuka.
TURNSTILE_SITEKEY = os.environ.get("TURNSTILE_SITEKEY", "0x4AAAAAAA_PLACEHOLDER")
PLACEHOLDER_SITEKEY = "0x4AAAAAAA_PLACEHOLDER"

# Penanda blok form di TEMPLATE. Saat sitekey belum asli, seluruh blok ini
# diganti dengan versi mailto-only supaya tidak ada form yang pasti gagal.
GATE_FORM_MARKER = "<!--GATE:FORM-->"
GATE_BEGIN = "<!--GATE:BEGIN-->"
GATE_END = "<!--GATE:END-->"
GATE_MAILTO_ONLY = """<section class="cvgate" aria-labelledby="cvgate-title">
  <h2 id="cvgate-title">Minta CV lengkap</h2>
  <p class="cvgate-note">CV lengkap saya kirim lewat email, tanpa nomor telepon di dalamnya.
  Tulis satu baris saja — siapa Anda dan untuk peran apa.</p>
  <p><a class="cvgate-cta" href="mailto:mail@yunarprawira.com?subject=Permintaan%20CV%20lengkap">Minta CV lengkap lewat email</a></p>
</section>"""


def swap_gate(page: str, use_form: bool) -> str:
    """Ganti seluruh blok antara GATE_BEGIN..GATE_END dengan bentuk yang sesuai.

    Dipisah sebagai fungsi supaya bisa diuji tanpa menjalankan build penuh.
    """
    start = page.find(GATE_BEGIN)
    end = page.find(GATE_END)
    if start == -1 or end == -1 or end < start:
        raise ValueError("penanda GATE:BEGIN/GATE:END tidak lengkap di TEMPLATE")
    if use_form:
        return page
    return page[:start] + GATE_MAILTO_ONLY + page[end + len(GATE_END):]

INTERNAL_MARK = "<!-- INTERNAL:"


def esc(s: str) -> str:
    return html.escape(s or "", quote=True)


def inline(s: str) -> str:
    """**bold** and bare URLs -> HTML."""
    s = esc(s)
    s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"(https?://[^\s<]+)", r'<a href="\1">\1</a>', s)
    return s


def render(md: str) -> str:
    cut = md.find(INTERNAL_MARK)
    if cut != -1:
        md = md[:cut]

    out: list[str] = []
    list_open = False
    first_h1 = True

    def close_list() -> None:
        nonlocal list_open
        if list_open:
            out.append("</ul>")
            list_open = False

    for raw in md.splitlines():
        line = raw.rstrip()
        if not line.strip():
            close_list()
            continue
        if line.startswith("### "):
            close_list()
            out.append(f'<h3>{inline(line[4:])}</h3>')
        elif line.startswith("## "):
            close_list()
            out.append(f'<h2>{inline(line[3:])}</h2>')
        elif line.startswith("# "):
            close_list()
            title = line[2:].strip()
            if first_h1:
                out.append(f'<h1 class="nama">{esc(title.title())}</h1>')
                first_h1 = False
            else:
                out.append(f"<h1>{inline(title)}</h1>")
        elif line.startswith("- "):
            if not list_open:
                out.append("<ul>")
                list_open = True
            out.append(f"<li>{inline(line[2:])}</li>")
        elif re.fullmatch(r"\s{2,}\S.*", line) or line.startswith("   "):
            # lanjutan butir / blok kode sederhana
            if list_open:
                out[-1] = out[-1].removesuffix("</li>") + "<br>" + inline(line.strip()) + "</li>"
            else:
                out.append(f'<p class="meta">{inline(line.strip())}</p>')
        else:
            close_list()
            cls = "subjudul" if line.startswith("**") and line.endswith("**") else "p"
            out.append(f'<p class="{cls}">{inline(line)}</p>')
    close_list()
    return "\n".join(out)


def main() -> None:
    body = render(SRC.read_text(encoding="utf-8"))
    # Sitekey Turnstile bukan rahasia (memang tampil di HTML), tapi harus bisa
    # diganti tanpa mengedit kode: env var menang, lalu nilai cadangan.
    sitekey = os.environ.get("TURNSTILE_SITEKEY", TURNSTILE_SITEKEY)
    page = TEMPLATE.replace("{{BODY}}", body)

    # Form gate hanya dirender kalau sitekey ASLI sudah ada. Dengan placeholder,
    # Turnstile pasti menolak dan pengunjung hanya melihat error — lebih buruk
    # daripada tombol mailto biasa. Ini menjaga janji PRD A3: selama gate B
    # belum siap kredensialnya, jalur yang dipakai adalah mailto.
    if sitekey == PLACEHOLDER_SITEKEY or not sitekey:
        page = swap_gate(page, use_form=False)
    else:
        page = page.replace("{{TURNSTILE_SITEKEY}}", sitekey)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(page, encoding="utf-8")
    print(f"docs/cv/index.html ditulis ({len(page) // 1024} KB, gate={'form' if sitekey != PLACEHOLDER_SITEKEY else 'mailto'})")


TEMPLATE = """<!doctype html>
<html lang="id">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>CV — Yunar Prawira Negara</title>
<meta name="description" content="CV Yunar Prawira Negara — Senior Project Manager / Delivery Lead, HR Tech &amp; Enterprise SaaS. Lima belas tahun, 51.500 karyawan dalam lingkup implementasi.">
<meta name="color-scheme" content="light">
<meta name="robots" content="noindex,nofollow">
<link rel="canonical" href="https://www.yunarprawira.com/cv/">
<meta property="og:title" content="CV — Yunar Prawira Negara">
<meta property="og:type" content="profile">
<meta property="og:url" content="https://www.yunarprawira.com/cv/">
<link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><rect width='100' height='100' fill='%23D70015'/></svg>">
<style>
:root{
  --bg:#FDFCF9; --surface:#F7F4EE; --ink:#16130F; --muted:#6E6659;
  --hairline:#E0D9CB; --accent:#D70015;
  --display:"Bitstream Charter", Charter, "Liberation Serif", Georgia, serif;
  --body:Lato, "Liberation Sans", "DejaVu Sans", Arial, sans-serif;
  --mono:"DejaVu Sans Mono", "Liberation Mono", monospace;
  --s1:4px; --s2:8px; --s3:12px; --s4:16px; --s5:20px; --s6:24px;
  --s8:32px; --s10:40px; --s12:48px; --s16:64px; --s20:80px;
}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font-family:var(--body);
  font-size:16px;line-height:1.6;-webkit-font-smoothing:antialiased}
.wrap{max-width:760px;margin:0 auto;padding:0 var(--s6)}
a{color:inherit;text-decoration:none}
.masthead{border-bottom:1px solid var(--hairline)}
.masthead .wrap{display:flex;align-items:center;gap:var(--s4);min-height:56px}
.masthead .who{font-family:var(--mono);font-size:11px;letter-spacing:.08em;
  text-transform:uppercase;color:var(--muted)}
.masthead nav{margin-left:auto;display:flex;gap:var(--s4);font-family:var(--mono);
  font-size:11px;letter-spacing:.08em;text-transform:uppercase}
.masthead nav a{color:var(--muted);display:inline-flex;align-items:center;min-height:44px;
  word-break:normal;white-space:nowrap}
.masthead nav a:hover{color:var(--ink)}
main{padding:var(--s16) 0 var(--s12)}
h1.nama{font-family:var(--display);font-weight:400;font-size:40px;line-height:1.05;
  letter-spacing:-.02em;margin:0}
h2{font-family:var(--display);font-weight:400;font-size:20px;margin:var(--s10) 0 var(--s3);
  padding-top:var(--s4);border-top:1px solid var(--hairline);letter-spacing:-.005em}
h3{font-family:var(--mono);font-weight:400;font-size:11px;letter-spacing:.08em;
  text-transform:uppercase;color:var(--accent);margin:var(--s6) 0 var(--s2)}
p{margin:var(--s2) 0 0;max-width:62ch}
p.subjudul{font-family:var(--display);font-size:20px;margin-top:var(--s2);color:var(--ink)}
p.meta{font-family:var(--mono);font-size:11px;letter-spacing:.04em;color:var(--muted)}
ul{margin:var(--s2) 0 0;padding-left:var(--s5);max-width:62ch}
li{margin-bottom:var(--s2)}
strong{font-weight:700}
a[href^="http"],a[href^="mailto"]{color:var(--accent);
  text-decoration:underline;text-underline-offset:3px;word-break:break-word}
footer{border-top:1px solid var(--hairline);padding:var(--s6) 0;font-family:var(--mono);
  font-size:11px;letter-spacing:.04em;color:var(--muted);display:flex;gap:var(--s4);
  flex-wrap:wrap}
footer a{min-height:44px;display:inline-flex;align-items:center}
@media (max-width:640px){
  .wrap{padding:0 var(--s5)}
  main{padding:var(--s10) 0}
  h1.nama{font-size:30px}
}
@media print{
  .masthead,footer{display:none}
  main{padding:0}
  body{font-size:11pt}
  h2{page-break-after:avoid}
  .cvgate{display:none}
}
/* Form permintaan CV lengkap */
.cvgate{margin:3rem 0 1rem;padding:1.5rem 1.25rem;border:1px solid #e3e0d8;
  border-radius:10px;background:#fbfaf7}
.cvgate h2{margin:0 0 .4rem;font-size:1.15rem}
.cvgate-note{margin:0 0 1.1rem;font-size:.9rem;color:#5b5b52;max-width:52ch;line-height:1.55}
.cvgate label{display:block;font-size:.82rem;font-weight:600;margin-bottom:.35rem;
  letter-spacing:.02em;text-transform:uppercase;color:#3a3a33}
.cvgate input{width:100%;max-width:26rem;padding:.6rem .7rem;font:inherit;font-size:.95rem;
  border:1px solid #cfc9bc;border-radius:6px;background:#fff;color:#1b2b45}
.cvgate input:focus{outline:2px solid #b5762a;outline-offset:2px;border-color:#b5762a}
.cvgate button{margin-top:1rem;padding:.62rem 1.15rem;font:inherit;font-size:.95rem;
  font-weight:600;color:#fff;background:#b5762a;border:0;border-radius:6px;cursor:pointer;
  min-height:44px}
.cvgate button:hover{background:#9c6323}
.cvgate button:disabled{opacity:.6;cursor:progress}
.cvgate [data-cv-status]{margin:.9rem 0 0;font-size:.9rem}
.cvgate [data-cv-status][data-kind=error]{color:#a12b1f}
.cvgate [data-cv-status][data-kind=info]{color:#5b5b52}
.cvgate [data-cv-mailto]{font-size:.9rem;margin:.6rem 0 0}
.cvgate [data-cv-success] p{margin:0;font-size:.95rem;color:#1b2b45}
</style>
<!-- Turnstile: dimuat async, tidak memblokir render. Kalau gagal dimuat,
     form tetap tampil dan mailto fallback yang dipakai. -->
<script src="https://challenges.cloudflare.com/turnstile/v0/api.js" async defer></script>
<script src="../assets/cv-gate.js" defer></script>
</head>
<body>

<div class="masthead">
  <div class="wrap">
    <span class="who">Yunar Prawira · Jakarta</span>
    <nav>
      <a href="../">Beranda</a>
      <a href="https://linkedin.com/in/yunarprawira">LinkedIn</a>
      <a href="mailto:mail@yunarprawira.com">Email</a>
    </nav>
  </div>
</div>

<main class="wrap">
{{BODY}}

<section class="cvgate" aria-labelledby="cvgate-title">
<!--GATE:BEGIN-->
  <h2 id="cvgate-title">Minta CV lengkap</h2>
  <p class="cvgate-note">CV lengkap dikirim lewat email berisi tautan pribadi — berlaku 7 hari,
  maksimal 3 unduhan. Email dipakai untuk mengirim CV ini saja.</p>

  <form data-cv-gate action="/api/request-cv" method="post" novalidate>
    <label for="cvgate-email">Email</label>
    <input id="cvgate-email" name="email" type="email" required
           autocomplete="email" placeholder="nama@perusahaan.com"
           inputmode="email" spellcheck="false">
    <div class="cf-turnstile" data-sitekey="{{TURNSTILE_SITEKEY}}" data-theme="light"></div>
    <button type="submit">Kirim tautan CV</button>
    <p data-cv-status role="status" aria-live="polite" hidden></p>
    <p data-cv-mailto hidden>
      Atau <a href="mailto:mail@yunarprawira.com?subject=Permintaan%20CV%20lengkap">minta langsung lewat email</a>.
    </p>
  </form>

  <div data-cv-success hidden>
    <p><strong>Terkirim.</strong> Cek inbox (dan folder spam) untuk tautan CV-nya.</p>
  </div>
<!--GATE:END-->
</section>
</main>

<footer class="wrap">
  <span>Yunar Prawira · 2026</span>
  <a href="mailto:mail@yunarprawira.com">mail@yunarprawira.com</a>
  <a href="https://www.linkedin.com/in/yunarprawira">linkedin.com/in/yunarprawira</a>
</footer>

</body>
</html>
"""

if __name__ == "__main__":
    main()
