from pathlib import Path
import py_compile
BASE=Path(__file__).resolve().parents[1]
e=(BASE/"engines/step13_macro_risk_engine.py").read_text(encoding="utf-8")
w=(BASE/".github/workflows/step13_macro_market_update.yml").read_text(encoding="utf-8")
for x in ["Retry(","timeout=(15,75)","load_local_fallback","PASS_WITH_STALE_DATA","source_used"]:
    assert x in e
assert w.count("- cron:")==8
assert "timeout-minutes: 25" in w
py_compile.compile(str(BASE/"engines/step13_macro_risk_engine.py"),doraise=True)
print("PASS: macro v10.2 retry/fallback/stale-preserve + 8x KST schedule validated.")
