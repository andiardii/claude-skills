---
name: list-kerja
description: Kirim laporan pekerjaan yang baru selesai ke grup Telegram lewat bot, berformat [ID-TIKET] penjelasan + link tiket Jira. Pakai hanya saat user mengetik /list-kerja atau /list-kerja <penjelasan>. Jangan dijalankan otomatis saat tugas selesai.
disable-model-invocation: true
---

# /list-kerja — lapor kerjaan ke grup Telegram

User memanggil skill ini setiap selesai satu tugas, supaya grup tahu apa yang baru dikerjakan. Satu panggilan = satu pesan untuk tiket sesi ini.

## Format pesan

Dengan ID tiket:

```
[PROFIL-12] Perbaiki validasi login saat email kosong
https://digides.atlassian.net/browse/PROFIL-12
```

Tanpa ID tiket: baris penjelasan saja, tanpa kurung dan tanpa link. Format ini dibuat oleh script, jadi jangan disusun manual.

## Langkah

1. **Ambil ID tiket dari judul sesi** dengan `mcp__ccd_session_mgmt__get_session` (`session_id: "self"`). Kalau tool belum ter-load, load dulu lewat ToolSearch (`select:mcp__ccd_session_mgmt__get_session`). Judul dianggap ID tiket kalau seluruhnya berpola `<PREFIX>-<nomor>` (mis. `PROFIL-12`). Judul lain (mis. dari `/start judul: ...`) atau tool tidak tersedia berarti kirim tanpa ID. Jangan menanyakan ID ke user.

2. **Tentukan penjelasan.**
   - Ada argumen (`/list-kerja perbaiki validasi login`): pakai teks user apa adanya, langsung ke langkah 4.
   - Tanpa argumen: tulis satu kalimat dari pekerjaan yang benar-benar selesai di sesi ini, lanjut ke langkah 3. Tulis dalam bahasa Indonesia yang dimengerti anggota grup non-teknis: apa yang berubah, bukan nama file atau fungsi. Kalau sesi ini belum menyelesaikan pekerjaan apa pun, minta user menuliskan penjelasannya.

3. **Minta persetujuan draf** (hanya kalau penjelasan dirangkum Claude). Tampilkan pesan persis seperti yang akan terkirim, lalu tunggu user setuju atau mengoreksi. Pesan masuk ke grup dan dibaca orang lain, sedangkan rangkuman bisa keliru.

4. **Kirim** lewat Bash tool. Teks lewat stdin supaya tanda kutip dan karakter non-ASCII aman:

   ```bash
   python ~/.claude/skills/list-kerja/scripts/kirim.py --ticket PROFIL-12 <<'EOF'
   Perbaiki validasi login saat email kosong
   EOF
   ```

   Tanpa ID tiket, hilangkan `--ticket`. Kirim sekali saja. Kalau gagal, jangan otomatis mengulang kecuali errornya jelas pesan belum terkirim dan penyebabnya sudah dibetulkan.

5. **Konfirmasi singkat**, satu baris: `Terkirim ke grup: [PROFIL-12] ...`.

## Kalau script gagal

- `.env belum ada` atau nilainya kosong: minta user menyalin `.env.example` jadi `.env` di folder skill dan mengisinya sendiri. Jangan minta token ditempel di chat, dan jangan membaca atau menampilkan isi `.env`.
- Butuh chat ID grup: jalankan `python ~/.claude/skills/list-kerja/scripts/kirim.py --list-chats` setelah user mengirim satu pesan di grup.
- Error dari Telegram: sampaikan pesan errornya apa adanya. `chat not found` biasanya berarti bot belum masuk grup atau chat ID salah.
