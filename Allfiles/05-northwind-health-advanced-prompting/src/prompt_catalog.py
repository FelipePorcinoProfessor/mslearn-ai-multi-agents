"""Load explicit semantic prompt versions from source control."""
from pathlib import Path
CATALOG=Path(__file__).resolve().parents[1]/"assets"/"prompts"
def load_prompt(version:str)->str:
    if not version or any(part in version for part in ("/","\\","..")):raise ValueError("Invalid prompt version")
    path=CATALOG/f"clinical-agent-v{version}.txt"
    if not path.is_file():raise ValueError(f"Unknown prompt version: {version}")
    return path.read_text(encoding="utf-8")