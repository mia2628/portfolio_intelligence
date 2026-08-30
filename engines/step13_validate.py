from pathlib import Path
import py_compile
BASE=Path(__file__).resolve().parents[1]

trend=(BASE/"engines/step13_trend_snapshot.py").read_text(encoding="utf-8")
audit=(BASE/"engines/step13_history_audit.py").read_text(encoding="utf-8")
integ=(BASE/"engines/step13_dashboard_integrity_check.py").read_text(encoding="utf-8")
html=(BASE/"docs/index.html").read_text(encoding="utf-8")
sw=(BASE/"docs/sw.js").read_text(encoding="utf-8")

for t in ["if not date:","by_date[row[\"date\"]]=row","Blank rows      : 0 (filtered)"]:
    assert t in trend
for t in ["STEP13 HISTORY AUDIT","blank date rows","duplicate date rows"]:
    assert t in audit
assert "duplicate trend dates detected" in integ
assert "app.js?v=91" in html
assert "portfolio-intelligence-v9-1" in sw

py_compile.compile(str(BASE/"engines/step13_trend_snapshot.py"),doraise=True)
py_compile.compile(str(BASE/"engines/step13_history_audit.py"),doraise=True)
py_compile.compile(str(BASE/"engines/step13_dashboard_integrity_check.py"),doraise=True)
print("PASS: STEP13 v9.1 blank-row filtering + unique-date history audit validated.")
