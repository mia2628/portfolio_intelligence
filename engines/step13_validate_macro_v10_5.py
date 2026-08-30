from pathlib import Path
import py_compile
BASE=Path(__file__).resolve().parents[1]
e=(BASE/"engines/step13_macro_risk_engine.py").read_text(encoding="utf-8")
w=(BASE/".github/workflows/step13_macro_market_update.yml").read_text(encoding="utf-8")
html=(BASE/"docs/index.html").read_text(encoding="utf-8")
for x in ["git_history_candidate","GIT_LAST_KNOWN_GOOD","REPOSITORY_DATA_ONLY","external_network_required"]:
    assert x in e
assert "fred.stlouisfed.org" not in e
assert "requests" not in e
assert "fetch-depth: 0" in w
assert w.count("- cron:")==8
assert "미 10Y 변화" in html
py_compile.compile(str(BASE/"engines/step13_macro_risk_engine.py"),doraise=True)
print("PASS: v10.5 repository-only macro recovery architecture validated.")
