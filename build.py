#!/usr/bin/env python3
"""Bangun docs/index.html (ID) dan docs/en/index.html (EN) untuk yunarprawira.com.

Aturan isi:
- Tidak ada angka, nama klien, atau klaim yang tidak ada di sumber terverifikasi
  (MASTER_CV.md dan produk yang benar-benar bisa dibuka). Kalau tidak terverifikasi,
  jangan ditulis.
- Edisi Kilas diambil dari feed saat build; kalau feed mati, halaman tetap dibangun.
- Dua halaman statis, bukan satu halaman yang ditukar JS: /en/ punya URL sendiri
  sehingga bisa dibagikan dan diindeks.
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
OUT_ID = ROOT / "docs" / "index.html"
OUT_EN = ROOT / "docs" / "en" / "index.html"

KILAS = "https://kilas.yunarprawira.com"
FEED = KILAS + "/feed.xml"
PORTFOLIO = ("https://valiant-headstand-331.notion.site/"
             "Yunar-s-Portfolio-3bad563c825c804e9167ed2d68f1b0c6")
EMAIL = "mail@yunarprawira.com"

BULAN = ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli", "Agustus",
         "September", "Oktober", "November", "Desember"]
MONTHS_EN = ["January", "February", "March", "April", "May", "June", "July", "August",
             "September", "October", "November", "December"]

# ---------------------------------------------------------------- copy
# Angka di sini berasal dari MASTER_CV.md (single source of truth). Jangan menambah
# klaim baru tanpa memperbarui sumbernya lebih dulu.
COPY = {
    "id": {
        "lang": "id",
        "title": "Yunar Prawira | Project manager implementasi HR technology",
        "desc": "Project manager implementasi HRIS: 15 tahun domain HR, 10 dari 11 implementasi enterprise. Membangun produk AI dan menulis Kilas.",
        "oglocale": "id_ID",
        "sharealt": "Yunar Prawira, project manager implementasi HR technology",
        "canonical": "https://www.yunarprawira.com/",
        "jobtitle": "Senior Project Manager / Delivery Lead",
        "skip": "Langsung ke isi",
        "navlabel": "Navigasi utama",
        "navwork": "Yang saya bangun",
        "navkilas": "Kilas",
        "navcontact": "Kontak",
        "role": "Project manager · implementasi HR technology",
        "lede": "Lima belas tahun di domain HR, tujuh di antaranya memimpin implementasi HRIS enterprise di Asia Tenggara: 51.500 karyawan dan 108 badan hukum, dari discovery sampai go-live.",
        "lede2": "Sekarang saya juga membangun produk AI sendiri, dan menulis apa yang saya pelajari dari keduanya.",
        "btncv": "Unduh CV (PDF)",
        "btntalk": "Bicarakan proyek",
        "prooflabel": "Ringkas",
        "proofhead": "Ringkas",
        "proof": [
            ("15 tahun", "domain HR, termasuk operasi payroll dan kepatuhan PPh21"),
            ("7 tahun", "memimpin implementasi HRIS enterprise di Indonesia dan Vietnam"),
            ("10 dari 11", "implementasi enterprise saya pegang langsung sebagai project manager"),
        ],
        "workhead": "Yang saya bangun",
        "worklead": "Produk dan sistem yang bisa Anda buka sekarang, bukan konsep.",
        "work": [
            {
                "title": "Kalkulator PPh21",
                "what": "Kalkulator pajak penghasilan karyawan Indonesia yang jalan penuh di browser: tarif progresif, PTKP, dan rincian potongan tanpa perlu login.",
                "result": "Dipakai untuk memeriksa perhitungan payroll sebelum periode tutup buku.",
                "links": [("Buka kalkulator", "https://kalkulator-pph21-pi.vercel.app/")],
            },
            {
                "title": "PM Screening Simulator",
                "what": "Ujian seleksi project manager dengan tiga format soal, timer absolut, dan penilaian per topik. Keluar di tengah ujian berarti sesi berakhir, sama seperti asesmen sungguhan.",
                "result": "Data ujian tersimpan lokal, jadi hasil bisa ditinjau ulang tanpa server.",
                "links": [("Buka simulator", "https://pm-screening-simulator.vercel.app/")],
            },
            {
                "title": "Kilas",
                "what": "Brief AI tiga edisi seminggu yang saya tulis dan terbitkan sendiri: model, riset, dan cara AI mengubah pekerjaan.",
                "result": "Setiap angka bertaut ke sumbernya, jadi bisa diperiksa ulang.",
                "links": [("Baca Kilas", KILAS + "/")],
            },
        ],
        "portfoliolabel": "Studi kasus implementasi enterprise ada di Notion, tab baru: ",
        "portfoliocta": "Portfolio (Notion)",
        "kilashead": "Edisi terbaru di Kilas",
        "kilasall": "Semua edisi dan arsip topik",
        "contacthead": "Membicarakan proyek",
        "contactpitch": "Untuk implementasi HRIS, pengelolaan delivery, atau membangun otomasi AI bersama.",
        "contactask": "Kirim satu paragraf soal masalahnya, bukan lampiran tender. Saya balas dengan pertanyaan yang menentukan ruang lingkup.",
        "btnmail": "Kirim email",
        "btnlinkedin": "LinkedIn",
        "mailsubject": "Proyek%20%E2%80%94%20satu%20paragraf",
    },
    "en": {
        "lang": "en",
        "title": "Yunar Prawira | HR technology implementation project manager",
        "desc": "HRIS implementation project manager: 15 years in HR, PM on 10 of 11 enterprise rollouts. I build AI products and write Kilas.",
        "oglocale": "en_GB",
        "sharealt": "Yunar Prawira, HR technology implementation project manager",
        "canonical": "https://www.yunarprawira.com/en/",
        "jobtitle": "Senior Project Manager / Delivery Lead",
        "skip": "Skip to content",
        "navlabel": "Main navigation",
        "navwork": "What I build",
        "navkilas": "Kilas",
        "navcontact": "Contact",
        "role": "Project manager · HR technology implementation",
        "lede": "Fifteen years in HR, seven of them leading enterprise HRIS implementations across Southeast Asia: 51,500 employees and 108 legal entities, from discovery to go-live.",
        "lede2": "I also build my own AI products, and write about what I learn from both.",
        "btncv": "Download CV (PDF)",
        "btntalk": "Discuss a project",
        "prooflabel": "At a glance",
        "proofhead": "At a glance",
        "proof": [
            ("15 years", "in HR, including payroll operations and PPh21 tax compliance"),
            ("7 years", "leading enterprise HRIS implementations in Indonesia and Vietnam"),
            ("10 of 11", "enterprise implementations I ran directly as project manager"),
        ],
        "workhead": "What I build",
        "worklead": "Products and systems you can open right now, not concepts.",
        "work": [
            {
                "title": "PPh21 Calculator",
                "what": "Indonesian employee income tax calculator that runs entirely in the browser: progressive brackets, PTKP allowances, and a full withholding breakdown with no login.",
                "result": "Built to check payroll figures before a period closes.",
                "links": [("Open calculator", "https://kalkulator-pph21-pi.vercel.app/")],
            },
            {
                "title": "PM Screening Simulator",
                "what": "A project manager screening exam with three question formats, an absolute timer, and scoring per topic. Leaving mid-exam ends the session, the way a real assessment does.",
                "result": "Exam data stays on the device, so results can be reviewed without a server.",
                "links": [("Open simulator", "https://pm-screening-simulator.vercel.app/")],
            },
            {
                "title": "Kilas",
                "what": "An AI brief published three times a week, written and shipped by me: models, research, and how AI changes work.",
                "result": "Every figure links to its source, so you can check it.",
                "links": [("Read Kilas", KILAS + "/")],
            },
        ],
        "portfoliolabel": "Enterprise case studies live in Notion, new tab: ",
        "portfoliocta": "Portfolio (Notion)",
        "kilashead": "Latest editions of Kilas",
        "kilasall": "All editions and topic archives",
        "contacthead": "Discuss a project",
        "contactpitch": "For HRIS implementation, delivery management, or building AI automation together.",
        "contactask": "Send one paragraph about the problem, not a tender attachment. I reply with the questions that decide scope.",
        "btnmail": "Send email",
        "btnlinkedin": "LinkedIn",
        "mailsubject": "Project%20%E2%80%94%20one%20paragraph",
    },
}

# Terjemahan Kilas dikunci pada copy sumber persis. Edisi baru tanpa terjemahan
# direview ditampilkan sebagai tautan, bukan terjemahan karangan.
TRANSLATIONS = {
    "98 persen lulus, seperempat cocok": "98 percent pass, a quarter match",
    "Batas yang hanya bekerja kalau ditulis": "Boundaries that only work when written down",
    "Dua puluh gigabyte, dan asal-usul yang tak bisa dilihat": "Twenty gigabytes, and origins that cannot be seen",
    "Test suite Anthropic lulus 98% tapi cuma seperempat input produksi yang cocok. Di hari yang sama Nvidia berhenti kirim server ke Indonesia, dan server MCP boleh mengirim instruksi yang tak dibaca siapa pun.": "Anthropic's test suite passes 98%, but only a quarter of production inputs match. On the same day, Nvidia stops shipping servers to Indonesia, and MCP servers can send instructions that nobody reads.",
    "Enam model Claude mencoba keluar sandbox di 21-32% skenario, tapi cuma 0,6-1,6% yang memakainya secara salah. Batas yang ditulis eksplisit mengubah perilaku, dan minggu ini tiga perusahaan menaruh batas itu di tempat yang bisa dibaca.": "Six Claude models try to escape a sandbox in 21-32% of scenarios, but only 0.6-1.6% misuse it. Explicitly written boundaries change behaviour, and this week three companies put those boundaries where they can be read.",
    "Model 26B berlisensi Apache bisa jalan offline di laptop dan menyalip model 27B di coding agent. Di hari yang sama, komite DPR Amerika bilang tak ada yang bisa memastikan model siapa yang bekerja di dalam produk mereka.": "An Apache-licensed 26B model can run offline on a laptop and outperform a 27B model in a coding agent. On the same day, a US House committee says nobody can be certain whose model is working inside their products.",
}


def esc(s: str) -> str:
    return html.escape(s or "", quote=True)


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
        m = re.match(r"^Edisi\s+(\d+)\s+—\s+(.*)$", judul)
        nomor, judul_bersih = (m.group(1), m.group(2)) if m else ("", judul)
        out.append({"nomor": nomor, "judul": judul_bersih, "link": link,
                    "ringkas": desc,
                    "tanggal": f"{d.day} {BULAN[d.month - 1]} {d.year}" if d else "",
                    "date_en": f"{d.day} {MONTHS_EN[d.month - 1]} {d.year}" if d else ""})
    return out


def baris_edisi(ed: dict, lang: str) -> str:
    title = ed["judul"]
    summary = ed["ringkas"]
    ok = title in TRANSLATIONS and summary in TRANSLATIONS
    if not ok:
        print(f"peringatan: terjemahan edisi {ed['nomor']} belum tersedia; tautan saja",
              file=sys.stderr)
    if lang == "en":
        judul = TRANSLATIONS[title] if ok else "Read this edition of Kilas"
        ringkas = TRANSLATIONS[summary] if ok else ""
        tanggal = ed["date_en"]
        no = f"No. {ed['nomor']}" if ed["nomor"] else ""
        meta = f'<span class="date">{esc(tanggal)}</span> <span class="no">{esc(no)}</span>'
        read = "Read" if ok else ""
    else:
        judul = title if ok else "Baca edisi Kilas"
        ringkas = summary if ok else ""
        tanggal = ed["tanggal"]
        no = f"No. {ed['nomor']}" if ed["nomor"] else ""
        meta = f'<span class="date">{esc(tanggal)}</span> <span class="no">{esc(no)}</span>'
        read = ""
    ringkas_html = (f'\n<p class="edisi-ringkas">{esc(ringkas)}</p>' if ringkas else "")
    return f"""<li class="edisi">
<a class="edisi-judul" href="{esc(ed['link'])}">{esc(judul)}</a>{ringkas_html}
<p class="edisi-meta">{meta}</p>
</li>"""


def blok_kilas(edisi, lang: str) -> str:
    if not edisi:
        text = ("Baca edisi terbaru di Kilas" if lang == "id"
                else "Read the latest editions on Kilas")
        return f'<p class="kosong"><a class="text-link" href="{KILAS}/">{esc(text)}</a></p>'
    return ('<ol class="daftar-edisi">\n'
            + "\n".join(baris_edisi(e, lang) for e in edisi)
            + "\n</ol>")


def blok_proof(copy: dict) -> str:
    return "\n".join(
        f'<li><span class="val">{esc(v)}</span>'
        f'<span class="lbl">{esc(l)}</span></li>'
        for v, l in copy["proof"])


def blok_work(copy: dict) -> str:
    items = []
    for item in copy["work"]:
        links = "".join(
            f'<a class="text-link" href="{esc(href)}">{esc(label)}</a>'
            for label, href in item["links"])
        items.append(f"""<li>
<h3>{esc(item['title'])}</h3>
<p class="what">{esc(item['what'])}</p>
<p class="result">{esc(item['result'])}</p>
<p class="links">{links}</p>
</li>""")
    return "\n".join(items)


def render(lang: str, edisi) -> str:
    copy = COPY[lang]
    out = TEMPLATE.read_text(encoding="utf-8")
    subs = {
        "{{LANG}}": copy["lang"],
        "{{TITLE}}": esc(copy["title"]),
        "{{DESC}}": esc(copy["desc"]),
        "{{CANONICAL}}": copy["canonical"],
        "{{OGLOCALE}}": copy["oglocale"],
        "{{SHAREALT}}": esc(copy["sharealt"]),
        "{{JOBTITLE}}": esc(copy["jobtitle"]),
        "{{SKIP}}": esc(copy["skip"]),
        "{{NAVLABEL}}": esc(copy["navlabel"]),
        "{{NAVWORK}}": esc(copy["navwork"]),
        "{{NAVKILAS}}": esc(copy["navkilas"]),
        "{{NAVCONTACT}}": esc(copy["navcontact"]),
        "{{CURRENTID}}": ' aria-current="true"' if lang == "id" else "",
        "{{CURRENTEN}}": ' aria-current="true"' if lang == "en" else "",
        "{{ROLE}}": esc(copy["role"]),
        "{{LEDE}}": esc(copy["lede"]),
        "{{LEDE2}}": esc(copy["lede2"]),
        "{{BTNCV}}": esc(copy["btncv"]),
        "{{BTNTALK}}": esc(copy["btntalk"]),
        "{{PROOFLABEL}}": esc(copy["prooflabel"]),
        "{{PROOFHEAD}}": esc(copy["proofhead"]),
        "{{PROOF}}": blok_proof(copy),
        "{{WORKHEAD}}": esc(copy["workhead"]),
        "{{WORKLEAD}}": esc(copy["worklead"]),
        "{{WORKITEMS}}": blok_work(copy),
        "{{KILASHEAD}}": esc(copy["kilashead"]),
        "{{EDITIONS}}": blok_kilas(edisi, lang),
        "{{KILASALL}}": esc(copy["kilasall"]),
        "{{CONTACTHEAD}}": esc(copy["contacthead"]),
        "{{CONTACTPITCH}}": esc(copy["contactpitch"]),
        "{{CONTACTASK}}": esc(copy["contactask"]),
        "{{BTNMAIL}}": esc(copy["btnmail"]),
        "{{BTNLINKEDIN}}": esc(copy["btnlinkedin"]),
        "{{MAILSUBJECT}}": copy["mailsubject"],
        "{{TAHUN}}": str(date.today().year),
    }
    for k, v in subs.items():
        out = out.replace(k, v)
    # Stopgap portfolio: tautan Notion diberi label jelas dan buka tab baru.
    ph = f'{esc(copy["portfoliolabel"])}<a class="text-link" href="{esc(PORTFOLIO)}" target="_blank" rel="noopener noreferrer">{esc(copy["portfoliocta"])}</a>'
    out = out.replace("<ul class=\"work\">", f'<p class="lede-2">{ph}</p>\n<ul class="work">')
    sisa = re.findall(r"\{\{[A-Z0-9]+\}\}", out)
    if sisa:
        raise SystemExit(f"gagal: placeholder belum terisi: {sorted(set(sisa))}")
    sig = hashlib.sha256(out.encode("utf-8")).hexdigest()[:12]
    return out.replace("</head>", f"<!-- build {sig} -->\n</head>", 1)


def salin_aset() -> list[str]:
    """Salin assets/ ke docs/assets/ — GitHub Pages menyajikan docs/ sebagai root,
    jadi /assets/... harus ada di dalam docs/."""
    src = ROOT / "assets"
    dst = ROOT / "docs" / "assets"
    if not src.is_dir():
        return []
    copied = []
    for item in sorted(src.rglob("*")):
        if not item.is_file():
            continue
        target = dst / item.relative_to(src)
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.is_file() or target.read_bytes() != item.read_bytes():
            target.write_bytes(item.read_bytes())
            copied.append(str(item.relative_to(src)))
    return copied


def main() -> int:
    edisi = ambil_edisi()
    for lang, path in (("id", OUT_ID), ("en", OUT_EN)):
        html_out = render(lang, edisi)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(html_out, encoding="utf-8")
        print(f"built {path.relative_to(ROOT)} — {len(edisi)} edisi, {len(html_out)} byte")
    aset = salin_aset()
    print(f"aset: {len(aset)} berkas disalin" if aset else "aset: sudah mutakhir")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
