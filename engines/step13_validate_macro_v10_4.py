from pathlib import Path
import py_compile
BASE=Path(__file__).resolve().parents[1]
e=(BASE/"engines/step13_macro_risk_engine.py").read_text(encoding="utf-8")
w=(BASE/".github/workflows/step13_macro_market_update.yml").read_text(encoding="utf-8")
for x in ["discover_local_sources","INDICATOR_CANDIDATES","VALUE_CANDIDATES","WIDE","LONG","LOCAL_AUTODETECT_WITH_FRED_FALLBACK"]:
    assert x in e
assert "timeout-minutes: 5" in w
assert w.count("- cron:")==8
py_compile.compile(str(BASE/"engines/step13_macro_risk_engine.py"),doraise=True)
print("PASS: v10.4 local CSV wide/long auto-detection validated.")
