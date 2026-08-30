from pathlib import Path
import ast

BASE=Path(__file__).resolve().parents[1]
P=BASE/"engines"/"step09_rebalancing_engine.py"
tree=ast.parse(P.read_text(encoding="utf-8"))

evaluate=None
for node in tree.body:
    if isinstance(node, ast.FunctionDef) and node.name=="evaluate":
        evaluate=node
        break
if evaluate is None:
    raise SystemExit("FAIL: evaluate() not found")

args=[a.arg for a in evaluate.args.args]
if "gold_weight_source" not in args:
    raise SystemExit("FAIL: evaluate() does not receive gold_weight_source")

# Ensure main passes the variable into evaluate.
text=P.read_text(encoding="utf-8")
needle="""result = evaluate(
        current_date,
        last_rebalance,
        gold_weight,
        gold_weight_source,"""
if needle not in text:
    raise SystemExit("FAIL: main() does not pass gold_weight_source to evaluate()")

print("PASS: STEP9 gold_weight_source is explicitly passed into evaluate().")
