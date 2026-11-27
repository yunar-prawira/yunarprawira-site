#!/usr/bin/env python3
"""Ukur geometri docs/index.html + docs/en/index.html (halaman home).

Prinsip: hanya BLOK teks (punya teks langsung, bukan pembungkus) yang diukur —
<li> dan <section> dilewati karena barisnya sudah diwakili anak-anaknya.
Tepi kiri hanya dihitung dari elemen block-level, bukan inline.

Exit 1 kalau ada temuan.
"""
import sys
from playwright.sync_api import sync_playwright

PROBE = r"""(() => {
  const SKIP = new Set(['LI','UL','OL','SECTION','MAIN','DIV','HEADER','FOOTER','NAV','BODY','HTML']);
  const isLeafText = el => {
    if (SKIP.has(el.tagName)) return false;
    if (el.querySelector('p,li,h1,h2,h3,a')) return false;
    return el.textContent.trim().length > 2;
  };
  const lineCount = el => {
    const cs = getComputedStyle(el);
    const lh = parseFloat(cs.lineHeight) || 0;
    if (cs.display === 'flex' || cs.display === 'inline-flex') {
      return lh ? Math.max(1, Math.round(el.getBoundingClientRect().height / lh)) : 1;
    }
    const rg = document.createRange(); rg.selectNodeContents(el);
    const tops = new Set();
    for (const r of rg.getClientRects()) tops.add(Math.round(r.top));
    return tops.size;
  };
  const leaves = [...document.querySelectorAll('main h1, main h2, main h3, main p, main .val, main .lbl')]
      .filter(isLeafText);

  const lines = leaves.map(el => ({
      sel: el.tagName + (el.className ? '.' + String(el.className).split(' ')[0] : ''),
      text: el.textContent.trim().slice(0, 38),
      width: Math.round(el.getBoundingClientRect().width),
      chars: el.textContent.trim().length,
      lines: lineCount(el),
      x: Math.round(el.getBoundingClientRect().x)}));

  // tepi kiri: hanya elemen block-level dengan teks
  const blockEdges = [...new Set(leaves
      .filter(el => getComputedStyle(el).display !== 'inline')
      .map(el => Math.round(el.getBoundingClientRect().x)))].sort((a,b)=>a-b);

  // target sentuh: hanya yang terlihat & punya area
  const targets = [...document.querySelectorAll('a, button')].map(el => {
      const b = el.getBoundingClientRect();
      return {t: el.textContent.trim().slice(0,20), w: Math.round(b.width), h: Math.round(b.height),
              skip: el.classList.contains('skip')};
    }).filter(x => !x.skip && x.h > 0 && (x.h < 44 || x.w < 44));

  const tiny = leaves.filter(el => parseFloat(getComputedStyle(el).fontSize) < 13)
      .map(el => ({t: el.textContent.trim().slice(0,18), fs: getComputedStyle(el).fontSize}));

  return {blockEdges, lines, targets, tiny,
          scrollW: document.documentElement.scrollWidth,
          clientW: document.documentElement.clientWidth,
          height: document.documentElement.scrollHeight};
})()"""

fails = []
with sync_playwright() as p:
    b = p.chromium.launch()
    for page, tag_lang in (("/", "id"), ("/en/", "en")):
        url = "http://127.0.0.1:8899/" + page
        for w, h in ((1440, 900), (1280, 900), (390, 844)):
            pg = b.new_page(viewport={"width": w, "height": h})
            pg.goto(url); pg.wait_for_timeout(250)
            d = pg.evaluate(PROBE)
            tag = f"{tag_lang}@{w}"
            print(f"== {tag}: tepi={d['blockEdges']} scrollW/clientW={d['scrollW']}/{d['clientW']} tinggi={d['height']}")
            if len(d["blockEdges"]) > 4:
                fails.append(f"{tag}: {len(d['blockEdges'])} tepi kiri {d['blockEdges']}")
            if d["scrollW"] != d["clientW"]:
                fails.append(f"{tag}: overflow {d['scrollW']}/{d['clientW']}")
            if d["tiny"]:
                fails.append(f"{tag}: font <13px {d['tiny'][:3]}")
            if d["targets"]:
                fails.append(f"{tag}: target <44px {d['targets'][:3]}")
            if w >= 1280:
                broken = [x for x in d["lines"]
                          if x["chars"] <= 120 and x["lines"] > 1 and x["width"] >= 600]
                if broken:
                    fails.append(f"{tag}: blok <=120 char pecah baris "
                                 f"{[(x['sel'], x['chars'], x['lines'], x['width']) for x in broken]}")
                print(f"   paragraf panjang (>120 char) pecah: "
                      f"{[(x['sel'], x['chars'], x['lines']) for x in d['lines'] if x['lines']>1]}")
            pg.close()
    b.close()

print()
if fails:
    print("TEMUAN:")
    for f in fails: print(" -", f)
    sys.exit(1)
print("SEMUA CEK LULUS")
