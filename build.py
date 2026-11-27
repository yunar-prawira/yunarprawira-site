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
from email.utils import parsedate_to_datetime
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
        d = None
        try:
            d = parsedate_to_datetime(item.findtext("pubDate") or "").date()
        except (TypeError, ValueError):
            pass
        # "Edisi 26 — judul" -> nomor + judul tanpa prefiks
        m = re.match(r"^Edisi\s+(\d+)\s+—\s+(.*)$", judul)
        nomor, judul_bersih = (m.group(1), m.group(2)) if m else ("", judul)
        out.append({"nomor": nomor, "judul": judul_bersih, "link": link,
                    "ringkas": desc, "tanggal": tanggal(d) if d else ""})
    return out


# Reviewed translations are keyed by the exact source copy. A changed feed item
# gets a bilingual reading link, never an invented or stale translation.
TRANSLATIONS = {
    "98 persen lulus, seperempat cocok": "98 percent pass, a quarter match",
    "Batas yang hanya bekerja kalau ditulis": "Boundaries that only work when written down",
    "Dua puluh gigabyte, dan asal-usul yang tak bisa dilihat": "Twenty gigabytes, and origins that cannot be seen",
    "Test suite Anthropic lulus 98% tapi cuma seperempat input produksi yang cocok. Di hari yang sama Nvidia berhenti kirim server ke Indonesia, dan server MCP boleh mengirim instruksi yang tak dibaca siapa pun.": "Anthropic's test suite passes 98%, but only a quarter of production inputs match. On the same day, Nvidia stops shipping servers to Indonesia, and MCP servers can send instructions that nobody reads.",
    "Enam model Claude mencoba keluar sandbox di 21-32% skenario, tapi cuma 0,6-1,6% yang memakainya secara salah. Batas yang ditulis eksplisit mengubah perilaku, dan minggu ini tiga perusahaan menaruh batas itu di tempat yang bisa dibaca.": "Six Claude models try to escape a sandbox in 21-32% of scenarios, but only 0.6-1.6% misuse it. Explicitly written boundaries change behaviour, and this week three companies put those boundaries where they can be read.",
    "Model 26B berlisensi Apache bisa jalan offline di laptop dan menyalip model 27B di coding agent. Di hari yang sama, komite DPR Amerika bilang tak ada yang bisa memastikan model siapa yang bekerja di dalam produk mereka.": "An Apache-licensed 26B model can run offline on a laptop and outperform a 27B model in a coding agent. On the same day, a US House committee says nobody can be certain whose model is working inside their products.",
}
MONTHS_EN = ["January", "February", "March", "April", "May", "June", "July", "August",
             "September", "October", "November", "December"]


def baris_edisi(ed: dict) -> str:
    title = ed['judul']
    summary = ed['ringkas']
    translated = title in TRANSLATIONS and summary in TRANSLATIONS
    if not translated:
        print(f"peringatan: terjemahan edisi {ed['nomor']} belum tersedia; pakai tautan bilingual", file=sys.stderr)
    title_id = title if translated else 'Baca edisi Kilas'
    title_en = TRANSLATIONS[title] if translated else 'Read this edition of Kilas'
    paragraph = (f'<p class="edisi-ringkas" data-en="{esc(TRANSLATIONS[summary])}">{esc(summary)}</p>'
                 if translated else '')
    date_en = ed['tanggal']
    for month_id, month_en in zip(BULAN, MONTHS_EN):
        date_en = date_en.replace(month_id, month_en)
    return f"""      <li class="edisi">
        <div class="edisi-isi">
          <a class="edisi-judul" href="{esc(ed['link'])}" data-en="{esc(title_en)}">{esc(title_id)}</a>
          {paragraph}
          <span class="meta" data-en="{esc(date_en)}">{esc(ed['tanggal'])}</span>
        </div>
        <span class="edition-number">{esc(ed['nomor'])}</span>
      </li>"""


def blok_kilas(edisi) -> str:
    if not edisi:
        return f'''      <p class="kosong"><a href="{KILAS}/" data-en="Read the latest editions on Kilas">Baca edisi terbaru di Kilas</a></p>'''
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
