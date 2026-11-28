/**
 * POST /api/request-cv — Fase B yunarprawira.com
 *
 * Alur: form publik (email + Turnstile) -> verifikasi Turnstile -> rate limit ->
 * tulis ke Sheet + notifikasi Telegram ke Yunar -> balas tautan bertoken.
 *
 * Keputusan desain (dari PRD, jangan diubah tanpa keputusan Yunar):
 *  - Token = HMAC(email|exp|jti, CV_TOKEN_SECRET). Stateless: tidak butuh database,
 *    cukup KV untuk menghitung jumlah unduhan.
 *  - Masa berlaku 7 hari, maksimal 3 unduhan. Unduhan ke-4 ditolak.
 *  - Yang DIKIRIM adalah tautan, bukan lampiran.
 *  - Tanpa nomor telepon di PDF; footer "Untuk: email | tanggal" ditambahkan saat unduh.
 *
 * Secrets yang WAJIB diset (wrangler pages secret put ... --project-name yunarprawira):
 *   TURNSTILE_SECRET   Cloudflare Turnstile secret key
 *   CV_TOKEN_SECRET    string acak >= 32 byte, untuk menandatangani token
 *   TELEGRAM_BOT_TOKEN bot token (notifikasi ke Yunar)
 *   TELEGRAM_CHAT_ID   chat tujuan notifikasi
 *   RESEND_API_KEY     kirim email tautan
 *   FROM_ADDRESS       mis. "Yunar Prawira <mail@yunarprawira.com>"
 * Binding KV: CV_DOWNLOADS (menghitung unduhan per token)
 */

const TOKEN_TTL_SECONDS = 7 * 24 * 60 * 60;
const MAX_DOWNLOADS = 3;
const PER_EMAIL_PER_DAY = 1;
const GLOBAL_PER_DAY = 50;

export async function onRequestPost({ request, env }) {
  try {
    const { email, turnstileToken } = await request.json();

    const emailError = validateEmail(email);
    if (emailError) return json({ ok: false, error: emailError }, 400);

    const remoteIp = request.headers.get("CF-Connecting-IP") || "";
    const human = await verifyTurnstile(turnstileToken, remoteIp, env);
    if (!human) return json({ ok: false, error: "verifikasi manusia gagal" }, 403);

    const day = new Date().toISOString().slice(0, 10);
    const emailKey = `rl:email:${day}:${email.toLowerCase()}`;
    const globalKey = `rl:global:${day}`;

    const alreadyAsked = Number(await env.CV_DOWNLOADS.get(emailKey)) || 0;
    if (alreadyAsked >= PER_EMAIL_PER_DAY) {
      return json({ ok: false, error: "sudah diminta hari ini — cek inbox" }, 429);
    }
    const globalCount = Number(await env.CV_DOWNLOADS.get(globalKey)) || 0;
    if (globalCount >= GLOBAL_PER_DAY) {
      return json({ ok: false, error: "batas harian tercapai" }, 429);
    }

    const exp = Math.floor(Date.now() / 1000) + TOKEN_TTL_SECONDS;
    const jti = crypto.randomUUID();
    const token = await signToken({ email: email.toLowerCase(), exp, jti }, env.CV_TOKEN_SECRET);
    const link = `${new URL(request.url).origin}/api/download-cv?t=${encodeURIComponent(token)}`;

    await sendLinkEmail({ email, link, exp }, env);
    await logRequest({ email, exp, jti, request }, env);
    await notifyYunar({ email, exp, request }, env);

    await env.CV_DOWNLOADS.put(emailKey, String(alreadyAsked + 1), {
      expirationTtl: 24 * 60 * 60,
    });
    await env.CV_DOWNLOADS.put(globalKey, String(globalCount + 1), {
      expirationTtl: 24 * 60 * 60,
    });

    return json({ ok: true });
  } catch (err) {
    // Jangan bocorkan detail internal ke klien; catat di log Worker.
    console.error("request-cv failed", err);
    return json({ ok: false, error: "gagal memproses permintaan" }, 500);
  }
}

export async function onRequestGet() {
  return json({ ok: false, error: "gunakan POST" }, 405);
}

/* ── validasi & keamanan ────────────────────────────────────────────────── */

export function validateEmail(email) {
  if (typeof email !== "string") return "email wajib diisi";
  const value = email.trim();
  if (value.length < 5 || value.length > 254) return "email tidak valid";
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(value)) return "email tidak valid";
  // Tolak alamat sekali-pakai yang paling umum; bukan daftar lengkap, hanya lapis pertama.
  const disposable = /@(mailinator|guerrillamail|10minutemail|tempmail|yopmail)\./i;
  if (disposable.test(value)) return "gunakan email yang benar-benar aktif";
  return null;
}

async function verifyTurnstile(token, remoteIp, env) {
  if (!token) return false;
  const body = new FormData();
  body.append("secret", env.TURNSTILE_SECRET);
  body.append("response", token);
  if (remoteIp) body.append("remoteip", remoteIp);
  try {
    const res = await fetch("https://challenges.cloudflare.com/turnstile/v0/siteverify", {
      method: "POST",
      body,
    });
    if (!res.ok) return false;
    const data = await res.json();
    return data.success === true;
  } catch {
    // Jaringan ke Cloudflare gagal: perlakukan sebagai gagal verifikasi,
    // bukan sebagai error server. Membalik ini menjadi "lolos" membuka gate.
    return false;
  }
}

/* ── token HMAC (stateless) ─────────────────────────────────────────────── */

async function hmacKey(secret) {
  return crypto.subtle.importKey(
    "raw",
    new TextEncoder().encode(secret),
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["sign", "verify"],
  );
}

function b64url(bytes) {
  return btoa(String.fromCharCode(...bytes)).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}

function fromB64url(str) {
  const pad = str.length % 4 ? "=".repeat(4 - (str.length % 4)) : "";
  return Uint8Array.from(atob(str.replace(/-/g, "+").replace(/_/g, "/") + pad), (c) => c.charCodeAt(0));
}

export async function signToken(payload, secret) {
  const body = b64url(new TextEncoder().encode(JSON.stringify(payload)));
  const key = await hmacKey(secret);
  const sig = new Uint8Array(await crypto.subtle.sign("HMAC", key, new TextEncoder().encode(body)));
  return `${body}.${b64url(sig)}`;
}

export async function verifyToken(token, secret) {
  if (typeof token !== "string" || !token.includes(".")) return null;
  const [body, sig] = token.split(".");
  if (!body || !sig) return null;
  let sigBytes;
  try {
    sigBytes = fromB64url(sig);
  } catch {
    return null; // token cacat dari query string: tolak, jangan crash
  }
  let bodyBytes;
  try {
    bodyBytes = fromB64url(body);
  } catch {
    return null;
  }
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

/* ── efek samping ───────────────────────────────────────────────────────── */

async function sendLinkEmail({ email, link, exp }, env) {
  const expiry = new Date(exp * 1000).toLocaleDateString("id-ID", {
    day: "numeric", month: "long", year: "numeric", timeZone: "Asia/Jakarta",
  });
  const text = [
    "Terima kasih sudah meminta CV lengkap.",
    "",
    `Tautan: ${link}`,
    `Berlaku sampai: ${expiry}`,
    "Maksimal 3 unduhan. Setelah itu minta ulang lewat situs.",
    "",
    "Yunar Prawira",
  ].join("\n");

  const res = await fetch("https://api.resend.com/emails", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${env.RESEND_API_KEY}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      from: env.FROM_ADDRESS,
      to: email,
      subject: "CV lengkap — Yunar Prawira",
      text,
    }),
  });
  if (!res.ok) {
    throw new Error(`resend ${res.status}: ${(await res.text()).slice(0, 200)}`);
  }
}

async function logRequest({ email, exp, jti, request }, env) {
  if (!env.LOG_WEBHOOK) return; // opsional: Google Apps Script / Sheet webhook
  await fetch(env.LOG_WEBHOOK, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      ts: new Date().toISOString(),
      email,
      exp: new Date(exp * 1000).toISOString(),
      jti,
      country: request.cf?.country || "",
      ua: (request.headers.get("User-Agent") || "").slice(0, 120),
    }),
  }).catch(() => {});
}

async function notifyYunar({ email, exp, request }, env) {
  if (!env.TELEGRAM_BOT_TOKEN || !env.TELEGRAM_CHAT_ID) return;
  const when = new Date(exp * 1000).toLocaleString("id-ID", { timeZone: "Asia/Jakarta" });
  const text = [
    "Permintaan CV lengkap",
    `email : ${email}`,
    `tautan berlaku s/d: ${when}`,
    `negara: ${request.cf?.country || "?"}`,
  ].join("\n");
  await fetch(`https://api.telegram.org/bot${env.TELEGRAM_BOT_TOKEN}/sendMessage`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ chat_id: env.TELEGRAM_CHAT_ID, text }),
  }).catch(() => {});
}

function json(payload, status = 200) {
  return new Response(JSON.stringify(payload), {
    status,
    headers: { "Content-Type": "application/json", "Cache-Control": "no-store" },
  });
}

export const _internals = { TOKEN_TTL_SECONDS, MAX_DOWNLOADS, PER_EMAIL_PER_DAY, GLOBAL_PER_DAY };
