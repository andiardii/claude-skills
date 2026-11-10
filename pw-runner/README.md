# pw-runner

Menjalankan test plan FR-DEV-02 secara otomatis dengan Playwright, lalu mengisi Result, Notes, dan screenshot ke file Excel yang sama. **Tanpa AI saat dijalankan**, jadi tidak memakai token.

```
Codex (skill test-plan)  ──►  FR-DEV-02 Test Plan - <TIKET>.xlsx   (sheet utama + sheet "Steps")
                                       │
pw-runner (Playwright)   ──►  jalankan Steps → screens/<No>.png → Excel terisi Pass/Failed + screenshot
```

## Sekali pasang

```bash
pip install --user playwright openpyxl
python -m playwright install chromium
```

Lalu salin `.env.example` menjadi `.env` dan isi `BASE_URL` serta akun login Laragon. Kalau tiap tiket memakai aplikasi atau akun berbeda, taruh `.env` di folder tiket (`Documents\Test Plan\<TIKET>\.env`).

## Alur per tiket

1. **Buat test plan di Codex**: `$test-plan ONLINE-152` (atau minta "buatkan test plan beserta steps otomatis"). Codex menyusun test case dan steps, lalu menghasilkan `Documents\Test Plan\ONLINE-152\FR-DEV-02 Test Plan - ONLINE-152.xlsx`.
2. **Cek sheet Steps** di Excel. Boleh diedit manual, aksi punya dropdown. Referensi lengkap ada di [STEPS.md](STEPS.md).
3. **Jalankan**:
   ```bash
   python runner.py ONLINE-152
   ```
4. Buka Excel. Kolom Result - 1 dan Notes terisi, screenshot tertanam. Case tanpa steps (test manual) tidak disentuh.

## Opsi

| Opsi | Guna |
|---|---|
| `--headed` | tampilkan browser, untuk melihat jalannya test |
| `--slowmo 500` | perlambat tiap aksi (ms) |
| `--only 1,3-5` | jalankan case tertentu saja |
| `--base-url http://desa.test` | override BASE_URL |
| `--retest` | tulis ke Result - 2 / Notes kedua (setelah fix ulang) |
| `--dry-run` | validasi Excel saja tanpa membuka browser |

Argumen pertama boleh ID tiket (dicari di `output_dir` pada `config.json`) atau path file `.xlsx`.

## Output di folder tiket

| File | Isi |
|---|---|
| `FR-DEV-02 Test Plan - <TIKET>.xlsx` | diperbarui; versi sebelumnya disimpan sebagai `.xlsx.bak` |
| `screens/<No>.png` | screenshot akhir tiap case |
| `traces/<No>.zip` | rekaman case yang gagal. Buka dengan `python -m playwright show-trace traces/3.zip` untuk melihat langkah per langkah, DOM, dan network |
| `run-log.txt` | log tiap step |
| `spec.json` | data test plan terbaru (dipakai generator) |

## Kalau ada yang gagal

1. Baca kolom Notes atau `run-log.txt`: step mana dan selector apa yang tidak ketemu.
2. Buka trace-nya, atau jalankan ulang dengan `--headed --slowmo 500 --only <No>`.
3. Perbaiki Target di sheet Steps (cari selector dengan `npx playwright codegen http://desa.test`), simpan, lalu jalankan lagi. Tutup file di Excel sebelum menjalankan runner.

## Coba demo

```bash
python -m http.server 18765 -d example/site --bind 127.0.0.1
python runner.py "example/DEMO-1/FR-DEV-02 Test Plan - DEMO-1.xlsx" --headed
```

Hasil yang diharapkan: 4 Pass dan 1 Failed (case 5 memang dibuat gagal).

## Catatan

- `config.json`: `generator` menunjuk ke `generate_test_plan.py` milik skill test-plan, supaya format template (logo, tanda tangan, footer) tetap sama. `timeout_ms` adalah batas tunggu per aksi.
- Daftar aksi ada di dua tempat: `ACTIONS` di `runner.py` dan `STEP_ACTIONS` di generator. Kalau menambah aksi baru, ubah keduanya.
