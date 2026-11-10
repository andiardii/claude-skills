# claude-skills

Kumpulan skill Claude Code buatan sendiri beserta alat pendukungnya. Repo ini private karena memuat template dokumen perusahaan.

## Isi

| Folder | Fungsi |
|---|---|
| `skills/start` | Mengganti nama sesi jadi ID tiket Jira atau judul bebas. |
| `skills/test-plan` | Membuat dokumen Test Plan FR-DEV-02 (xlsx) per tiket. |
| `skills/list-kerja` | Mengirim laporan pekerjaan ke grup Telegram lewat bot. |
| `pw-runner` | Menjalankan langkah test dari xlsx dengan Playwright, tanpa AI. Dipakai oleh `test-plan`. |

## Pemasangan

Salin folder di `skills/` ke `~/.claude/skills/`, lalu siapkan file per mesin berikut. File-file ini tidak masuk repo.

| File | Dibuat dari |
|---|---|
| `skills/test-plan/config.json` | `skills/test-plan/config.example.json` |
| `skills/list-kerja/.env` | `skills/list-kerja/.env.example` |
| `pw-runner/config.json` | `pw-runner/config.example.json` |
| `pw-runner/.env` | `pw-runner/.env.example` |

`skills/test-plan/SKILL.md` memanggil `pw-runner` lewat path tetap. Sesuaikan path itu kalau `pw-runner` berada di lokasi lain.
