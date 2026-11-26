#!/usr/bin/env python3
"""Cek geometri landing page dari DOM (bukan dari kesan screenshot)."""
import json
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent
URL = "file://" + str(ROOT / "docs" / "index.html")


def rects(page, sel):
    return page.eval_on_selector_all(
        sel, "els => els.map(e => { const r = e.getBoundingClientRect();"
             " return {t: Math.round(r.top), l: Math.round(r.left), w: Math.round(r.width),"
             " h: Math.round(r.height), txt: (e.textContent||'').trim().slice(0,28)}; })")


with sync_playwright() as p:
    b = p.chromium.launch(args=["--no-sandbox"])
    fails = []

    # ---------- desktop ----------
    pg = b.new_page(viewport={"width": 1440, "height": 900})
    pg.goto(URL)
    pg.wait_for_timeout(400)

    doors_h = rects(pg, ".door h2")
    print("door h2:", doors_h)
    if len(doors_h) == 2 and abs(doors_h[0]["t"] - doors_h[1]["t"]) > 1:
        fails.append(f"dua heading pintu tidak sebaris: {doors_h[0]['t']} vs {doors_h[1]['t']}")

    doors_no = rects(pg, ".door .no")
    print("door no:", doors_no)
    if len(doors_no) == 2 and abs(doors_no[0]["t"] - doors_no[1]["t"]) > 1:
        fails.append("nomor 01/02 tidak sebaris")

    doors_go = rects(pg, ".door .go")
    print("door go:", doors_go)
    if len(doors_go) == 2 and abs(doors_go[0]["t"] - doors_go[1]["t"]) > 1:
        fails.append("link bawah pintu tidak sebaris")

    # nomor seksi vs judul seksi sebaris?
    heads = pg.eval_on_selector_all(
        ".sec-head", "els => els.map(e => { const n = e.querySelector('.n'), h = e.querySelector('h2');"
        " const a = n.getBoundingClientRect(), c = h.getBoundingClientRect();"
        " return {n: e.querySelector('.n').textContent, dy: Math.round(Math.abs(a.top + a.height/2 - c.top - c.height/2))}; })")
    print("sec-head offset:", heads)
    for h in heads:
        if h["dy"] > 6:
            fails.append(f"nomor seksi {h['n']} tidak sejajar judul (dy {h['dy']}px)")

    # target sentuh < 44
    small = pg.eval_on_selector_all(
        "a, button", "els => els.filter(e => e.offsetParent !== null)"
        ".map(e => { const r = e.getBoundingClientRect(); return {w: Math.round(r.width), h: Math.round(r.height),"
        " txt: (e.textContent||'').trim().slice(0,26)}; })"
        ".filter(o => o.h < 44 || o.w < 44)")
    print("target <44:", small)

    # overflow horizontal
    ov = pg.evaluate("() => ({sw: document.documentElement.scrollWidth, cw: document.documentElement.clientWidth})")
    print("desktop overflow:", ov)
    if ov["sw"] > ov["cw"]:
        fails.append(f"overflow horizontal desktop: {ov}")

    # dua edisi: garis bawah kartu sejajar
    pg.screenshot(path=str(ROOT / "proof-desktop.png"), full_page=True)

    # ---------- mobile ----------
    m = b.new_page(viewport={"width": 390, "height": 844})
    m.goto(URL)
    m.wait_for_timeout(400)
    ov = m.evaluate("() => ({sw: document.documentElement.scrollWidth, cw: document.documentElement.clientWidth})")
    print("mobile overflow:", ov)
    if ov["sw"] > ov["cw"]:
        fails.append(f"overflow horizontal mobile: {ov}")

    nav = rects(m, ".masthead nav a")
    print("mobile nav:", nav)
    if len(nav) >= 2 and len({n["t"] for n in nav}) > 1:
        fails.append("nav mobile wrap ke dua baris")

    # pintu harus menumpuk (bukan berdampingan)
    d = rects(m, ".door")
    print("mobile doors:", d)
    if len(d) == 2 and d[0]["l"] == d[1]["l"] and d[1]["t"] > d[0]["t"]:
        pass  # stacked, benar
    elif len(d) == 2:
        fails.append("pintu tidak menumpuk di mobile")

    # tidak ada elemen melebar keluar viewport
    wide = m.evaluate("""() => Array.from(document.querySelectorAll('main *'))
        .map(e => ({t: (e.textContent||'').trim().slice(0,24), r: Math.round(e.getBoundingClientRect().right)}))
        .filter(o => o.r > 390 + 1)""")
    if wide:
        fails.append(f"elemen melewati 390px: {wide[:4]}")

    m.screenshot(path=str(ROOT / "proof-mobile.png"), full_page=True)
    b.close()

print()
if fails:
    for f in fails:
        print("FAIL", f)
    sys.exit(1)
print("geometri OK")
