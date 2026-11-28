# Verifikasi

Satu perintah:

```
npm test          # atau ./verify.sh
```

Cakupan (6 langkah):
1. `node --check` semua `functions/api/*.js` dan `assets/*.js`
2. `py_compile` + JSON valid (`docs/_routes.json`, `package.json`)
3. Build idempoten — dua `build_cv.py` berturut-turut menghasilkan sha256 sama
4. `audit/test-build-cv.py` — 29 asersi perilaku gate + landmark
5. `audit/test-functions.mjs` — 57 asersi fungsi (token, email, stampFooter,
   batas unduhan, jalur PDF via KV, PDF rusak -> 503)
6. `audit/test-upload-cv.sh` — sanitizer + gerbang isi CV (pakai `--check`,
   tidak menulis ke KV)

`deploy.sh` menjalankan `./verify.sh` sebelum commit, jadi tidak mungkin
men-deploy build yang gagal.

## Aturan pipa

Jangan menaruh pemeriksaan di ujung kiri pipa. `cmd | tail` menyembunyikan
exit code `cmd`; `cmd | grep -q` membuat `cmd` kena SIGPIPE (141) yang dengan
`set -o pipefail` terbaca sebagai gagal — atau sebaliknya, **gerbang lolos pada
data yang justru melanggar**. Itu persis yang terjadi pada `upload-cv.sh` dan
membuat PDF bertelepon sempat terunggah ke KV.

## Tes tidak boleh punya efek samping

`scripts/upload-cv.sh --check` menjalankan semua pemeriksaan lalu berhenti
sebelum `PUT`. Tanpa itu, menguji penolakan justru mengunggah PDF kotor ke
produksi. Diverifikasi: `npm test` 3x berturut-turut, KV tetap 404.

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
