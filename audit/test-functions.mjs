/**
 * Uji ad-hoc functions/api/*.js — bukan test suite repo (repo ini tidak punya
 * harness untuk Cloudflare Functions). Dijalankan: node audit/test-functions.mjs
 *
 * Yang diuji: token HMAC (sign/verify/tamper/expired), validasi email,
 * stampFooter pada PDF NYATA, dan logika rate-limit / hitungan unduhan.
 */
import { readFileSync, writeFileSync, existsSync } from "node:fs";
import { execFileSync } from "node:child_process";

// Functions ditulis sebagai ES module Cloudflare; di Node kita impor apa adanya.
const reqMod = await import("../functions/api/request-cv.js");
const dlMod = await import("../functions/api/download-cv.js");

let fails = 0;
const results = [];
function check(label, cond, detail = "") {
  results.push([cond, label, detail]);
  if (!cond) fails++;
}

const SECRET = "x".repeat(48);

/* ── token: round-trip, tamper, expiry ───────────────────────────────────── */
const payload = { email: "uji@example.com", exp: Math.floor(Date.now() / 1000) + 3600, jti: "abc" };
const token = await reqMod.signToken(payload, SECRET);
check("token bertitik dua bagian", token.split(".").length === 2, token.slice(0, 40));

const back = await reqMod.verifyToken(token, SECRET);
check("verify mengembalikan payload", !!back && back.email === "uji@example.com", JSON.stringify(back));
check("jti ikut", back?.jti === "abc");
check("exp ikut", typeof back?.exp === "number");

check("secret salah -> null", (await reqMod.verifyToken(token, "y".repeat(48))) === null);
check("token kosong -> null", (await reqMod.verifyToken("", SECRET)) === null);
check("token tanpa titik -> null", (await reqMod.verifyToken("abc", SECRET)) === null);
check("token sampah -> null", (await reqMod.verifyToken("aa.bb", SECRET)) === null);

// Payload diubah tapi signature lama -> harus ditolak
const [, sig] = token.split(".");
const forgedBody = Buffer.from(JSON.stringify({ ...payload, email: "penyerang@evil.com" }))
  .toString("base64").replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
check("payload dipalsukan ditolak", (await reqMod.verifyToken(`${forgedBody}.${sig}`, SECRET)) === null);

// Expired
const expired = await reqMod.signToken({ ...payload, exp: Math.floor(Date.now() / 1000) - 10 }, SECRET);
check("token kedaluwarsa ditolak", (await reqMod.verifyToken(expired, SECRET)) === null);

/* ── validasi email ─────────────────────────────────────────────────────── */
const v = reqMod.validateEmail;
check("email normal lolos", v("a@b.co") === null);
check("email panjang >254 ditolak", v("a".repeat(250) + "@b.co") !== null);
check("tanpa @ ditolak", v("ab.co") !== null);
check("tanpa TLD ditolak", v("a@b") !== null);
check("spasi ditolak", v("a b@c.co") !== null);
check("non-string ditolak", v(null) !== null && v(123) !== null);
check("mailinator ditolak", v("x@mailinator.com") !== null);
check("yopmail ditolak", v("x@yopmail.com") !== null);
check("gmail sah lolos", v("orang@gmail.com") === null);

/* ── konstanta sesuai PRD ───────────────────────────────────────────────── */
const K = reqMod._internals;
check("TTL 7 hari", K.TOKEN_TTL_SECONDS === 7 * 24 * 3600, String(K.TOKEN_TTL_SECONDS));
check("maks 3 unduhan", K.MAX_DOWNLOADS === 3, String(K.MAX_DOWNLOADS));
check("1 per email per hari", K.PER_EMAIL_PER_DAY === 1);

/* ── stampFooter pada PDF NYATA ─────────────────────────────────────────── */
const candidates = [
  "/home/ubuntu/yunarprawira-site/assets/Yunar-Prawira-CV.pdf",
  "/home/ubuntu/.hermes/cache/scratch/email-mig/Yunar Prawira Negara - Senior Project Manager Lead.pdf",
];
const pdfPath = candidates.find((p) => existsSync(p));
if (!pdfPath) {
  check("PDF nyata tersedia untuk uji", false, "tidak ketemu di kandidat");
} else {
  const bytes = new Uint8Array(readFileSync(pdfPath));
  check("PDF nyata terbaca", bytes.length > 1000, `${bytes.length} bytes`);
  let stamped = null, err = null;
  try {
    stamped = await dlMod.stampFooter(bytes, "uji@example.com", {});
  } catch (e) {
    err = e.message;
  }
  check("stampFooter berhasil pada PDF nyata", stamped !== null, err || "");
  if (stamped) {
    const text = new TextDecoder("latin1").decode(stamped);
    check("header %PDF utuh", text.startsWith("%PDF"));
    check("trailer EOF utuh", text.trimEnd().endsWith("%%EOF"));
    check("ukuran bertambah wajar", stamped.length > bytes.length);
    check("ukuran tidak menggelembung >2x", stamped.length < bytes.length * 2,
      `${bytes.length} -> ${stamped.length}`);
    const countPages = (s) => (s.match(/\/Type\s*\/Page[^s]/g) || []).length;
    check("jumlah halaman tidak berubah",
      countPages(text) === countPages(new TextDecoder("latin1").decode(bytes)),
      `${countPages(new TextDecoder("latin1").decode(bytes))} -> ${countPages(text)}`);

    // JANGAN cek "string ada di bytes": pdf-lib menulis teks sebagai hex di dalam
    // stream terkompresi, jadi pencarian ASCII selalu gagal walau footernya ada —
    // dan versi pertama tes ini justru sebaliknya: bytes cocok, render kosong.
    // Satu-satunya bukti sah adalah mengekstrak teks dari PDF hasil.
    const tmp = "/tmp/_stamp_verify.pdf";
    writeFileSync(tmp, Buffer.from(stamped));
    let extracted = "";
    try {
      extracted = execFileSync("pdftotext", [tmp, "-"], { encoding: "utf8" });
    } catch (e) {
      extracted = "";
    }
    check("footer TERLIHAT saat PDF dirender (pdftotext)",
      extracted.includes("uji@example.com"), "footer tidak muncul di teks hasil render");
    check("label 'Untuk:' TERLIHAT", extracted.includes("Untuk:"));

    // Footer harus ada di SETIAP halaman, bukan hanya halaman pertama.
    const pagesInRender = extracted.split("\f").filter((p) => p.includes("uji@example.com")).length;
    const totalPages = countPages(new TextDecoder("latin1").decode(bytes));
    check("footer ada di semua halaman", pagesInRender === totalPages,
      `${pagesInRender} dari ${totalPages} halaman`);
  }
}

/* ── rate limit & hitungan unduhan (env KV palsu) ───────────────────────── */
function fakeKV(initial = {}) {
  const store = new Map(Object.entries(initial));
  return {
    _store: store,
    async get(k) { return store.has(k) ? store.get(k) : null; },
    async put(k, v) { store.set(k, v); },
  };
}

const env = {
  CV_DOWNLOADS: fakeKV(),
  TURNSTILE_SECRET: "ts",
  CV_TOKEN_SECRET: SECRET,
  RESEND_API_KEY: "re_test",
  FROM_ADDRESS: "Yunar <mail@yunarprawira.com>",
};

// Panggil onRequestPost dengan Turnstile dipaksa gagal (fetch dipalsukan).
const realFetch = globalThis.fetch;
globalThis.fetch = async (url) => {
  if (String(url).includes("siteverify")) return new Response(JSON.stringify({ success: false }));
  return new Response("{}", { status: 200 });
};
let res = await reqMod.onRequestPost({
  request: new Request("https://x/api/request-cv", {
    method: "POST", body: JSON.stringify({ email: "a@b.co", turnstileToken: "t" }),
  }),
  env,
});
check("Turnstile gagal -> 403", res.status === 403, String(res.status));

// Turnstile lolos
globalThis.fetch = async (url) => {
  if (String(url).includes("siteverify")) return new Response(JSON.stringify({ success: true }));
  if (String(url).includes("resend.com")) return new Response(JSON.stringify({ id: "e1" }));
  if (String(url).includes("telegram")) return new Response(JSON.stringify({ ok: true }));
  return new Response("{}");
};
res = await reqMod.onRequestPost({
  request: new Request("https://x/api/request-cv", {
    method: "POST", body: JSON.stringify({ email: "a@b.co", turnstileToken: "t" }),
  }),
  env,
});
check("permintaan sah -> 200", res.status === 200, String(res.status));
const body1 = await res.json();
check("balasan ok:true", body1.ok === true, JSON.stringify(body1));

// Permintaan kedua untuk email sama di hari yang sama -> 429
res = await reqMod.onRequestPost({
  request: new Request("https://x/api/request-cv", {
    method: "POST", body: JSON.stringify({ email: "a@b.co", turnstileToken: "t" }),
  }),
  env,
});
check("email sama kedua kali -> 429", res.status === 429, String(res.status));

// Email berbeda -> tetap boleh
res = await reqMod.onRequestPost({
  request: new Request("https://x/api/request-cv", {
    method: "POST", body: JSON.stringify({ email: "c@d.co", turnstileToken: "t" }),
  }),
  env,
});
check("email lain -> 200", res.status === 200, String(res.status));

// Email tidak valid -> 400
res = await reqMod.onRequestPost({
  request: new Request("https://x/api/request-cv", {
    method: "POST", body: JSON.stringify({ email: "bukan-email", turnstileToken: "t" }),
  }),
  env,
});
check("email tidak valid -> 400", res.status === 400, String(res.status));

globalThis.fetch = realFetch;

/* ── download: hitungan 3 lalu ditolak ──────────────────────────────────── */
// Pakai PDF NYATA: stampFooter memakai pdf-lib yang butuh struktur PDF valid.
// PDF mainan (string "%PDF-1.4 ...") membuat pdf-lib gagal di catalog.Pages().
if (!pdfPath) {
  check("PDF nyata untuk uji unduhan", false, "tidak ada PDF");
} else {
  const dlEnv = {
    CV_DOWNLOADS: fakeKV(),
    CV_TOKEN_SECRET: SECRET,
    CV_PDF_B64: readFileSync(pdfPath).toString("base64"),
  };
  const dlToken = await reqMod.signToken(
    { email: "uji@example.com", exp: Math.floor(Date.now() / 1000) + 600, jti: "dl1" }, SECRET);

  let okCount = 0, lastStatus = 0, firstBody = null;
  for (let i = 0; i < 4; i++) {
    const r = await dlMod.onRequestGet({
      request: new Request(`https://x/api/download-cv?t=${encodeURIComponent(dlToken)}`),
      env: dlEnv,
    });
    lastStatus = r.status;
    if (r.status === 200) {
      okCount++;
      if (i === 0) {
        const buf = Buffer.from(await r.arrayBuffer());
        firstBody = buf;
        check("unduhan 200 mengirim PDF", buf.subarray(0, 5).toString() === "%PDF-");
        check("unduhan Content-Type PDF", r.headers.get("Content-Type") === "application/pdf");
        check("unduhan noindex", (r.headers.get("X-Robots-Tag") || "").includes("noindex"));
        check("unduhan attachment", (r.headers.get("Content-Disposition") || "").includes("attachment"));
        check("unduhan tidak di-cache", (r.headers.get("Cache-Control") || "").includes("no-store"));
        // End-to-end: PDF yang benar-benar dikirim Worker harus memuat footer.
        writeFileSync("/tmp/_dl_e2e.pdf", buf);
        let dlText = "";
        try {
          dlText = execFileSync("pdftotext", ["/tmp/_dl_e2e.pdf", "-"], { encoding: "utf8" });
        } catch { dlText = ""; }
        check("PDF yang DIKIRIM memuat footer saat dirender",
          dlText.includes("uji@example.com"), "footer tidak terlihat di PDF hasil unduhan");
      }
    }
  }
  check("3 unduhan pertama 200", okCount === 3, String(okCount));
  check("unduhan ke-4 ditolak 429", lastStatus === 429, String(lastStatus));

  const bad = await dlMod.onRequestGet({
    request: new Request("https://x/api/download-cv?t=salah.salah"), env: dlEnv,
  });
  check("token cacat -> 403 (tidak crash)", bad.status === 403, String(bad.status));

  const malformed = await dlMod.onRequestGet({
    request: new Request("https://x/api/download-cv?t=!!!not-base64!!!"), env: dlEnv,
  });
  check("token non-base64 -> 403 (tidak crash)", malformed.status === 403, String(malformed.status));

  const none = await dlMod.onRequestGet({
    request: new Request("https://x/api/download-cv"), env: dlEnv,
  });
  check("tanpa token -> 400", none.status === 400, String(none.status));

  const expiredToken = await reqMod.signToken(
    { email: "a@b.co", exp: Math.floor(Date.now() / 1000) - 5, jti: "exp" }, SECRET);
  const expiredRes = await dlMod.onRequestGet({
    request: new Request(`https://x/api/download-cv?t=${encodeURIComponent(expiredToken)}`), env: dlEnv,
  });
  check("token kedaluwarsa -> 403", expiredRes.status === 403, String(expiredRes.status));
}

/* ── laporan ────────────────────────────────────────────────────────────── */
const icons = { true: "PASS", false: "FAIL" };
for (const [ok, label, detail] of results) {
  console.log(`${icons[ok]}  ${label}${ok ? "" : "  <- " + detail}`);
}
console.log(`\n${results.length - fails}/${results.length} lolos`);
process.exit(fails ? 1 : 0);
