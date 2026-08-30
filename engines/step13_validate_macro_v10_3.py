from pathlib import Path
import py_compile
BASE=Path(__file__).resolve().parents[1]
e=(BASE/"engines/step13_macro_risk_engine.py").read_text(encoding="utf-8")
w=(BASE/".github/workflows/step13_macro_market_update.yml").read_text(encoding="utf-8")
for x in ["LOCAL_FIRST_WITH_FRED_FALLBACK","ThreadPoolExecutor","timeout=(5,12)","PASS_WITH_STALE_DATA"]:
    assert x in e
assert "Retry(" not in e
assert w.count("- cron:")==8
assert "timeout-minutes: 8" in w
py_compile.compile(str(BASE/"engines/step13_macro_risk_engine.py"),doraise=True)
print("PASS: macro v10.3 local-first / parallel short FRED fallback / 8x schedule validated.")
