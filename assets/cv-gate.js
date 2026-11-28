/**
 * Form permintaan CV lengkap — disisipkan ke halaman /cv/ oleh build_cv.py.
 * Tanpa framework. Progressive enhancement: tanpa JS, form tetap mengirim
 * POST biasa dan Worker membalas JSON (jelek) — karena itu tombol mailto tetap
 * jadi jalur utama sampai gate ini terbukti bekerja di produksi.
 */
(function () {
  "use strict";

  var form = document.querySelector("[data-cv-gate]");
  if (!form) return;

  var status = form.querySelector("[data-cv-status]");
  var button = form.querySelector("button[type=submit]");
  var successBox = form.querySelector("[data-cv-success]");
  var mailtoFallback = form.querySelector("[data-cv-mailto]");

  function say(message, kind) {
    if (!status) return;
    status.textContent = message;
    status.dataset.kind = kind || "info";
    status.hidden = false;
  }

  form.addEventListener("submit", function (event) {
    event.preventDefault();
    if (button) button.disabled = true;
    say("Mengirim permintaan…", "info");

    var data = new FormData(form);
    var payload = {
      email: String(data.get("email") || "").trim(),
      turnstileToken: String(data.get("cf-turnstile-response") || ""),
    };

    fetch("/api/request-cv", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    })
      .then(function (res) {
        return res.json().then(function (body) {
          return { ok: res.ok, status: res.status, body: body };
        });
      })
      .then(function (result) {
        if (result.ok && result.body.ok) {
          form.hidden = true;
          if (successBox) successBox.hidden = false;
          return;
        }
        var message = result.body && result.body.error ? result.body.error : "Gagal mengirim.";
        if (result.status === 429) {
          message = "Sudah ada permintaan hari ini. Cek inbox, atau minta lagi besok.";
        }
        say(message, "error");
        if (mailtoFallback) mailtoFallback.hidden = false;
        if (button) button.disabled = false;
        if (window.turnstile && typeof window.turnstile.reset === "function") {
          window.turnstile.reset();
        }
      })
      .catch(function () {
        say("Tidak bisa menghubungi server. Pakai tautan email di bawah.", "error");
        if (mailtoFallback) mailtoFallback.hidden = false;
        if (button) button.disabled = false;
      });
  });
})();
