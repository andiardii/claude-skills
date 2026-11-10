---
name: test-plan
description: Buat dokumen Test Plan xlsx (format FR-DEV-02 PT Digital Desa Indonesia) untuk laporan tiket Jira yang baru selesai dikerjakan (feature, bugfix, request). Pakai saat user menjalankan /test-plan, minta "buatkan test plan", "test case tiket ini", "dokumen FR-DEV-02", atau minta update hasil/screenshot test plan tiket.
argument-hint: "[TICKET-ID] [catatan tambahan]"
---

# Test Plan FR-DEV-02 per tiket

Menghasilkan `FR-DEV-02 Test Plan - <TICKET>.xlsx` dari template perusahaan di `assets/`, diisi oleh `scripts/generate_test_plan.py`. Jangan menyusun xlsx dengan cara lain, karena script inilah yang menjaga format template (logo, header dokumen, tanda tangan CTO, footer).

Path di bawah relatif terhadap folder skill ini (`~/.claude/skills/test-plan`).

## 1. Tentukan ID tiket

Urutan sumber:
1. Argumen perintah, misalnya `/test-plan ONLINE-152`.
2. Judul chat/sesi ini. User selalu menamai chat dengan ID tiket.
3. Nama branch git, misalnya `bugfix/ONLINE-152`.

Format ID: `PREFIX-angka`. Prefix adalah Space Jira (PROFIL, ONLINE, MOBILE, ANDI, LANDING, ABSENSI), BUKAN nama repo. Repo diambil dari folder kerja sesi. Kalau sumber-sumber di atas tidak cocok atau tidak ada, tanyakan ke user.

## 2. Baca config

`config.json`:
- `tester`: nama untuk kolom Tester. Kalau kosong, tanyakan sekali ke user lalu simpan ke config.
- `output_dir`: folder output. Setiap tiket punya subfolder `<output_dir>/<TICKET>/`.

## 3. Pahami apa yang dikerjakan di tiket

- Jalankan `git log` dan `git diff` di branch tiket terhadap branch dasarnya (`develop`, `dev`, `master`, atau `main`; cek mana yang ada). Pahami fitur atau halaman apa yang berubah dari sisi user aplikasi, bukan dari sisi kode.
- Kalau konektor Jira (Atlassian) aktif, baca judul, deskripsi, dan acceptance criteria tiket. Kalau belum aktif, cukup dari diff ditambah penjelasan user.
- Jenis tiket (feature, bugfix, atau request) diambil dari Jira, prefix branch (`feature/`, `bugfix/`, `hotfix/`), atau tanyakan ke user.

## 4. Susun test case

Gaya mengikuti contoh yang sudah dipakai tim: judul aksi pendek dalam Bahasa Indonesia, dari sudut pandang user aplikasi. Contoh:
- "Login"
- "Mengakses halaman Buku Induk Penduduk"
- "Edit data Buku Tanah Kas Desa"
- "Print Buku Agenda"
- "Tes Fitur Cek Duplikat Buku Induk Penduduk"
- "Membuat Surat menggunakan hasil data penduduk dari pencarian"

Panduan isi:
- Mulai dengan prasyarat alur kalau relevan, misalnya "Login" dan "Mengakses halaman X".
- **Feature**: alur utama, tambah/edit/hapus/print/export yang tersentuh, validasi input wajib, dan kasus batas yang masuk akal.
- **Bugfix**: satu case yang mereproduksi kondisi bug dan memastikan bug sudah tidak muncul, plus case regresi untuk fitur di sekitarnya yang ikut tersentuh diff.
- **Request**: sesuai permintaan di tiket.
- Category `Security` untuk akses tanpa login, akses lintas desa/role, injeksi input, atau data sensitif. Selain itu `Functional`.
- `test_data` diisi kalau case butuh input spesifik (NIK contoh, nama dusun, file upload). Kalau tidak perlu, biarkan kosong. Pakai data contoh fiktif, jangan data warga asli.
- Biasanya 5–15 case. Jangan menggembungkan jumlah case.

Tunjukkan daftar test case ke user (tabel ringkas) sebelum membuat file, supaya bisa dikoreksi.

## 5. Tulis spec dan generate

Simpan spec di `<output_dir>/<TICKET>/spec.json`:

```json
{
  "ticket": "ONLINE-152",
  "feature": "<judul tiket / ringkasan fitur>",
  "date": "YYYY-MM-DD",
  "tester": "<dari config>",
  "cases": [
    {"test_case": "...", "category": "Functional", "test_data": "",
     "result_1": "", "notes_1": "", "screenshot_1": "",
     "result_2": "", "notes_2": "", "result_3": ""}
  ]
}
```

Lalu jalankan:

```bash
python scripts/generate_test_plan.py "<output_dir>/<TICKET>/spec.json" "<output_dir>/<TICKET>/FR-DEV-02 Test Plan - <TICKET>.xlsx"
```

Script akan menolak spec yang tidak valid dan menyebutkan alasannya. Perbaiki spec-nya, jangan script-nya.

## 5b. Steps otomatis untuk pw-runner

Kalau aplikasinya web dan bisa diakses dari Laragon lokal, tambahkan `"steps"` di setiap case yang bisa diotomasi. Generator akan menulisnya ke sheet `Steps`, lalu kamu sendiri yang menjalankan pw-runner dan memeriksa hasilnya (langkah 5c).

```json
{"test_case": "Login", "category": "Functional", "test_data": "",
 "steps": [
   {"action": "goto", "target": "/login"},
   {"action": "fill", "target": "label=Email", "value": "{{ADMIN_EMAIL}}"},
   {"action": "fill", "target": "label=Password", "value": "{{ADMIN_PASSWORD}}"},
   {"action": "click", "target": "role=button[Masuk]"},
   {"action": "expectUrl", "value": "/dashboard"}
 ]}
```

Aturan:
- Baca dulu `D:\Software\laragon\www\random\pw-runner\STEPS.md` untuk daftar aksi dan format Target. Jangan memakai aksi di luar daftar itu.
- Ambil selector dari kode view/template di repo (label, placeholder, teks tombol, `id`, `name`), jangan menebak. Utamakan `label=`, `role=...[nama]`, `placeholder=`, lalu `#id`/`[name=...]`.
- Case berjalan berurutan dalam satu sesi browser: case 1 biasanya "Login". Mulai setiap case berikutnya dengan `goto` ke halamannya.
- Setiap case diakhiri minimal satu aksi `expect...` yang membuktikan hasilnya, misalnya toast sukses, isi tabel, atau URL.
- Password dan akun pakai variabel `{{NAMA}}` dari `.env` (`pw-runner/.env` atau `<output_dir>/<TICKET>/.env`), jangan ditulis langsung. Kalau butuh variabel baru, beri tahu user agar menambahkannya di `.env`.
- File upload ditaruh di `<output_dir>/<TICKET>/test-data/` dan diisi relatif, misalnya `test-data/tc04.xlsx`.
- Case yang tidak bisa diotomasi (print fisik, cek isi PDF, aplikasi mobile) dibiarkan tanpa `steps`. Case seperti ini tetap dites manual.

## 5c. Jalankan pw-runner dan cek hasilnya

Kalau ada case yang punya `steps`, jalankan runner sendiri setelah generate. Jangan menyuruh user menjalankannya.

1. **Validasi dulu**: `python D:\Software\laragon\www\random\pw-runner\runner.py <TICKET> --dry-run`. Kalau gagal (aksi tidak dikenal, nomor TC salah), perbaiki `steps` di spec, generate ulang, lalu ulangi.
2. **Cek prasyarat**: harus ada `.env` (di `pw-runner/.env` atau `<output_dir>/<TICKET>/.env`) yang berisi `BASE_URL` (atau `BASE_URL_<PREFIX>`) dan semua variabel `{{...}}` yang dipakai steps. Kalau ada yang belum diisi, minta user menambahkannya. Jangan menebak password atau mengisinya sendiri.
3. **Jalankan**: `python D:\Software\laragon\www\random\pw-runner\runner.py <TICKET>` (headless). Batasi timeout sampai 10 menit atau jalankan di background, karena satu run bisa lebih dari 2 menit. Exit code 0 berarti semua Pass. Exit code 1 berarti ada yang Failed atau ada error. Baca baris `Selesai ...: X Pass, Y Failed` di output.
4. **Kalau ada yang Failed**, baca `<output_dir>/<TICKET>/run-log.txt` dan Notes case tersebut, lalu tentukan penyebabnya:
   - **Kesalahan steps** (selector tidak ketemu, salah halaman, timing): cek ulang selector di kode view/template repo, perbaiki `steps` di `spec.json` (yang sudah berisi hasil terakhir dari runner), generate ulang, lalu jalankan ulang hanya case itu ditambah case Login, misalnya `--only 1,4`, karena semua case berjalan dalam satu sesi browser. Maksimal 2 putaran perbaikan per case.
   - **Bug aplikasi** (halaman error, data tidak tersimpan, perilaku tidak sesuai tiket): jangan ubah `expect...` agar lolos. Biarkan hasilnya Failed dan laporkan ke user beserta bukti dari log, Notes, dan `traces/<No>.zip`.
   - **Lingkungan** (Laragon mati, `BASE_URL` tidak bisa diakses, file xlsx sedang terbuka di Excel): hentikan, lalu beri tahu user apa yang perlu dibereskan.
5. Ringkas hasilnya ke user: jumlah Pass/Failed, lalu untuk setiap case yang Failed sebutkan nomor, judul, penyebab, dan apakah sudah diperbaiki atau diduga bug aplikasi.

## 6. Hasil test dan screenshot

- **Jangan pernah mengisi `result_*` dengan Pass/Failed kalau belum benar-benar dites.** Di generate pertama, kolom hasil dibiarkan kosong.
- Setelah user mengetes, user memberi tahu hasilnya. Screenshot bukti ditaruh di `<output_dir>/<TICKET>/screens/` dengan nama sesuai nomor case (`1.png`, `2.jpg`, ...). Isi `result_1`, `notes_1`, dan `screenshot_1` di spec, lalu jalankan ulang perintah generate. File xlsx akan ditimpa dengan versi terbaru.
- `result_2`/`notes_2`/`result_3` hanya dipakai untuk retest (misalnya setelah fix ulang).
- Case yang punya steps diisi otomatis oleh pw-runner (langkah 5c), termasuk screenshot `screens/<No>.png` dan `spec.json`. Untuk retest setelah fix ulang, jalankan runner dengan `--retest` supaya hasilnya ditulis ke Result - 2.

## 7. Lapor ke user

Sebutkan path file xlsx, jumlah test case, hasil pw-runner (Pass/Failed dan penyebab setiap Failed), dan case manual yang masih perlu dites user.
