"""Minimal A2A agent-card and JSON-RPC service backed by Foundry Agents v2."""
from __future__ import annotations
import os
from pathlib import Path
from typing import Any
from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import PromptAgentDefinition
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException

load_dotenv(Path(__file__).resolve().parents[1] / ".env")
app=FastAPI(title="Contoso A2A risk agent")
CARD={"name":"contoso-risk-agent","description":"Synthetic portfolio risk analysis","url":f"{os.getenv('A2A_BASE_URL','http://127.0.0.1:8000')}/a2a","version":"1.0.0","skills":[{"id":"risk-analysis","name":"risk-analysis","description":"Analyze synthetic risk scenarios","tags":["risk","synthetic"]}]}
@app.get("/")
def status()->dict[str,str]: return {"status":"ready","agent_card":"/.well-known/agent-card.json","message_endpoint":"/a2a"}
@app.get("/.well-known/agent-card.json")
def agent_card()->dict[str,Any]: return CARD
def extract_text(response:Any)->str:return "\n".join(getattr(p,"text","") for i in response.output if getattr(i,"type",None)=="message" for p in getattr(i,"content",[])).strip()
def handle_message(payload:dict[str,Any])->dict[str,Any]:
    """Learner task: validate JSON-RPC/tenant, call Foundry, return result."""
    # LAB PLACEHOLDER 5: Replace this line with the Task 5 sample.
    raise NotImplementedError("Complete handle_message in Task 5")
@app.post("/a2a")
def a2a(payload:dict[str,Any])->dict[str,Any]:
    try:return handle_message(payload)
    except ValueError as exc:raise HTTPException(status_code=400,detail=str(exc)) from exc