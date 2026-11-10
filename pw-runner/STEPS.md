# Referensi sheet "Steps"

Sheet `Steps` di file FR-DEV-02 berisi langkah otomatis per test case. Satu baris = satu aksi.

| Kolom | Isi |
|---|---|
| No TC | Nomor test case di sheet utama (kolom No) |
| Step | Urutan langkah (1, 2, 3, ...) |
| Aksi | Salah satu aksi di tabel bawah |
| Target | Selector elemen, atau URL untuk `goto` |
| Nilai | Teks, opsi, nama file, angka, dll. sesuai aksi |
| Keterangan | Bebas, tidak dijalankan |

Test case **tanpa** baris di sheet Steps dianggap test manual: hasilnya tidak disentuh runner.

## Cara kerja

- Semua case dijalankan **berurutan dalam satu sesi browser**. Jadi cukup case 1 = "Login", case berikutnya sudah dalam keadaan login.
- Mulai tiap case dengan `goto` ke halamannya sendiri supaya bisa dijalankan terpisah dengan `--only`.
- Begitu satu step gagal, case itu berhenti dan dinilai **Failed**, lalu lanjut ke case berikutnya.
- Screenshot diambil di akhir setiap case (Pass maupun Failed) ke `screens/<No>.png` dan tertanam di kolom Notes.
- Dialog `confirm()`/`alert()` otomatis di-**accept**. Pakai `dismissDialog` sebelum klik kalau ingin menekan "Batal".

## Aksi

| Aksi | Target | Nilai | Contoh |
|---|---|---|---|
| `goto` | URL relatif ke BASE_URL atau URL penuh | | `/penduduk` |
| `click` | selector | | `role=button[Simpan]` |
| `dblclick` | selector | | |
| `hover` | selector | | |
| `fill` | selector input | teks | `label=NIK` / `3500000000000001` |
| `type` | selector input | teks (diketik per huruf, untuk autocomplete) | |
| `press` | selector (opsional) | tombol keyboard | `Enter`, `Control+A` |
| `select` | selector `<select>` | value atau teks opsi | `Krajan` |
| `check` / `uncheck` | selector checkbox/radio | | |
| `upload` | selector `input[type=file]` | path file, relatif ke folder tiket; banyak file dipisah `;` | `test-data/tc04.xlsx` |
| `download` | selector tombol yang memicu unduhan (juga kalau unduhannya dibuka di tab baru), atau URL relatif/penuh untuk diunduh langsung | nama file simpan (opsional) | disimpan ke `downloads/`; gagal kalau tidak ada unduhan (mis. server error). Batas tunggu `download_timeout_ms` di config.json (default 120 detik) |
| `acceptDialog` | | teks untuk `prompt()` (opsional) | |
| `dismissDialog` | | | dialog berikutnya ditekan Batal |
| `wait` | | milidetik | `1500` |
| `waitFor` | selector | `visible` (default) / `hidden` / `attached` / `detached` | |
| `expectVisible` | selector | | |
| `expectHidden` | selector | | |
| `expectText` | selector (opsional) | teks yang harus ada | tanpa target = cari di seluruh halaman |
| `expectValue` | selector input | nilai persis | |
| `expectUrl` | | potongan URL, atau `re:<regex>` | `/dashboard` |
| `expectTitle` | | potongan judul halaman | |
| `expectCount` | selector | jumlah elemen | `tbody tr` / `10` |
| `newSession` | | | buang cookie/login, mulai browser bersih |
| `screenshot` | | nama file (opsional) | screenshot tambahan ke `screens/extra/` |

## Target (selector)

Utamakan selector yang dilihat user, karena lebih tahan perubahan HTML:

| Bentuk | Artinya |
|---|---|
| `label=Email` | input dengan label "Email" (`<label for>` atau label yang membungkus input) |
| `placeholder=Cari nama` | input dengan placeholder |
| `role=button[Simpan]` | tombol bernama "Simpan". Role lain: `link`, `heading`, `textbox`, `combobox`, `checkbox`, `tab`, `menuitem`, `row`, `cell` |
| `text=Data berhasil disimpan` | elemen yang berisi teks |
| `title=Hapus` / `alt=Logo` / `testid=btn-simpan` | atribut title / alt / data-testid |
| `"..."` di dalam nilai | cocok persis, mis. `role=button["Simpan"]` atau `text="Edit"` |
| selain itu | CSS/XPath biasa Playwright: `#nik`, `.btn-danger`, `//table//tr[2]` |
| `A >> B` | rantai Playwright: `tr:has-text('3500000000000002') >> role=button[name='Hapus']` |

Kalau beberapa elemen cocok, yang pertama yang dipakai (kecuali `expectCount`).

Cara cepat mencari selector: `npx playwright codegen http://desa.test`, klik elemennya, salin locator yang muncul.

## Variabel

`{{NAMA}}` di Target/Nilai diganti dari `.env`. Dibaca dari `pw-runner/.env` lalu `<folder tiket>/.env` (yang kedua menang).
`BASE_URL` di `.env` dipakai sebagai alamat dasar `goto`. Kalau ada `BASE_URL_<PREFIX>` sesuai prefix tiket (mis. `BASE_URL_PROFIL` untuk `PROFIL-32`), itu yang dipakai. Simpan password di `.env`, jangan di Excel.
