"""Side-effect-free Lab 05 checks."""
import ast,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];cases=[json.loads(x) for x in (ROOT/'assets/prompt-cases.jsonl').read_text(encoding='utf-8').splitlines() if x.strip()]
checks={'python_3_11':sys.version_info>=(3,11),'prompt_versions':all((ROOT/'assets/prompts'/f'clinical-agent-v{v}.txt').is_file() for v in ('1.0.0','1.1.0')),'synthetic_cases':all(x.get('consent')=='synthetic' and x.get('deidentified') for x in cases),'syntax':all(ast.parse(p.read_text(encoding='utf-8')) for p in (ROOT/'src').glob('*.py'))}
[print(f"{'PASS' if v else 'FAIL'} {k}") for k,v in checks.items()];raise SystemExit(0 if all(checks.values()) else 1)