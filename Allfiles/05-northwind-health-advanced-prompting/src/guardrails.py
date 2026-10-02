"""Learner-owned deterministic guardrail interventions."""
from __future__ import annotations
import re
from typing import Any

INJECTION_PATTERNS = (
    r"ignore\s+(?:previous|prior|all)\s+instructions",
    r"(?:system|developer)\s+(?:message|prompt|override)",
    r"disregard\s+(?:previous|prior|all)",
    r"reveal\s+(?:the\s+)?system\s+prompt",
    r"skip\s+(?:safety|contraindication)\s+checks",
)

def _contains_injection(value:str)->bool:
    return any(re.search(pattern,value,flags=re.IGNORECASE) for pattern in INJECTION_PATTERNS)

def guard_input(case:dict[str,Any])->dict[str,Any]:
    """Validate and delimit untrusted input; fail closed on injection signals."""
    # LAB PLACEHOLDER 1: Replace this line with the Task 1 sample.
    raise NotImplementedError("Complete guard_input in Task 1")
def guard_tool_call(name:str,arguments:dict[str,Any])->dict[str,Any]:
    """Enforce tool allow-list, parameter schema, content, and ranges."""
    # LAB PLACEHOLDER 2: Replace this line with the Task 2 sample.
    raise NotImplementedError("Complete guard_tool_call in Task 2")
def guard_tool_response(name:str,response:dict[str,Any])->dict[str,Any]:
    """Enforce response schema, redaction, scanning, and value ranges."""
    # LAB PLACEHOLDER 3: Replace this line with the Task 3 sample.
    raise NotImplementedError("Complete guard_tool_response in Task 3")
def guard_output(text:str)->dict[str,Any]:
    """Validate advisory language, evidence gaps, escalation, and output schema."""
    # LAB PLACEHOLDER 4: Replace this line with the Task 4 sample.
    raise NotImplementedError("Complete guard_output in Task 4")