"""Uji ad-hoc build_cv.py: swap_gate() dua cabang + hasil build nyata.

Bukan test suite repo (repo ini tidak punya harness Python untuk build_cv).
Jalankan: python3 audit/test-build-cv.py
"""
import importlib.util
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path.home() / "yunarprawira-site"
fails = []


def check(label, cond, detail=""):
    print(f"{'PASS' if cond else 'FAIL'}  {label}" + ("" if cond else f"  <- {detail}"))
    if not cond:
        fails.append(label)


def load():
    spec = importlib.util.spec_from_file_location("bcv", str(ROOT / "build_cv.py"))
    if spec is None or spec.loader is None:
        raise SystemExit("tidak bisa memuat build_cv.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


m = load()

# ── swap_gate langsung ────────────────────────────────────────────────────
page = "A<!--GATE:BEGIN-->FORM_CONTENT<!--GATE:END-->Z"
out_form = m.swap_gate(page, use_form=True)
check("use_form=True tidak mengubah apa pun", out_form == page, out_form)
out_mail = m.swap_gate(page, use_form=False)
check("use_form=False mengganti blok", "FORM_CONTENT" not in out_mail, out_mail)
check("  ... menyisipkan mailto", "mailto:mail@yunarprawira.com" in out_mail)
check("  ... mempertahankan teks sebelum", out_mail.startswith("A"), out_mail[:20])
check("  ... mempertahankan teks sesudah", out_mail.endswith("Z"), out_mail[-20:])
check("  ... tidak menyisakan penanda", "GATE:BEGIN" not in out_mail and "GATE:END" not in out_mail)

# penanda hilang -> harus melempar, bukan diam-diam menghasilkan halaman rusak
try:
    m.swap_gate("tanpa penanda", use_form=False)
    check("penanda hilang melempar ValueError", False, "tidak melempar")
except ValueError:
    check("penanda hilang melempar ValueError", True)

# hanya BEGIN, tanpa END
try:
    m.swap_gate("X<!--GATE:BEGIN-->Y", use_form=False)
    check("END hilang melempar ValueError", False, "tidak melempar")
except ValueError:
    check("END hilang melempar ValueError", True)

# ── build nyata, dua mode ─────────────────────────────────────────────────
OUT = ROOT / "docs" / "cv" / "index.html"

def build(sitekey=None):
    env = dict(os.environ)
    env.pop("TURNSTILE_SITEKEY", None)
    if sitekey:
        env["TURNSTILE_SITEKEY"] = sitekey
    r = subprocess.run([sys.executable, str(ROOT / "build_cv.py")], env=env,
                       capture_output=True, text=True)
    return r.returncode, r.stdout + r.stderr, OUT.read_text(encoding="utf-8")

rc, log, html = build(None)
check("build tanpa sitekey sukses", rc == 0, log[-200:])
check("  mode mailto dilaporkan", "gate=mailto" in log, log[-120:])
check("  tidak ada form di HTML", 'data-cv-gate' not in html)
check("  tidak ada turnstile di HTML", 'cf-turnstile' not in html)
check("  ada CTA mailto", "cvgate-cta" in html)
check("  tidak ada placeholder bocor", "PLACEHOLDER" not in html)
check("  tidak ada {{...}} tersisa", "{{" not in html)
check("  tetap noindex", 'content="noindex,nofollow"' in html)
check("  data pribadi tetap bersih",
      not any(k in html for k in ("+62 851", "yunarpn@gmail.com", "Nagrak", "Gunung Putri")))
# Regresi nyata: swap_gate pernah menyisipkan <section> DI DALAM <section>,
# menghasilkan landmark bersarang (axe landmark-unique). Jumlah pembungkus
# gate harus tetap satu, bukan dua.
check("  gate section tidak bersarang", html.count('class="cvgate"') == 1,
      f'ada {html.count(chr(34) + "cvgate" + chr(34))} section cvgate')
check("  masthead berupa landmark <header>", '<header class="masthead">' in html)
check("  nav punya aria-label", '<nav aria-label="Navigasi utama">' in html)
check("  print tetap sembunyikan masthead", ".masthead,footer{display:none}" in html)

rc, log, html = build("0x4AAAAAAA_REALKEY123")
check("build dengan sitekey sukses", rc == 0, log[-200:])
check("  mode form dilaporkan", "gate=form" in log, log[-120:])
check("  form ada", 'data-cv-gate' in html)
check("  turnstile ada", 'cf-turnstile' in html)
check("  sitekey tersubstitusi", 'data-sitekey="0x4AAAAAAA_REALKEY123"' in html, "")
check("  tanpa CTA mailto-only", "cvgate-cta" not in html)
check("  tidak ada {{...}} tersisa", "{{" not in html)

# kembali ke placeholder supaya repo tidak tertinggal dalam kondisi form
build(None)
check("repo dikembalikan ke mode mailto", "gate=mailto" in build(None)[1])

print(f"\n{len(fails)} gagal" if fails else "\nSEMUA LULUS")
sys.exit(1 if fails else 0)
