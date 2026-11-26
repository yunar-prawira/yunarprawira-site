#!/usr/bin/env python3
"""Bangun index.html untuk yunarprawira.com dari template + 3 edisi terbaru Kilas.

Edisi diambil dari feed Kilas saat build; kalau feed tidak bisa dihubungi,
halaman tetap dibangun dengan tautan saja (jangan pernah bikin build gagal
hanya karena jaringan).
"""
from __future__ import annotations

import html
import hashlib
import re
import sys
import urllib.request
from datetime import date
from pathlib import Path
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parent
TEMPLATE = ROOT / "template.html"
OUT = ROOT / "docs" / "index.html"

KILAS = "https://kilas.yunarprawira.com"
FEED = KILAS + "/feed.xml"
PORTFOLIO = ("https://valiant-headstand-331.notion.site/"
             "Yunar-s-Portfolio-3bad563c825c804e9167ed2d68f1b0c6")
EMAIL = "mail@yunarprawira.com"

BULAN = ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli", "Agustus",
         "September", "Oktober", "November", "Desember"]


def esc(s: str) -> str:
    return html.escape(s or "", quote=True)


def tanggal(d: date) -> str:
    return f"{d.day} {BULAN[d.month - 1]} {d.year}"


def ambil_edisi(limit: int = 3):
    """Ambil edisi terbaru dari feed RSS Kilas. Gagal -> list kosong."""
    try:
        with urllib.request.urlopen(FEED, timeout=15) as r:
            root = ET.fromstring(r.read())
    except Exception as e:  # noqa: BLE001 - build tidak boleh mati karena jaringan
        print(f"peringatan: feed Kilas tidak terbaca ({e.__class__.__name__})", file=sys.stderr)
        return []
    out = []
    for item in root.findall("./channel/item")[:limit]:
        judul = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        desc = (item.findtext("description") or "").strip()
        pub = (item.findtext("pubDate") or "")[:16]
        try:
            d = date.fromisoformat(pub)
        except ValueError:
            d = None
        # "Edisi 26 — judul" -> nomor + judul tanpa prefiks
        m = re.match(r"^Edisi\s+(\d+)\s+—\s+(.*)$", judul)
        nomor, judul_bersih = (m.group(1), m.group(2)) if m else ("", judul)
        out.append({"nomor": nomor, "judul": judul_bersih, "link": link,
                    "ringkas": desc, "tanggal": tanggal(d) if d else ""})
    return out


def baris_edisi(ed: dict) -> str:
    nomor = f'<span class="no">{esc(ed["nomor"])}</span>' if ed["nomor"] else '<span class="no">·</span>'
    return f"""      <li class="edisi">
        {nomor}
        <div class="edisi-isi">
          <a class="edisi-judul" href="{esc(ed['link'])}">{esc(ed['judul'])}</a>
          <p class="edisi-ringkas">{esc(ed['ringkas'])}</p>
        </div>
        <span class="edisi-tgl">{esc(ed['tanggal'])}</span>
      </li>"""


def blok_kilas(edisi) -> str:
    if not edisi:
        return f"""      <p class="kosong">Edisi terbaru bisa dibaca langsung di
        <a href="{KILAS}/">{esc(KILAS.replace('https://', ''))}</a>.</p>"""
    return "      <ol class=\"daftar-edisi\">\n" + "\n".join(baris_edisi(e) for e in edisi) + "\n      </ol>"


def main() -> int:
    edisi = ambil_edisi()
    html_out = TEMPLATE.read_text(encoding="utf-8")
    subs = {
        "{{EDITIONS}}": blok_kilas(edisi),
        "{{KILAS}}": KILAS,
        "{{PORTFOLIO}}": PORTFOLIO,
        "{{EMAIL}}": EMAIL,
        "{{TAHUN}}": str(date.today().year),
    }
    for k, v in subs.items():
        html_out = html_out.replace(k, v)
    sisa = re.findall(r"\{\{[A-Z]+\}\}", html_out)
    if sisa:
        print(f"gagal: placeholder belum terisi: {sorted(set(sisa))}", file=sys.stderr)
        return 1
    OUT.parent.mkdir(parents=True, exist_ok=True)
    sig = hashlib.sha256(html_out.encode("utf-8")).hexdigest()[:12]
    html_out = html_out.replace("</head>", f"<!-- build {sig} -->\n</head>", 1)
    OUT.write_text(html_out, encoding="utf-8")
    print(f"built {OUT.name} — {len(edisi)} edisi Kilas, {len(html_out)} byte")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
