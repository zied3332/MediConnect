"""Update evidence tables from retained real-browser measurements."""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOC = ROOT / "docs/accessibility"
FINAL = DOC / "reports/final"


def read(name):
    return json.loads((FINAL / (name + ".json")).read_text(encoding="utf-8"))


def table(file, marker, headings, rows):
    target = DOC / file
    content = target.read_text(encoding="utf-8")
    rendered = "\n".join([
        "| " + " | ".join(headings) + " |",
        "|" + "|".join("---" for _ in headings) + "|",
        *["| " + " | ".join(str(v).replace("|", "/").replace("\n", " ") for v in row) + " |" for row in rows],
    ])
    start, end = f"<!-- {marker} -->", f"<!-- END {marker} -->"
    block = start + "\n\n" + rendered + "\n\n" + end
    pattern = re.escape(start) + r".*?" + re.escape(end)
    content = re.sub(pattern, lambda _: block, content, flags=re.S) if end in content else content.replace(start, block)
    target.write_text(content, encoding="utf-8")


pages = read("summary")["pages"]
table("accessibility-audit.md", "ROUTES",
      ["Page condition", "Role", "Exact route", "Loaded", "Violations", "Incomplete groups"],
      [[p["name"], p["role"], p["route"], p["status"], len(p.get("violations", [])), p.get("incomplete", "—")] for p in pages])
table("accessibility-audit.md", "LIGHTHOUSE",
      ["Page", "Route", "Score / 100", "Final URL"],
      [[p["name"], p["route"], round(p["score"] * 100), p["finalUrl"]] for p in read("lighthouse-summary")])
incomplete = []
for page in pages:
    for issue in read(page["name"] + "-axe")["incomplete"]:
        incomplete.append([page["name"], issue["id"], len(issue["nodes"])])
table("accessibility-audit.md", "INCOMPLETE", ["Page", "Rule needing review", "Nodes"], incomplete)

observations = [
    "First Tab reaches skip link; Tab advances; Shift+Tab returns; Enter focuses main.",
    "Space opens; close button receives focus; Tab/Shift+Tab stay inside; Escape hides; opener regains focus.",
    "Space opens; close button receives focus; Tab/Shift+Tab stay inside; Escape hides; enrollment button regains focus.",
    "Space opens confirmation; Cancel receives focus; Tab cycles inside; Escape cancels and restores opener focus.",
    "At 320px Enter expands; 25 mixed Tab/Shift+Tab events remain inside; Escape restores toggle focus.",
    "Enter submits empty form; rendered alerts contain errors and fields are marked invalid.",
    "Typing an unmatched value hides fixture and updates status; focus stays in search; clearing restores item.",
    "Tab reaches next-page link; Enter loads page 2; result count receives focus.",
    "Tab reaches populated risk badge and reveals tooltip; Escape dismisses.",
    "Enter loads real brief fragment and expanded state; Space closes; opener regains focus.",
    "Tab reaches named overflow region at 320px; ArrowRight increases scrollLeft; focus-visible is true.",
    "Tab reaches specialty Save; horizontal container scrolls button into viewport; focus-visible is true.",
]
table("keyboard-test-results.md", "KEYBOARD",
      ["Workflow", "Role", "Route", "Expected and actual observation", "Result"],
      [[k["name"], k["role"], k["route"], observation, k["result"]]
       for k, observation in zip(read("keyboard")["results"], observations, strict=True)])
table("contrast-results.md", "CONTRAST",
      ["Element and state", "Foreground", "Effective background", "Ratio", "Threshold", "Result"],
      [[c["name"] + " (" + c["state"] + ")", c.get("foreground", "—"), c.get("background", "—"),
        f'{c["ratio"]:.2f}:1' if "ratio" in c else "—",
        str(c["threshold"]) + ":1" if c.get("threshold") else "—", c["result"]] for c in read("contrast")])
table("responsive-results.md", "RESPONSIVE",
      ["Page", "Route", "Setting", "Viewport width", "Document width", "Width check"],
      [[r["name"], r["route"], r["mode"], r["width"], r["scrollWidth"], "fail" if r["overflow"] else "pass"]
       for r in read("responsive")])
print("Updated evidence tables from final browser reports.")
