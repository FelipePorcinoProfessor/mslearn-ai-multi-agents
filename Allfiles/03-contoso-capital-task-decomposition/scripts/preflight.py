"""Side-effect-free Lab 03 checks."""
import ast,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];data=json.loads((ROOT/'assets/research-query.json').read_text(encoding='utf-8'))
checks={'python_3_11':sys.version_info>=(3,11),'registry':len(data.get('registry',{}))>=4,'query':bool(data.get('query')),'starter_syntax':bool(ast.parse((ROOT/'src/main.py').read_text(encoding='utf-8')))}
[print(f"{'PASS' if v else 'FAIL'} {k}") for k,v in checks.items()];raise SystemExit(0 if all(checks.values()) else 1)