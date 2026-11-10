---
name: start
description: Inisialisasi chat — ganti nama sesi/chat jadi ID tiket Jira atau judul bebas. Pakai hanya saat user mengetik /start <ID-TIKET> (mis. /start PROFIL-12, /start online-305) atau /start judul: <teks> (mis. /start judul: Skill Claude Baru), atau eksplisit minta "set nama chat jadi X". Jangan dijalankan otomatis di setiap chat baru.
---

# /start — inisialisasi chat

User menamai chat Claude dengan ID tiket Jira supaya chat, tiket, dan artefak (test plan, dll.) bisa dilacak balik. Untuk obrolan non-tiket (diskusi random), user memakai judul bebas. Skill ini cuma melakukan itu: ganti nama sesi. Hanya jalan saat user memanggilnya — chat tanpa `/start` dibiarkan apa adanya.

## Dua mode

- **Tiket:** `/start PROFIL-12` → judul `PROFIL-12`. Ikuti langkah di bawah.
- **Judul bebas:** argumen diawali `judul:` (tidak peka huruf besar/kecil) → judul = teks setelah `judul:`, di-trim, tulisan dipertahankan apa adanya (`/start judul: Skill Claude Baru` → `Skill Claude Baru`). Lewati validasi tiket, langsung ke langkah 3 dan 4. Kalau teksnya kosong, tanya judulnya.

## Format ID tiket

`<PREFIX>-<nomor>`, prefix = Jira Space:

| Prefix     | Space                 |
|------------|-----------------------|
| `PROFIL`   | Website Profil        |
| `ONLINE`   | Sistem Online         |
| `MOBILE`   | Mobile App            |
| `ANDI`     | Andi Smart            |
| `INTERNAL` | Internal App          |
| `ABSENSI`  | Absensi & Buku Tamu   |

Space **tidak** menentukan repo — tiket di Space mana pun bisa mengerjakan project mana pun. Jangan menebak repo dari prefix; repo diambil dari working directory / konteks.

## Langkah

1. **Ambil ID dari argumen** (mode tiket). Rapikan: trim, huruf besar, spasi/underscore di antara prefix dan nomor jadi `-` (`profil 12` → `PROFIL-12`).
2. **Validasi.**
   - Prefix tidak ada di tabel → tanya user ("Prefix `XYZ` belum saya kenal — maksudnya salah satu dari PROFIL/ONLINE/MOBILE/ANDI/INTERNAL/ABSENSI, atau Space baru?"). Kalau user bilang Space baru, lanjutkan saja.
   - Nomor kosong atau bukan angka (mis. `PROFIL-XX`, `/start` tanpa argumen) → minta ID lengkapnya. Jangan rename dengan placeholder.
3. **Rename sesi** dengan `mcp__ccd_session_mgmt__set_session_title` (`session_id: "self"`, `title: "<ID atau judul>"`). Judulnya persis ID tiket / judul bebas, tanpa tambahan. Kalau tool belum ter-load, load dulu lewat ToolSearch (`select:mcp__ccd_session_mgmt__set_session_title`). Kalau tool tidak tersedia (bukan di desktop app), beri tahu user untuk rename manual.
4. **Konfirmasi singkat**, satu-dua baris, lalu tunggu instruksi:
   > Sesi diberi nama **PROFIL-12** (Website Profil). Siap — tiketnya tentang apa?

   Mode judul bebas: "Sesi diberi nama **Skill Claude Baru**." saja (tanpa nama Space).

   Kalau user sudah menulis deskripsi tugas setelah ID (mis. `/start ONLINE-88 perbaiki export excel`), jangan berhenti di konfirmasi — langsung kerjakan tugasnya.

ID tiket ini juga dipakai skill lain (mis. `test-plan`) untuk penamaan file dan test case, jadi pastikan formatnya benar.
