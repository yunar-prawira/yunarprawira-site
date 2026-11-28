#!/usr/bin/env python3
"""Bangun docs/cv/index.html dari cv_source_MASTER_CV.md.

Sumbernya salinan `gdrive:02 - Job Search/Master CV v2/MASTER_CV.md` (single source of
truth). Blok setelah penanda INTERNAL dibuang, jadi halaman hanya berisi CV publik.
Desainnya meminjam token yang sama dengan landing page (editorial, kertas hangat,
satu aksen maroon) supaya /cv tidak terasa seperti situs lain.
"""
from __future__ import annotations

import html
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "cv_source_MASTER_CV.md"
OUT = ROOT / "docs" / "cv" / "index.html"

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
    page = TEMPLATE.replace("{{BODY}}", body)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(page, encoding="utf-8")
    print(f"docs/cv/index.html ditulis ({len(page) // 1024} KB)")


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
}
</style>
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
