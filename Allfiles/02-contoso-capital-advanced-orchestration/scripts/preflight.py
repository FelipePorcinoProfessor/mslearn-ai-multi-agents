"""Side-effect-free Lab 02 checks."""
import ast, json, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
data=json.loads((ROOT/'assets/portfolio-request.json').read_text(encoding='utf-8'))
checks={'python_3_11':sys.version_info>=(3,11),'three_spokes':len(data.get('agents',[]))==3,'required_subset':set(data.get('required_agents',[]))<=set(a['name'] for a in data['agents']),'starter_syntax':bool(ast.parse((ROOT/'src/main.py').read_text(encoding='utf-8')))}
[print(f"{'PASS' if value else 'FAIL'} {name}") for name,value in checks.items()]
raise SystemExit(0 if all(checks.values()) else 1)