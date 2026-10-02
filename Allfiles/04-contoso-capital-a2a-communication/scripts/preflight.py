"""Side-effect-free Lab 04 checks."""
import ast,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];card=json.loads((ROOT/'assets/risk-agent-card.json').read_text(encoding='utf-8'));request=json.loads((ROOT/'assets/a2a-request.json').read_text(encoding='utf-8'))
checks={'python_3_11':sys.version_info>=(3,11),'card_shape':all(k in card for k in ('id','url','capabilities')),'jsonrpc':request.get('jsonrpc')=='2.0','syntax':all(ast.parse(p.read_text(encoding='utf-8')) for p in (ROOT/'src').glob('*.py'))}
[print(f"{'PASS' if v else 'FAIL'} {k}") for k,v in checks.items()];raise SystemExit(0 if all(checks.values()) else 1)