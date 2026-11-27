#!/usr/bin/env python3
"""Satu pemeriksaan untuk halaman home yunarprawira.com: statis + geometri.

Self-contained: menyajikan docs/ di port acak lewat http.server, jadi tidak
butuh server manual maupun `file://` (yang membuat CSS /assets tidak termuat).

Lapis statis  — kendala yang mudah diregresi: placeholder, satu h1, lang,
                hreflang, canonical, og:image, JSON-LD, em dash, link MU,
                aset yang dirujuk, klaim yang harus ada di MASTER_CV.md.
Lapis geometri — diukur dari DOM, bukan dari kesan gambar: tepi kiri, paragraf
                pendek yang pecah baris, target sentuh, font <13px, overflow.

Exit 1 kalau ada temuan. Pakai: python3 audit/check-home.py
"""
from __future__ import annotations

import functools
import json
import os
import re
import sys
import threading
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path

VENV = Path("/home/ubuntu/.hermes/hermes-agent/venv/bin/python")

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    # Playwright hanya ada di venv Hermes. Jangan bandingkan resolve(): beberapa venv
    # (mis. .agent-reach) adalah symlink ke interpreter uv yang sama, jadi resolve()
    # membuat dua lingkungan berbeda terlihat identik. Bandingkan path mentah.
    if VENV.is_file() and sys.executable != str(VENV):
        os.execv(str(VENV), [str(VENV), str(Path(__file__).resolve()), *sys.argv[1:]])
    sys.exit("gagal: playwright tidak tersedia di interpreter ini")

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
CV_SRC = Path.home() / "yunarprawira-site/cv_source_MASTER_CV.md"
CLAIMS = ("51.500", "108", "10 dari 11")
MAX_EDGES, MIN_TARGET, MIN_FONT = 4, 44, 13

fails: list[str] = []


def check(label: str, ok: bool, detail: str = "") -> None:
    print(f"{'PASS' if ok else 'FAIL'}  {label}{'  ' + detail if detail else ''}")
    if not ok:
        fails.append(label)


def serve() -> str:
    handler = functools.partial(SimpleHTTPRequestHandler, directory=str(DOCS))
    srv = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return f"http://127.0.0.1:{srv.server_address[1]}"


def static(base: str) -> None:
    cv_digits = re.sub(r"\D", "", CV_SRC.read_text(encoding="utf-8")) if CV_SRC.is_file() else None
    if cv_digits is None:
        fails.append(f"sumber CV tidak ada: {CV_SRC}")

    for lang, rel in (("id", "index.html"), ("en", "en/index.html")):
        html = (DOCS / rel).read_text(encoding="utf-8")
        t = f"[{lang}]"
        check(f"{t} tanpa placeholder", "{{" not in html)
        check(f"{t} satu h1", html.count("<h1") == 1)
        check(f"{t} html lang", f'<html lang="{lang}">' in html)
        check(f"{t} hreflang id/en/x-default", html.count('rel="alternate" hreflang=') == 3)
        check(f"{t} canonical www", 'rel="canonical" href="https://www.yunarprawira.com' in html)
        check(f"{t} og:image 1200x630",
              'og:image:width" content="1200"' in html and 'og:image:height" content="630"' in html)
        check(f"{t} twitter large card", "summary_large_image" in html)
        ld = re.search(r'<script type="application/ld\+json">(.*?)</script>', html, re.S)
        check(f"{t} JSON-LD Person",
              bool(ld) and json.loads(ld.group(1)).get("@type") == "Person")
        desc = re.search(r'name="description" content="([^"]*)"', html)
        check(f"{t} description <=155", bool(desc) and len(desc.group(1)) <= 155,
              f"{len(desc.group(1))} char" if desc else "")
        check(f"{t} tanpa em dash", "\u2014" not in html)
        check(f"{t} tanpa link MU", "manutd-dashboard" not in html)
        check(f"{t} skip link sebelum main", html.index('class="skip"') < html.index("<main"))
        check(f"{t} mailto ada", "mailto:mail@yunarprawira.com" in html)
        for href in sorted(set(re.findall(r'href="(/(?:en/|cv/|assets/[^"]*))"', html))):
            target = DOCS / href.lstrip("/")
            check(f"{t} {href} resolve",
                  (target / "index.html").is_file() if target.is_dir() else target.is_file())

    if cv_digits is not None:
        page = (DOCS / "index.html").read_text(encoding="utf-8")
        for token in CLAIMS:
            check(f"klaim {token!r} ada di sumber", re.sub(r"\D", "", token) in cv_digits)


PROBE = r"""(() => {
  const SKIP = new Set(['LI','UL','OL','SECTION','MAIN','DIV','HEADER','FOOTER','NAV','BODY','HTML']);
  const leaf = el => !SKIP.has(el.tagName) && !el.querySelector('p,li,h1,h2,h3,a')
                    && el.textContent.trim().length > 2;
  const lines = el => {
    const cs = getComputedStyle(el), lh = parseFloat(cs.lineHeight) || 0;
    if (cs.display === 'flex' || cs.display === 'inline-flex')
      return lh ? Math.max(1, Math.round(el.getBoundingClientRect().height / lh)) : 1;
    const rg = document.createRange(); rg.selectNodeContents(el);
    return new Set([...rg.getClientRects()].map(r => Math.round(r.top))).size;
  };
  const leaves = [...document.querySelectorAll('main h1, main h2, main h3, main p, main .val, main .lbl')]
      .filter(leaf);
  const box = el => el.getBoundingClientRect();
  return {
    edges: [...new Set(leaves.filter(el => getComputedStyle(el).display !== 'inline')
        .map(el => Math.round(box(el).x)))].sort((a, b) => a - b),
    broken: leaves.map(el => ({sel: el.tagName + (el.className ? '.' + String(el.className).split(' ')[0] : ''),
                               chars: el.textContent.trim().length,
                               width: Math.round(box(el).width), lines: lines(el)}))
        .filter(x => x.chars <= 120 && x.lines > 1 && x.width >= 600),
    targets: [...document.querySelectorAll('a, button')].filter(el => !el.classList.contains('skip'))
        .map(el => ({t: el.textContent.trim().slice(0, 18),
                     w: Math.round(box(el).width), h: Math.round(box(el).height)}))
        .filter(x => x.h > 0 && (x.h < 44 || x.w < 44)),
    tiny: leaves.filter(el => parseFloat(getComputedStyle(el).fontSize) < 13)
        .map(el => el.textContent.trim().slice(0, 18)),
    scrollW: document.documentElement.scrollWidth,
    clientW: document.documentElement.clientWidth,
  };
})()"""


def geometry(base: str) -> None:
    with sync_playwright() as p:
        browser = p.chromium.launch()
        for path, lang in (("/", "id"), ("/en/", "en")):
            for w, h in ((1440, 900), (1280, 900), (390, 844)):
                pg = browser.new_page(viewport={"width": w, "height": h})
                pg.goto(base + path)
                pg.wait_for_timeout(250)
                d = pg.evaluate(PROBE)
                t = f"[{lang}@{w}]"
                check(f"{t} tepi kiri <= {MAX_EDGES}", len(d["edges"]) <= MAX_EDGES,
                      f"{d['edges']}")
                check(f"{t} tanpa overflow", d["scrollW"] == d["clientW"],
                      f"{d['scrollW']}/{d['clientW']}")
                check(f"{t} font >= {MIN_FONT}px", not d["tiny"], str(d["tiny"][:3]))
                check(f"{t} target >= {MIN_TARGET}px", not d["targets"], str(d["targets"][:3]))
                if w >= 1280:
                    check(f"{t} tanpa paragraf pendek pecah baris", not d["broken"],
                          str([(x["sel"], x["chars"], x["lines"]) for x in d["broken"]]))
                pg.close()
        browser.close()


if __name__ == "__main__":
    base = serve()
    static(base)
    geometry(base)
    print()
    print("SELESAI:", "semua PASS" if not fails else f"{len(fails)} GAGAL")
    for f in fails:
        print(" -", f)
    sys.exit(1 if fails else 0)
