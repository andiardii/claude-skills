---
name: deskripsi-tiket
description: Tulis deskripsi tiket Jira bergaya Product/Project Manager (latar belakang, tujuan, ruang lingkup, kriteria penerimaan) sebagai teks siap copy-paste ke kolom Description Jira. Pakai hanya saat user mengetik /deskripsi-tiket atau /deskripsi-tiket <catatan kasar>. Jangan dijalankan otomatis.
disable-model-invocation: true
---

# /deskripsi-tiket — deskripsi tiket ala PM

User butuh isi kolom **Description** tiket Jira yang rapi, seperti ditulis PM: orang yang membuka tiket langsung paham *kenapa* tugas ini ada, *apa* yang dikerjakan, dan *kapan* dianggap selesai. Hasilnya cuma teks. Skill ini tidak mengirim apa pun ke Jira dan tidak mengubah file.

## Langkah

1. **Ambil ID tiket dari judul sesi** dengan `mcp__ccd_session_mgmt__get_session` (`session_id: "self"`). Kalau tool belum ter-load, load lewat ToolSearch (`select:mcp__ccd_session_mgmt__get_session`). Judul dianggap ID tiket kalau seluruhnya berpola `<PREFIX>-<nomor>` (mis. `PROFIL-12`). Selain itu, anggap tidak ada ID. Jangan menanyakan ID ke user; ID hanya dipakai untuk konteks, tidak wajib muncul di teks.

2. **Kumpulkan bahan**, dari yang paling diutamakan:
   - Argumen user (`/deskripsi-tiket tambah filter tanggal di laporan absensi`): ini inti tugasnya. Lengkapi dari konteks sesi kalau ada.
   - Tanpa argumen: pakai pekerjaan yang dibahas atau dikerjakan di sesi ini (percakapan, perubahan kode, `git diff`/`git log` di repo yang sedang dipakai kalau relevan).
   - Kalau dua-duanya kosong, minta user menulis satu-dua kalimat tentang tugasnya. Jangan mengarang tugas.

3. **Tentukan jenis tiket** dari bahan: **Fitur/Request** (hal baru atau perubahan perilaku) atau **Bug** (sesuatu yang seharusnya jalan tapi tidak). Kalau ragu, pakai Fitur.

4. **Tulis deskripsi** memakai template di bawah, dalam bahasa Indonesia yang baku tapi luwes.
   - Sudut pandang PM: fokus ke kebutuhan pengguna dan dampak bisnis, bukan nama file, fungsi, atau tabel. Detail teknis hanya boleh di bagian **Catatan Teknis**, singkat, dan bagian itu dihapus kalau tidak ada yang penting.
   - Kriteria penerimaan harus bisa dicek QA: konkret, satu perilaku per butir, bukan "berjalan dengan baik".
   - Jangan mengarang angka, nama klien, tenggat, atau keputusan yang tidak ada di bahan. Kalau ada yang belum jelas tapi penting, taruh di **Pertanyaan Terbuka** daripada ditebak.
   - Ringkas. Hapus bagian yang isinya kosong atau basa-basi.

5. **Tampilkan hasil** di dalam satu blok kode ```` ```markdown ```` supaya user tinggal klik copy. Editor Jira Cloud mengubah Markdown (`##`, `-`, `**`, `1.`) jadi format saat ditempel. Di luar blok kode cukup satu baris, mis. `Deskripsi untuk PROFIL-12, siap ditempel ke Jira.` Kalau ada Pertanyaan Terbuka, sebutkan juga di baris itu bahwa ada hal yang perlu dipastikan.

Kalau user minta revisi (lebih singkat, ganti nada, tambah poin), tulis ulang seluruh blok, jangan hanya potongan.

## Template Fitur / Request

```markdown
## Latar Belakang
<Masalah atau kebutuhan saat ini, siapa yang terdampak, kenapa perlu dikerjakan. 2–4 kalimat.>

## Tujuan
<Hasil yang diharapkan dari sudut pandang pengguna/bisnis. 1–2 kalimat.>

## Ruang Lingkup
- <Yang dikerjakan>
- <...>

**Di luar cakupan:**
- <Yang sengaja tidak dikerjakan di tiket ini>

## Kriteria Penerimaan
1. <Perilaku yang bisa dicek>
2. <...>

## Catatan Teknis
- <Opsional, singkat>

## Pertanyaan Terbuka
- <Opsional>
```

## Template Bug

```markdown
## Ringkasan
<Apa yang salah dan dampaknya ke pengguna. 1–2 kalimat.>

## Langkah Reproduksi
1. <...>
2. <...>

## Perilaku Saat Ini
<Yang terjadi sekarang.>

## Perilaku yang Diharapkan
<Yang seharusnya terjadi.>

## Kriteria Penerimaan
1. <Bug tidak muncul lagi pada langkah di atas>
2. <Perilaku terkait yang tidak boleh ikut rusak>

## Catatan Teknis
- <Opsional: penyebab atau perbaikan, singkat>
```
