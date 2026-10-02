"""CLI for A2A registry and protocol exercises."""
from __future__ import annotations
import argparse,json
from pathlib import Path
import httpx
from dotenv import load_dotenv
from .registry import Registry

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

def main()->None:
    p=argparse.ArgumentParser();sub=p.add_subparsers(dest="command",required=True)
    r=sub.add_parser("register");r.add_argument("--card",type=Path,required=True);r.add_argument("--tenant",default="contoso")
    d=sub.add_parser("discover");d.add_argument("--tenant",required=True);d.add_argument("--capability",required=True)
    s=sub.add_parser("send");s.add_argument("--url",required=True);s.add_argument("--message",type=Path,required=True)
    a=p.parse_args()
    if a.command=="send": result=httpx.post(a.url,json=json.loads(a.message.read_text(encoding="utf-8")),timeout=60).json()
    elif a.command=="register": result=Registry().register(json.loads(a.card.read_text(encoding="utf-8")),a.tenant)
    else: result=Registry().discover(a.tenant,a.capability)
    print(json.dumps(result,indent=2))
if __name__=="__main__":main()