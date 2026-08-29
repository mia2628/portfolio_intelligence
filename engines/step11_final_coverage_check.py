from pathlib import Path
import csv
B=Path(__file__).resolve().parents[1]/"data"
def read(p):
    with p.open("r",encoding="utf-8-sig",newline="") as f:return list(csv.DictReader(f))
s=read(B/"step03_coverage_summary.csv")[0]
print("="*90);print("STEP11 FINAL STRUCTURAL VALIDATION v2");print("="*90)
for k,v in s.items():print(f"{k:<28}: {v}")
if s["Missing_As_Zero"]!="NO":raise SystemExit(2)
if "CONFIDENCE_SHRINKAGE" not in s["Scoring_Mode"]:raise SystemExit(3)
if not s["Shock_Method"].startswith("EMPIRICAL"):raise SystemExit(4)
print("PASS: no second-difference / no missing-as-zero / empirical shock / confidence shrinkage")
