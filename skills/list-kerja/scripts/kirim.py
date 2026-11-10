"""Kirim laporan kerja ke grup Telegram. Teks penjelasan dibaca dari stdin."""
import argparse
import json
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

ENV_PATH = Path(__file__).resolve().parent.parent / ".env"
JIRA_BROWSE = "https://digides.atlassian.net/browse/"
TICKET_RE = re.compile(r"^[A-Z][A-Z0-9]*-\d+$")


def format_message(ticket, text):
    text = " ".join(text.split())
    if not text:
        sys.exit("Penjelasan kosong.")
    if not ticket:
        return text
    ticket = ticket.strip().upper()
    if not TICKET_RE.match(ticket):
        sys.exit(f"ID tiket tidak valid: {ticket}")
    return f"[{ticket}] {text}\n{JIRA_BROWSE}{ticket}"


def load_env():
    if not ENV_PATH.exists():
        sys.exit(f".env belum ada: {ENV_PATH}")
    env = {}
    for line in ENV_PATH.read_text(encoding="utf-8-sig").splitlines():
        key, sep, value = line.partition("=")
        if sep and not key.strip().startswith("#"):
            env[key.strip()] = value.strip().strip("\"'")
    return env


def require(env, key):
    if not env.get(key):
        sys.exit(f"{key} kosong di {ENV_PATH}")
    return env[key]


def telegram(token, method, payload):
    request = urllib.request.Request(
        f"https://api.telegram.org/bot{token}/{method}",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            return json.load(response)["result"]
    except urllib.error.HTTPError as error:
        body = json.load(error)
        sys.exit(f"Telegram menolak: {body.get('description', error.code)}")
    except urllib.error.URLError as error:
        sys.exit(f"Tidak bisa menghubungi Telegram: {error.reason}")


def list_chats(token):
    chats = {}
    for update in telegram(token, "getUpdates", {}):
        for value in update.values():
            chat = value.get("chat") if isinstance(value, dict) else None
            if chat and chat["type"] in ("group", "supergroup"):
                chats[chat["id"]] = chat.get("title", "")
    if not chats:
        print("Belum ada grup terbaca. Masukkan bot ke grup, kirim satu pesan di sana, lalu ulangi.")
    for chat_id, title in chats.items():
        print(f"{chat_id}\t{title}")


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ticket", help="ID tiket Jira, mis. PROFIL-12")
    parser.add_argument("--dry-run", action="store_true", help="tampilkan pesan tanpa mengirim")
    parser.add_argument("--list-chats", action="store_true", help="tampilkan chat ID grup yang terlihat bot")
    args = parser.parse_args()

    if args.list_chats:
        list_chats(require(load_env(), "TELEGRAM_BOT_TOKEN"))
        return

    message = format_message(args.ticket, sys.stdin.buffer.read().decode("utf-8"))
    if args.dry_run:
        print(message)
        return

    env = load_env()
    telegram(
        require(env, "TELEGRAM_BOT_TOKEN"),
        "sendMessage",
        {
            "chat_id": require(env, "TELEGRAM_CHAT_ID"),
            "text": message,
            "link_preview_options": {"is_disabled": True},
        },
    )
    print(message)


if __name__ == "__main__":
    main()
