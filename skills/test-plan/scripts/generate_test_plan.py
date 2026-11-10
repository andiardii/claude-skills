"""Fill the FR-DEV-02 Test Plan template from a JSON spec.

Usage:
    python generate_test_plan.py spec.json output.xlsx [--template path]

spec.json:
{
  "ticket": "ONLINE-152",
  "feature": "Perbaikan filter Buku Induk Penduduk",
  "date": "2026-10-27",            # optional, default today
  "tester": "Nama Tester",
  "cases": [
    {
      "test_case": "Mengakses halaman Buku Induk Penduduk",
      "category": "Functional",      # Functional | Security
      "test_data": "",               # optional
      "result_1": "Pass",            # optional: Pass | Failed | ""
      "notes_1": "",                 # optional text
      "screenshot_1": "C:/.../1.png",# optional image, embedded in Notes
      "result_2": "", "notes_2": "", "result_3": "",
      "steps": [                     # optional, for pw-runner automation
        {"action": "goto", "target": "/login", "value": "", "note": ""}
      ]
    }
  ]
}

Cases with "steps" get rows in an extra "Steps" sheet, which pw-runner executes.
"""
import argparse
import copy
import datetime as dt
import json
import math
import os
import sys

import openpyxl
from openpyxl.drawing.image import Image as XLImage
from openpyxl.drawing.spreadsheet_drawing import AnchorMarker, OneCellAnchor
from openpyxl.drawing.xdr import XDRPositiveSize2D
from openpyxl.styles import Alignment
from openpyxl.utils.units import pixels_to_EMU

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_TEMPLATE = os.path.join(HERE, "..", "assets", "FR-DEV-02 Test Plan.xlsx")

SHEET = "TEST"           # blank sheet in the template
FIRST_ROW = 9            # first test case row
TPL_LAST_ROW = 41        # last numbered row in the blank template
FOOTER_FIRST = 42        # signature block + disclaimer start here...
FOOTER_LAST = 54         # ...and end here
COLS = "ABCDEFGHIJ"
CATEGORIES = {"Functional", "Security"}
RESULTS = {"", "Pass", "Failed"}
SHOT_WIDTH_PX = 370      # fits column G, like the screenshots in the filled example sheet
SHOT_PAD_PX = 6
TEST_DATA_WIDTH = 24
STEPS_SHEET = "Steps"
STEPS_HEADER = ("No TC", "Step", "Aksi", "Target", "Nilai", "Keterangan")
STEPS_WIDTHS = (8, 6, 16, 40, 36, 40)
# Keep in sync with ACTIONS in pw-runner/runner.py.
STEP_ACTIONS = (
    "goto", "click", "dblclick", "fill", "type", "press", "select", "check", "uncheck",
    "upload", "hover", "download", "acceptDialog", "dismissDialog", "wait", "waitFor",
    "expectVisible", "expectHidden", "expectText", "expectValue", "expectUrl",
    "expectTitle", "expectCount", "newSession", "screenshot",
)


def snapshot_cell(c):
    return {"value": c.value, "style": copy.copy(c._style)}


def clear_row(ws, r):
    for col in range(1, ws.max_column + 1):
        c = ws.cell(r, col)
        if c.coordinate in ws.merged_cells:
            continue
        c.value = None
        c.style = "Normal"
    ws.row_dimensions[r].height = None


def text_height(case, widths):
    """Rough row height (pt) so wrapped text is visible without autofit."""
    lines = 1
    for key, col in (("test_case", "B"), ("test_data", "E"), ("notes_1", "G"), ("notes_2", "I")):
        text = str(case.get(key) or "")
        if not text:
            continue
        per_line = max(int(widths.get(col, 9) * 0.9), 6)
        n = sum(max(1, math.ceil(len(part) / per_line)) for part in text.split("\n"))
        lines = max(lines, n)
    return max(15.75, lines * 13.2 + 4)


def validate(spec):
    errors = []
    for k in ("ticket", "feature", "tester", "cases"):
        if not spec.get(k):
            errors.append(f"'{k}' wajib diisi")
    for i, case in enumerate(spec.get("cases") or [], 1):
        if not case.get("test_case"):
            errors.append(f"case {i}: 'test_case' kosong")
        if case.get("category", "Functional") not in CATEGORIES:
            errors.append(f"case {i}: category harus Functional/Security")
        for rk in ("result_1", "result_2", "result_3"):
            if (case.get(rk) or "") not in RESULTS:
                errors.append(f"case {i}: {rk} harus Pass/Failed/kosong")
        for sk in ("screenshot_1",):
            p = case.get(sk)
            if p and not os.path.isfile(p):
                errors.append(f"case {i}: file {sk} tidak ditemukan: {p}")
        for j, step in enumerate(case.get("steps") or [], 1):
            if step.get("action") not in STEP_ACTIONS:
                errors.append(f"case {i} step {j}: aksi '{step.get('action')}' tidak dikenal")
    if errors:
        sys.exit("Spec tidak valid:\n- " + "\n- ".join(errors))


def write_steps(wb, cases):
    if not any(case.get("steps") for case in cases):
        return
    from openpyxl.styles import Font, PatternFill
    from openpyxl.worksheet.datavalidation import DataValidation

    ws = wb.create_sheet(STEPS_SHEET)
    ws.append(STEPS_HEADER)
    for c in ws[1]:
        c.font = Font(bold=True)
        c.fill = PatternFill("solid", fgColor="D9E1F2")
    for i, case in enumerate(cases, 1):
        for j, step in enumerate(case.get("steps") or [], 1):
            ws.append([i, j, step.get("action"), step.get("target") or None,
                       step.get("value") or None, step.get("note") or None])
    for col, width in zip("ABCDEF", STEPS_WIDTHS):
        ws.column_dimensions[col].width = width
    ws.freeze_panes = "A2"
    dv = DataValidation(type="list", formula1='"' + ",".join(STEP_ACTIONS) + '"', allow_blank=True)
    ws.add_data_validation(dv)
    dv.add(f"C2:C{max(ws.max_row, 2) + 200}")


def build(spec, template, out):
    wb = openpyxl.load_workbook(template)
    for name in wb.sheetnames:
        if name != SHEET:
            del wb[name]
    ws = wb[SHEET]
    cases = spec["cases"]
    n = len(cases)
    last_row = FIRST_ROW + n - 1
    shift = last_row - TPL_LAST_ROW

    # Snapshot the data-row style and the footer block before rewriting.
    row_style = {col: copy.copy(ws[f"{col}{FIRST_ROW}"]._style) for col in COLS}
    footer = {
        r: {col: snapshot_cell(ws.cell(r, col)) for col in range(1, ws.max_column + 1)}
        for r in range(FOOTER_FIRST, FOOTER_LAST + 1)
    }
    footer_heights = {r: ws.row_dimensions[r].height for r in footer}
    footer_merges = [
        m for m in list(ws.merged_cells.ranges)
        if m.min_row >= FOOTER_FIRST and m.max_row <= FOOTER_LAST
    ]
    for m in footer_merges:
        ws.unmerge_cells(str(m))
    # Template images in the footer (the CTO signature); anchor rows are 0-based.
    footer_images = [
        img for img in ws._images
        if hasattr(img.anchor, "_from") and img.anchor._from.row >= FOOTER_FIRST - 1
    ]

    for r in range(FIRST_ROW, max(FOOTER_LAST, FOOTER_LAST + shift) + 1):
        clear_row(ws, r)

    # Header
    date = dt.date.fromisoformat(spec["date"]) if spec.get("date") else dt.date.today()
    ws["C4"].value = dt.datetime(date.year, date.month, date.day)
    ws["C5"].value = spec["feature"]
    ws["C6"].value = spec["ticket"]
    # Template merges Feature over C5:D5 only, which clips longer titles; span it like the ticket row.
    if "C5:D5" in [str(m) for m in ws.merged_cells.ranges]:
        ws.unmerge_cells("C5:D5")
        ws.merge_cells("C5:J5")
    # Column E is at default width in the template, too narrow for real test data.
    if (ws.column_dimensions["E"].width or 0) < TEST_DATA_WIDTH:
        ws.column_dimensions["E"].width = TEST_DATA_WIDTH

    widths = {k: v.width for k, v in ws.column_dimensions.items() if v.width}
    for i, case in enumerate(cases):
        r = FIRST_ROW + i
        values = {
            "A": i + 1,
            "B": case["test_case"],
            "C": case.get("category") or "Functional",
            "D": spec["tester"],
            "E": case.get("test_data") or None,
            "F": case.get("result_1") or None,
            "G": case.get("notes_1") or None,
            "H": case.get("result_2") or None,
            "I": case.get("notes_2") or None,
            "J": case.get("result_3") or None,
        }
        for col in COLS:
            c = ws[f"{col}{r}"]
            c._style = copy.copy(row_style[col])
            c.value = values[col]
        height = text_height(case, widths)
        shot = case.get("screenshot_1")
        if shot:
            img = XLImage(shot)
            scale = SHOT_WIDTH_PX / img.width
            img.width, img.height = SHOT_WIDTH_PX, int(img.height * scale)
            # Notes text sits at the top of the cell, the screenshot below it.
            text_px = 0
            if case.get("notes_1"):
                al = ws[f"G{r}"].alignment
                ws[f"G{r}"].alignment = Alignment(horizontal=al.horizontal, vertical="top", wrap_text=al.wrap_text)
                text_px = int(text_height({"notes_1": case["notes_1"]}, widths) / 0.75)
            img.anchor = OneCellAnchor(
                _from=AnchorMarker(col=COLS.index("G"), colOff=pixels_to_EMU(SHOT_PAD_PX),
                                   row=r - 1, rowOff=pixels_to_EMU(text_px + SHOT_PAD_PX)),
                ext=XDRPositiveSize2D(pixels_to_EMU(img.width), pixels_to_EMU(img.height)),
            )
            ws.add_image(img)
            # +15%: Excel on a scaled display renders images taller than px*0.75 pt.
            height = max(height, (text_px + img.height + 2 * SHOT_PAD_PX) * 0.75 * 1.15)
        ws.row_dimensions[r].height = height

    # Footer, moved to sit right under the table.
    for r, cells in footer.items():
        nr = r + shift
        for col, snap in cells.items():
            c = ws.cell(nr, col)
            c.value = snap["value"]
            c._style = snap["style"]
        ws.row_dimensions[nr].height = footer_heights[r]
    for m in footer_merges:
        ws.merge_cells(
            start_row=m.min_row + shift, start_column=m.min_col,
            end_row=m.max_row + shift, end_column=m.max_col,
        )
    for img in footer_images:
        img.anchor._from.row += shift
        if getattr(img.anchor, "to", None) is not None:
            img.anchor.to.row += shift

    ws.title = spec["ticket"][:31]
    write_steps(wb, cases)
    wb.active = 0
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    wb.save(out)
    return last_row + 1, shift


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("spec")
    ap.add_argument("out")
    ap.add_argument("--template", default=DEFAULT_TEMPLATE)
    a = ap.parse_args()
    with open(a.spec, encoding="utf-8") as f:
        spec = json.load(f)
    validate(spec)
    build(spec, a.template, a.out)
    print(f"OK: {len(spec['cases'])} test case -> {os.path.abspath(a.out)}")


if __name__ == "__main__":
    main()
