# Verifikasi

Satu perintah:

```
npm test          # atau ./verify.sh
```

Cakupan (5 langkah):
1. `node --check` semua `functions/api/*.js` dan `assets/*.js`
2. `py_compile` + JSON valid (`docs/_routes.json`, `package.json`)
3. Build idempoten — dua `build_cv.py` berturut-turut menghasilkan sha256 sama
4. `audit/test-build-cv.py` — 29 asersi perilaku gate + landmark
5. `audit/test-functions.mjs` — 50 asersi fungsi serverless

`deploy.sh` menjalankan `./verify.sh` sebelum commit, jadi tidak mungkin
men-deploy build yang gagal.

## Kenapa ada step 3

`swap_gate()` pernah menyisipkan `<section>` di dalam `<section>`; HTML tetap
terbaca dan build tetap exit 0, tapi axe melaporkan `landmark-unique`. Build
yang idempoten bukan tujuan akhir — step ini menangkap kelas bug "berubah setiap
build" yang tidak terlihat dari exit code.

## Yang tidak dicakup

Lighthouse, axe, dan uji ke produksi tidak dijalankan di sini karena butuh
jaringan dan Chrome. Hasilnya dicatat di `METRIK-PRD-2026-11-28.md`.

Fungsi yang butuh kredensial (`RESEND_API_KEY`, Turnstile asli) hanya diuji
dengan stub; jalur kirim email sungguhan belum pernah dieksekusi.
