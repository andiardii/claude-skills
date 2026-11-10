"""Run the "Steps" sheet of an FR-DEV-02 test plan with Playwright and write results back.

Usage:
    python runner.py ONLINE-152                      # looks in <output_dir>/ONLINE-152/
    python runner.py "C:/.../FR-DEV-02 Test Plan - ONLINE-152.xlsx"
    python runner.py ONLINE-152 --only 1,3-5 --headed --base-url http://desa.test
    python runner.py ONLINE-152 --retest             # writes Result - 2 / Notes instead

No AI is involved: every step is a fixed action from ACTIONS below. Cases are run in
order in one browser session (case 1 is usually "Login"), a screenshot is taken at the
end of each case (pass or fail), and the workbook is rebuilt with the results through
the test-plan skill's generator so the company template stays intact.
"""
import argparse
import datetime as dt
import importlib.util
import json
import os
import re
import shutil
import sys
import time

import openpyxl
from playwright.sync_api import Error as PWError
from playwright.sync_api import expect, sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
MAIN_FIRST_ROW = 9
STEPS_SHEET = "Steps"
SHOT_EXTS = (".png", ".jpg", ".jpeg")
VAR_RE = re.compile(r"\{\{\s*(\w+)\s*\}\}")
LOCATOR_PREFIXES = ("label", "placeholder", "text", "testid", "title", "alt", "role")


# ---------- config & input ----------

def load_config():
    with open(os.path.join(HERE, "config.json"), encoding="utf-8") as f:
        return json.load(f)


def load_env(*paths):
    """Simple KEY=VALUE .env reader; later files win, OS env vars only fill missing keys."""
    env = dict(os.environ)
    for p in paths:
        if not os.path.isfile(p):
            continue
        with open(p, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                v = v.strip().strip('"').strip("'")
                if v or k.strip() not in env:  # an empty KEY= must not wipe a value from an earlier file
                    env[k.strip()] = v
    return env


def resolve_xlsx(arg, cfg):
    if arg.lower().endswith(".xlsx"):
        return os.path.abspath(arg)
    folder = os.path.join(cfg["output_dir"], arg)
    path = os.path.join(folder, f"FR-DEV-02 Test Plan - {arg}.xlsx")
    if not os.path.isfile(path):
        sys.exit(f"File test plan tidak ditemukan: {path}")
    return path


def parse_only(text):
    if not text:
        return None
    nums = set()
    for part in text.split(","):
        part = part.strip()
        if "-" in part:
            a, b = part.split("-", 1)
            nums.update(range(int(a), int(b) + 1))
        elif part:
            nums.add(int(part))
    return nums


def cell_str(v):
    if v is None:
        return ""
    if isinstance(v, float) and v.is_integer():
        v = int(v)
    return str(v).strip()


def read_workbook(path):
    """Rebuild the generator spec (header, cases, steps) from the xlsx."""
    wb = openpyxl.load_workbook(path, data_only=True)
    ws = wb.worksheets[0]
    date = ws["C4"].value
    spec = {
        "ticket": cell_str(ws["C6"].value),
        "feature": cell_str(ws["C5"].value),
        "date": date.date().isoformat() if isinstance(date, dt.datetime) else None,
        "tester": "",
        "cases": [],
    }
    r = MAIN_FIRST_ROW
    while isinstance(ws.cell(r, 1).value, (int, float)) and ws.cell(r, 2).value:
        row = [ws.cell(r, c).value for c in range(1, 11)]
        spec["tester"] = spec["tester"] or cell_str(row[3])
        spec["cases"].append({
            "test_case": cell_str(row[1]),
            "category": cell_str(row[2]) or "Functional",
            "test_data": cell_str(row[4]),
            "result_1": cell_str(row[5]),
            "notes_1": cell_str(row[6]),
            "result_2": cell_str(row[7]),
            "notes_2": cell_str(row[8]),
            "result_3": cell_str(row[9]),
            "steps": [],
        })
        r += 1
    if STEPS_SHEET in wb.sheetnames:
        for row in wb[STEPS_SHEET].iter_rows(min_row=2, values_only=True):
            if not row or row[0] is None or not row[2]:
                continue
            n = int(row[0])
            if not 1 <= n <= len(spec["cases"]):
                sys.exit(f"Sheet Steps: No TC {n} tidak ada di daftar test case")
            spec["cases"][n - 1]["steps"].append({
                "action": cell_str(row[2]),
                "target": cell_str(row[3]),
                "value": cell_str(row[4]),
                "note": cell_str(row[5]) if len(row) > 5 else "",
            })
    return spec


# ---------- step execution ----------

class StepError(Exception):
    pass


class Session:
    def __init__(self, pw, cfg, args, folder):
        self.cfg, self.folder = cfg, folder
        launcher = getattr(pw, cfg.get("browser", "chromium"))
        self.browser = launcher.launch(headless=not args.headed and cfg.get("headless", True),
                                       slow_mo=args.slowmo if args.slowmo is not None else cfg.get("slow_mo_ms", 0))
        self.base_url = (args.base_url or cfg.get("base_url") or "").rstrip("/")
        self.dialog_mode = None
        self.dialog_text = None
        self.context = self.page = None
        self.new_context()

    def new_context(self):
        if self.context:
            self.context.close()
        self.context = self.browser.new_context(
            viewport=self.cfg.get("viewport"), ignore_https_errors=True, accept_downloads=True)
        self.context.set_default_timeout(self.cfg.get("timeout_ms", 10000))
        self.context.tracing.start(screenshots=True, snapshots=True, sources=False)
        self.page = self.context.new_page()
        self.page.on("dialog", self.on_dialog)

    def on_dialog(self, dialog):
        # Default: accept (confirm "Yakin hapus?" etc). dismissDialog/acceptDialog set a one-shot mode.
        mode, text = self.dialog_mode or "accept", self.dialog_text
        self.dialog_mode = self.dialog_text = None
        if mode == "dismiss":
            dialog.dismiss()
        else:
            dialog.accept(text) if text else dialog.accept()

    def url(self, target):
        if re.match(r"^https?://", target) or not self.base_url:
            return target
        return self.base_url + "/" + target.lstrip("/")

    def locator(self, target):
        if not target:
            raise StepError("Target (selector) wajib diisi untuk aksi ini")
        page = self.page
        m = re.match(r"^(\w+)=(.*)$", target, re.S)
        if m and m.group(1) in LOCATOR_PREFIXES and ">>" not in target:
            kind, arg = m.group(1), m.group(2).strip()
            exact = len(arg) > 1 and arg[0] == arg[-1] == '"'
            if exact:
                arg = arg[1:-1]
            if kind == "role":
                rm = re.match(r"^(\w+)(?:\[(.*)\])?$", arg)
                if not rm:
                    raise StepError(f"Format role salah: {target} (contoh: role=button[Simpan])")
                name = rm.group(2)
                if name and len(name) > 1 and name[0] == name[-1] == '"':
                    name, exact = name[1:-1], True
                return page.get_by_role(rm.group(1), name=name, exact=exact) if name else page.get_by_role(rm.group(1))
            fn = {"label": page.get_by_label, "placeholder": page.get_by_placeholder,
                  "text": page.get_by_text, "title": page.get_by_title, "alt": page.get_by_alt_text}
            if kind == "testid":
                return page.get_by_test_id(arg)
            return fn[kind](arg, exact=exact)
        return page.locator(target)

    def run_step(self, step, case_no, step_no):
        a, t, v = step["action"], step["target"], step["value"]
        timeout = self.cfg.get("timeout_ms", 10000)
        page = self.page
        loc = lambda: self.locator(t).first  # noqa: E731

        if a == "goto":
            page.goto(self.url(t or v), wait_until="load")
        elif a == "click":
            loc().click()
        elif a == "dblclick":
            loc().dblclick()
        elif a == "hover":
            loc().hover()
        elif a == "fill":
            loc().fill(v)
        elif a == "type":
            loc().press_sequentially(v, delay=30)
        elif a == "press":
            (loc().press(v) if t else page.keyboard.press(v))
        elif a == "select":
            loc().select_option(v)
        elif a == "check":
            loc().check()
        elif a == "uncheck":
            loc().uncheck()
        elif a == "upload":
            files = [p if os.path.isabs(p) else os.path.join(self.folder, p) for p in v.split(";") if p.strip()]
            missing = [p for p in files if not os.path.isfile(p)]
            if missing:
                raise StepError("File upload tidak ditemukan: " + ", ".join(missing))
            loc().set_input_files(files)
        elif a == "download":
            try:
                # Exports can take much longer than a normal step, so downloads get their own timeout.
                d = self.download(t, self.cfg.get("download_timeout_ms", 120000))
                out = os.path.join(self.folder, "downloads", v or d.suggested_filename)
                os.makedirs(os.path.dirname(out), exist_ok=True)
                d.save_as(out)
            finally:
                self.close_popups()
        elif a in ("acceptDialog", "dismissDialog"):
            self.dialog_mode = "accept" if a == "acceptDialog" else "dismiss"
            self.dialog_text = v or None
        elif a == "wait":
            page.wait_for_timeout(int(float(v or t or 1000)))
        elif a == "waitFor":
            loc().wait_for(state=v or "visible")
        elif a == "expectVisible":
            expect(loc()).to_be_visible(timeout=timeout)
        elif a == "expectHidden":
            expect(self.locator(t).first).to_be_hidden(timeout=timeout)
        elif a == "expectText":
            if t:
                expect(loc()).to_contain_text(v, timeout=timeout)
            else:
                expect(page.get_by_text(v).first).to_be_visible(timeout=timeout)
        elif a == "expectValue":
            expect(loc()).to_have_value(v, timeout=timeout)
        elif a == "expectUrl":
            want = v or t
            pattern = re.compile(want[3:]) if want.startswith("re:") else re.compile(re.escape(want))
            expect(page).to_have_url(pattern, timeout=timeout)
        elif a == "expectTitle":
            expect(page).to_have_title(re.compile(re.escape(v or t)), timeout=timeout)
        elif a == "expectCount":
            expect(self.locator(t)).to_have_count(int(v), timeout=timeout)
        elif a == "newSession":
            self.new_context()
        elif a == "screenshot":
            name = v or f"{case_no}-step{step_no}"
            self.screenshot(os.path.join(self.folder, "screens", "extra", name + ".png"))
        else:
            raise StepError(f"Aksi tidak dikenal: {a}")

    def download(self, target, timeout):
        # Target is a URL ("/export", "https://...") -> open it directly; otherwise a selector to click.
        if re.match(r"^(https?://|/(?!/))", target or ""):
            with self.page.expect_download(timeout=timeout) as info:
                try:
                    self.page.goto(self.url(target), timeout=timeout)
                except PWError as e:
                    if "Download is starting" not in str(e):
                        raise
            return info.value

        # The download may start in this tab or in a new one (window.open / target=_blank).
        got = []

        def on_download(d):
            got.append(d)

        def on_page(p):
            p.on("download", on_download)

        self.page.on("download", on_download)
        self.context.on("page", on_page)
        try:
            self.locator(target).first.click()
            deadline = time.time() + timeout / 1000
            while not got and time.time() < deadline:
                self.page.wait_for_timeout(200)
        finally:
            self.page.remove_listener("download", on_download)
            self.context.remove_listener("page", on_page)
        if not got:
            raise StepError(f"Tidak ada unduhan dalam {timeout // 1000} detik setelah klik {target} "
                            "(cek tab baru, mungkin halaman error)")
        return got[0]

    def close_popups(self):
        for p in self.context.pages:
            if p is not self.page:
                p.close()

    def screenshot(self, path):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        self.page.screenshot(path=path, full_page=self.cfg.get("full_page_screenshot", False))
        return path

    def close(self):
        try:
            self.context.tracing.stop()
        except PWError:
            pass
        self.browser.close()


ACTIONS = (
    "goto", "click", "dblclick", "fill", "type", "press", "select", "check", "uncheck",
    "upload", "hover", "download", "acceptDialog", "dismissDialog", "wait", "waitFor",
    "expectVisible", "expectHidden", "expectText", "expectValue", "expectUrl",
    "expectTitle", "expectCount", "newSession", "screenshot",
)


def substitute(text, env):
    def rep(m):
        if m.group(1) not in env:
            raise StepError(f"Variabel {{{{{m.group(1)}}}}} tidak ada di .env")
        return env[m.group(1)]
    return VAR_RE.sub(rep, text or "")


def short_error(e):
    msg = str(e).strip().splitlines()
    first = msg[0] if msg else e.__class__.__name__
    # Playwright puts the useful "waiting for ..." line under "Call log:".
    extra = next((ln.strip(" -") for ln in msg[1:] if "waiting for" in ln), "")
    first = re.sub(r"\s+", " ", first)
    return (first + (f" ({extra})" if extra else ""))[:300]


def run_case(sess, n, case, env, log):
    shot_dir = os.path.join(sess.folder, "screens")
    try:
        sess.context.tracing.start_chunk()
    except PWError:
        pass
    status, note = "Pass", "Sesuai ekspektasi (otomatis)"
    for j, step in enumerate(case["steps"], 1):
        desc = f"{step['action']} {step['target']}".strip()
        try:
            resolved = {**step, "target": substitute(step["target"], env), "value": substitute(step["value"], env)}
            sess.run_step(resolved, n, j)
            log(f"    ok   {j}. {desc}")
        except (StepError, PWError, AssertionError, ValueError) as e:
            status = "Failed"
            note = f"Gagal di step {j} ({desc}): {short_error(e)}"
            log(f"    FAIL {j}. {desc}\n         {short_error(e)}")
            break
    shot = None
    try:
        for ext in SHOT_EXTS:  # replace an older manual screenshot for this case
            old = os.path.join(shot_dir, f"{n}{ext}")
            if os.path.isfile(old):
                os.remove(old)
        shot = sess.screenshot(os.path.join(shot_dir, f"{n}.png"))
    except PWError as e:
        log(f"    (screenshot gagal: {short_error(e)})")
    try:
        if status == "Failed":
            trace = os.path.join(sess.folder, "traces", f"{n}.zip")
            os.makedirs(os.path.dirname(trace), exist_ok=True)
            sess.context.tracing.stop_chunk(path=trace)
            log(f"    trace: {trace}")
        else:
            sess.context.tracing.stop_chunk()
    except PWError:
        pass
    return status, note, shot


# ---------- output ----------

def load_generator(path):
    spec = importlib.util.spec_from_file_location("generate_test_plan", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def attach_screenshots(spec, folder):
    """The workbook is rebuilt from data, so re-embed screens/<n>.* for every case."""
    for i, case in enumerate(spec["cases"], 1):
        case.pop("screenshot_1", None)
        for ext in SHOT_EXTS:
            p = os.path.join(folder, "screens", f"{i}{ext}")
            if os.path.isfile(p):
                case["screenshot_1"] = p
                break


def main():
    ap = argparse.ArgumentParser(description="Jalankan sheet Steps test plan FR-DEV-02 dengan Playwright")
    ap.add_argument("target", help="ID tiket (mis. ONLINE-152) atau path file .xlsx")
    ap.add_argument("--only", help="nomor test case, mis. 1,3-5 (default: semua yang punya steps)")
    ap.add_argument("--base-url", help="override base_url, mis. http://desa.test")
    ap.add_argument("--headed", action="store_true", help="tampilkan browser")
    ap.add_argument("--slowmo", type=int, help="jeda antar aksi (ms)")
    ap.add_argument("--retest", action="store_true", help="tulis ke Result - 2 / Notes kedua")
    ap.add_argument("--dry-run", action="store_true", help="hanya validasi Excel, tidak membuka browser")
    args = ap.parse_args()

    cfg = load_config()
    xlsx = resolve_xlsx(args.target, cfg)
    folder = os.path.dirname(xlsx)
    spec = read_workbook(xlsx)
    env = load_env(os.path.join(HERE, ".env"), os.path.join(folder, ".env"))
    # BASE_URL_<PREFIX> (mis. BASE_URL_PROFIL untuk PROFIL-32) menang atas BASE_URL.
    prefix = os.path.basename(folder).split("-")[0].upper()
    if not args.base_url:
        args.base_url = env.get(f"BASE_URL_{prefix}") or env.get("BASE_URL")

    only = parse_only(args.only)
    todo = [(i, c) for i, c in enumerate(spec["cases"], 1) if c["steps"] and (not only or i in only)]
    bad = [f"TC {i} step {j}: '{s['action']}'" for i, c in todo for j, s in enumerate(c["steps"], 1)
           if s["action"] not in ACTIONS]
    if bad:
        sys.exit("Aksi tidak dikenal:\n- " + "\n- ".join(bad) + "\nAksi valid: " + ", ".join(ACTIONS))
    if not todo:
        sys.exit("Tidak ada test case dengan steps yang bisa dijalankan (cek sheet 'Steps').")

    if todo[0][1]["steps"][0]["action"] != "goto":
        print(f"PERINGATAN: TC {todo[0][0]} tidak diawali 'goto'. Case berjalan berurutan dalam satu "
              f"sesi browser, jadi kalau dijalankan tanpa case sebelumnya (mis. Login) hasilnya bisa gagal.")
    print(f"{spec['ticket']} - {spec['feature']}")
    print(f"{len(todo)} test case akan dijalankan, base_url={args.base_url or cfg.get('base_url') or '-'}")
    if args.dry_run:
        for i, c in todo:
            print(f"  TC {i}: {c['test_case']} ({len(c['steps'])} step)")
        return

    lines = []

    def log(msg):
        print(msg)
        lines.append(msg)

    results = {}
    started = time.time()
    with sync_playwright() as pw:
        sess = Session(pw, cfg, args, folder)
        try:
            for i, case in todo:
                log(f"TC {i}: {case['test_case']}")
                results[i] = run_case(sess, i, case, env, log)
                log(f"  => {results[i][0]}")
        finally:
            sess.close()

    for i, (status, note, _shot) in results.items():
        case = spec["cases"][i - 1]
        if args.retest:
            case["result_2"], case["notes_2"] = status, note
        else:
            case["result_1"], case["notes_1"] = status, note
    attach_screenshots(spec, folder)

    passed = sum(1 for s, _, _ in results.values() if s == "Pass")
    log(f"\nSelesai {time.time() - started:.0f} dtk: {passed} Pass, {len(results) - passed} Failed")

    with open(os.path.join(folder, "run-log.txt"), "w", encoding="utf-8") as f:
        f.write(f"{dt.datetime.now():%Y-%m-%d %H:%M:%S}\n" + "\n".join(lines) + "\n")
    spec_path = os.path.join(folder, "spec.json")
    with open(spec_path, "w", encoding="utf-8") as f:
        json.dump(spec, f, ensure_ascii=False, indent=2)

    gen = load_generator(cfg["generator"])
    gen.validate(spec)
    shutil.copy2(xlsx, xlsx + ".bak")
    try:
        gen.build(spec, gen.DEFAULT_TEMPLATE, xlsx)
    except PermissionError:
        sys.exit(f"Tidak bisa menulis {xlsx}. Tutup file di Excel lalu jalankan ulang "
                 f"(hasil sudah tersimpan di spec.json, bisa juga generate manual).")
    print(f"Excel diperbarui: {xlsx}")
    if passed < len(results):
        sys.exit(1)


if __name__ == "__main__":
    main()
