/**
 * GET /api/download-cv?t=<token>
 *
 * Menyajikan PDF CV lengkap dengan footer "Untuk: <email> | <tanggal>".
 * Token kedaluwarsa 7 hari, maksimal 3 unduhan (unduhan ke-4 ditolak).
 *
 * PDF sumber diambil dari env.CV_PDF (binding R2 / KV base64) ATAU dari aset
 * statis yang TIDAK dapat diakses langsung (lihat _routes.json: /assets-private/*
 * dikecualikan dari penyajian statis). Jangan pernah menaruh PDF lengkap di
 * direktori publik tanpa footer — itu membatalkan gunanya gate.
 */

const MAX_DOWNLOADS = 3;

export async function onRequestGet({ request, env }) {
  const url = new URL(request.url);
  const token = url.searchParams.get("t");
  if (!token) return html(errorPage("Tautan tidak lengkap."), 400);

  const payload = await verifyToken(token, env.CV_TOKEN_SECRET);
  if (!payload) {
    return html(errorPage("Tautan sudah kedaluwarsa atau tidak valid. Minta ulang lewat situs."), 403);
  }

  const countKey = `dl:${payload.jti}`;
  const used = Number(await env.CV_DOWNLOADS.get(countKey)) || 0;
  if (used >= MAX_DOWNLOADS) {
    return html(errorPage("Batas 3 unduhan untuk tautan ini sudah tercapai. Minta ulang lewat situs."), 429);
  }

  const source = await loadPdfBytes(env);
  if (!source) return html(errorPage("CV sedang tidak tersedia. Coba lagi nanti."), 503);

  const stamped = await stampFooter(source, payload.email, env);
  await env.CV_DOWNLOADS.put(countKey, String(used + 1), { expirationTtl: 7 * 24 * 60 * 60 });

  return new Response(stamped, {
    headers: {
      "Content-Type": "application/pdf",
      "Content-Disposition": 'attachment; filename="Yunar-Prawira-CV.pdf"',
      "Cache-Control": "no-store, private",
      // PDF ini spesifik untuk satu penerima; jangan pernah masuk indeks.
      "X-Robots-Tag": "noindex, nofollow, noarchive",
    },
  });
}

/* ── sumber PDF ─────────────────────────────────────────────────────────── */

async function loadPdfBytes(env) {
  if (env.CV_PDF && typeof env.CV_PDF.get === "function") {
    const obj = await env.CV_PDF.get("cv-full.pdf");
    if (obj) return new Uint8Array(await obj.arrayBuffer());
    return null;
  }
  if (env.CV_PDF_B64) {
    try {
      const bin = atob(env.CV_PDF_B64);
      return Uint8Array.from(bin, (c) => c.charCodeAt(0));
    } catch {
      return null;
    }
  }
  return null;
}

/**
 * Menambahkan footer "Untuk: email | tanggal" ke setiap halaman.
 *
 * Memakai pdf-lib: ia menulis objek teks PDF yang benar-benar dirender, bukan
 * menyisipkan operator ke content stream yang (pada PDF hasil reportlab) sudah
 * terkompresi Flate. Percobaan pertama menyisipkan teks mentah ke stream
 * terkompresi: bytes-nya ada di file, tapi tidak pernah muncul saat dirender —
 * tes yang hanya memeriksa bytes akan lolos padahal footernya tidak terlihat.
 */
export async function stampFooter(pdfBytes, email, env) {
  const { PDFDocument, StandardFonts, rgb } = await import("pdf-lib");
  const doc = await PDFDocument.load(pdfBytes, { ignoreEncryption: true, updateMetadata: false });
  const font = await doc.embedFont(StandardFonts.Helvetica);

  const label = `Untuk: ${email} | ${new Date().toLocaleDateString("id-ID", {
    day: "2-digit", month: "short", year: "numeric", timeZone: "Asia/Jakarta",
  })}`;
  // Huruf di luar WinAnsi tidak bisa dirender font standar; ganti agar tidak crash.
  const safe = label.replace(/[^\x20-\x7E\xA0-\xFF]/g, "?");

  const size = 7;
  const margin = 18;
  const gray = rgb(0.55, 0.55, 0.55);

  for (const page of doc.getPages()) {
    const width = page.getWidth();
    let text = safe;
    // Jaga teks tetap dalam lebar halaman.
    while (text.length > 4 && font.widthOfTextAtSize(text, size) > width - margin * 2) {
      text = text.slice(0, -2);
    }
    page.drawText(text, { x: margin, y: 14, size, font, color: gray });
    // Garis tipis di atas footer, supaya tidak terlihat menempel di tepi kertas.
    page.drawLine({
      start: { x: margin, y: 26 }, end: { x: width - margin, y: 26 },
      thickness: 0.4, color: rgb(0.85, 0.85, 0.85),
    });
  }

  // Metadata: jangan bawa identitas pembuat asli ke file yang dibagikan.
  doc.setProducer("");
  doc.setCreator("");
  doc.setAuthor("");

  return new Uint8Array(await doc.save({ useObjectStreams: false }));
}

/* ── dipakai bersama dengan request-cv.js ───────────────────────────────── */

async function hmacKey(secret) {
  return crypto.subtle.importKey("raw", new TextEncoder().encode(secret),
    { name: "HMAC", hash: "SHA-256" }, false, ["verify"]);
}

function fromB64url(str) {
  // Token datang dari query string pengguna: base64 yang tidak valid harus
  // menghasilkan null, bukan melempar DOMException yang menjatuhkan Worker.
  try {
    const pad = str.length % 4 ? "=".repeat(4 - (str.length % 4)) : "";
    const bin = atob(str.replace(/-/g, "+").replace(/_/g, "/") + pad);
    return Uint8Array.from(bin, (c) => c.charCodeAt(0));
  } catch {
    return null;
  }
}

export async function verifyToken(token, secret) {
  if (typeof token !== "string" || !token.includes(".")) return null;
  const [body, sig] = token.split(".");
  if (!body || !sig) return null;
  const sigBytes = fromB64url(sig);
  const bodyBytes = fromB64url(body);
  if (!sigBytes || !bodyBytes) return null;
  const key = await hmacKey(secret);
  const ok = await crypto.subtle.verify("HMAC", key, sigBytes, new TextEncoder().encode(body));
  if (!ok) return null;
  let payload;
  try {
    payload = JSON.parse(new TextDecoder().decode(bodyBytes));
  } catch {
    return null;
  }
  if (typeof payload.exp !== "number" || payload.exp * 1000 < Date.now()) return null;
  return payload;
}

function errorPage(message) {
  return `<!doctype html><html lang="id"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex,nofollow">
<title>CV — tautan tidak berlaku</title>
<style>body{font:16px/1.6 system-ui,sans-serif;max-width:34rem;margin:16vh auto;padding:0 1.25rem;color:#1b2b45}
a{color:#b5762a}</style></head><body>
<p>${message}</p>
<p><a href="/">Kembali ke situs</a></p>
</body></html>`;
}

function html(body, status) {
  return new Response(body, {
    status,
    headers: { "Content-Type": "text/html; charset=utf-8", "X-Robots-Tag": "noindex, nofollow" },
  });
}
