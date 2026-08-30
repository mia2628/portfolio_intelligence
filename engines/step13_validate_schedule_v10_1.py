from pathlib import Path
p=Path(".github/workflows/step13_macro_market_update.yml")
t=p.read_text(encoding="utf-8")
expected=[
'30 23 * * *',
'30 1 * * *',
'0 3 * * *',
'30 4 * * *',
'30 6 * * *',
'0 8 * * *',
'30 9 * * *',
'0 11 * * *',
]
for e in expected:
    assert e in t, e
assert t.count("- cron:") == 8
print("PASS: STEP13 macro update schedule set to 8 daily KST times.")
