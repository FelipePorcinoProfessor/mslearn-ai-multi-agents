"""Adaptive decomposition starter with live Agents v2 calls."""
from __future__ import annotations
import argparse, json, logging, os, time, uuid
from pathlib import Path
from typing import Any
from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import PromptAgentDefinition
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv

LOGGER=logging.getLogger("decomposition")
load_dotenv(Path(__file__).resolve().parents[1] / ".env")
def validate_plan(plan: dict[str, Any], registry: dict[str, Any]) -> None:
    """Learner task: validate IDs, capabilities, dependencies, DAG, and final task."""
    # LAB PLACEHOLDER 1: Replace this line with the Task 1 sample.
    raise NotImplementedError("Complete validate_plan in Task 1")

def ready_tasks(tasks: list[dict[str, Any]], completed: dict[str, Any]) -> list[dict[str, Any]]:
    """Learner task: select dependency-ready tasks or identify a deadlock."""
    # LAB PLACEHOLDER 2: Replace this line with the Task 2 sample.
    raise NotImplementedError("Complete ready_tasks in Task 2")
def build_handoff(task: dict[str, Any], completed: dict[str, Any], correlation_id: str) -> dict[str, Any]:
    """Learner task: construct and size-check a context-preserving envelope."""
    # LAB PLACEHOLDER 3: Replace this line with the Task 3 sample.
    raise NotImplementedError("Complete build_handoff in Task 3")

def should_replan(result: dict[str, Any], replan_count: int) -> bool:
    """Learner task: allow one evidence-driven replan only."""
    # LAB PLACEHOLDER 4: Replace this line with the Task 4 sample.
    raise NotImplementedError("Complete should_replan in Task 4")

def response_text(response: Any) -> str:
    return "\n".join(getattr(p,"text","") for i in response.output if getattr(i,"type",None)=="message" for p in getattr(i,"content",[])).strip()

def call_agent(openai: Any, content: str) -> Any:
    return openai.responses.create(input=content)

def run(path: Path) -> dict[str, Any]:
    data=json.loads(path.read_text(encoding="utf-8")); started=time.perf_counter(); correlation_id=str(uuid.uuid4())
    project=AIProjectClient(endpoint=os.environ["FOUNDRY_PROJECT_ENDPOINT"],credential=DefaultAzureCredential()); model=os.environ["FOUNDRY_MODEL_NAME"]
    planner=project.agents.create_version(agent_name="research-planner",definition=PromptAgentDefinition(model=model,instructions=(ROOT_INSTRUCTIONS + json.dumps(data["registry"]))))
    specialists={name:project.agents.create_version(agent_name=name,definition=PromptAgentDefinition(model=model,instructions=spec["instructions"])).name for name,spec in data["registry"].items()}
    planner_openai=project.get_openai_client(agent_name=planner.name)
    specialist_clients={name:project.get_openai_client(agent_name=agent_name) for name,agent_name in specialists.items()}
    planner_response=call_agent(planner_openai,json.dumps({"query":data["query"],"complexity_hint":data["complexity_hint"]}))
    plan=json.loads(response_text(planner_response)); validate_plan(plan,data["registry"]); completed={}; handoffs=0; replan_count=0
    while len(completed)<len(plan["tasks"]):
        batch=ready_tasks(plan["tasks"],completed)
        if not batch: raise RuntimeError("Plan deadlock: no task is dependency-ready")
        for task in batch:
            envelope=build_handoff(task,completed,correlation_id); handoffs+=1
            response=call_agent(specialist_clients[task["agent"]],json.dumps(envelope)); completed[task["id"]]={"status":"success","response_id":response.id,"summary":response_text(response)}
            if should_replan(completed[task["id"]],replan_count): replan_count+=1
    return {"planner_response_id":planner_response.id,"plan":plan["tasks"],"task_count":len(plan["tasks"]),"handoff_count":handoffs,"replan_count":replan_count,"coordination_ratio":round(handoffs/max(1,len(completed)),2),"elapsed_ms":round((time.perf_counter()-started)*1000),"results":completed}
ROOT_INSTRUCTIONS=(
    "Return JSON only: {\"tasks\":[{\"id\":\"T1\",\"objective\":\"...\","
    "\"agent\":\"...\",\"depends_on\":[],\"expected_schema\":\"...\"}]}. "
    "Use only known agents and exactly one final thesis-synthesis task. If "
    "complexity_hint is simple, return exactly two tasks: one best-fit evidence "
    "task and a final synthesis task that depends on it. If complexity_hint is "
    "complex, return three through six tasks and decompose the query across "
    "relevant evidence specialists before final synthesis. Registry: "
)

def main()->None:
    p=argparse.ArgumentParser();p.add_argument("--input",type=Path,default=Path("assets/research-query.json"));a=p.parse_args();logging.basicConfig(level=logging.INFO,format="%(levelname)s %(message)s");print(json.dumps(run(a.input),indent=2))
if __name__=="__main__":main()