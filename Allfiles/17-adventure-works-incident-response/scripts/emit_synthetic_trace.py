"""Emit a bounded synthetic success/failure cohort to Application Insights."""

from __future__ import annotations

import hashlib
import json
import os
import time
from pathlib import Path

from azure.identity import DefaultAzureCredential
from azure.monitor.opentelemetry import configure_azure_monitor
from dotenv import load_dotenv
from opentelemetry import trace
from opentelemetry.trace import SpanKind
from opentelemetry.trace.status import Status, StatusCode

PRICING_PROMPT = "Calculate the synthetic cart total from the captured catalog response."
CATALOG_RESPONSE = {"sku": "SYN-BIKE-01", "unit_price": 1200.0, "currency": "USD", "quantity": 1}
PAYMENT_RESPONSE = {"authorization": "SYN-AUTH-01", "approved": True}


def emit_checkout(tracer: trace.Tracer, synthetic_id: str, fail_pricing: bool) -> None:
    with tracer.start_as_current_span(
        "POST /synthetic/checkout", kind=SpanKind.SERVER
    ) as root:
        root.set_attribute("synthetic.case_id", synthetic_id)
        root.set_attribute("gen_ai.agent.name", "aw-checkout-orchestrator")
        root.set_attribute("deployment.environment", "lab")
        root.set_attribute("agent.configuration.version", "checkout-flow-v1")
        with tracer.start_as_current_span("pricing_agent.calculate_total") as pricing:
            pricing.set_attribute("gen_ai.request.model", "synthetic-pricing-v2" if fail_pricing else "synthetic-pricing-v1")
            pricing.set_attribute("agent.configuration.version", "checkout-flow-v1")
            pricing.set_attribute("gen_ai.prompt.template", PRICING_PROMPT)
            pricing.set_attribute("gen_ai.prompt.hash", hashlib.sha256(PRICING_PROMPT.encode()).hexdigest())
            pricing.set_attribute("tool.name", "catalog_lookup")
            pricing.set_attribute("tool.mock_id", "catalog-response-syn-01")
            pricing.set_attribute("tool.mock_response", json.dumps(CATALOG_RESPONSE, sort_keys=True))
            pricing.set_attribute("tool.response.success", True)
            if fail_pricing:
                time.sleep(0.35)
                pricing.set_attribute("incident.error.type", "SyntheticPriceFormatError")
                pricing.set_status(Status(StatusCode.ERROR, "synthetic formatted price rejected"))
                root.set_status(Status(StatusCode.ERROR, "synthetic checkout failed"))
            else:
                time.sleep(0.05)
        with tracer.start_as_current_span("payment_agent.authorize") as payment:
            payment.set_attribute("tool.name", "payment_gateway")
            payment.set_attribute("tool.mock_id", "payment-response-syn-01")
            payment.set_attribute("tool.mock_response", json.dumps(PAYMENT_RESPONSE, sort_keys=True))
            payment.set_attribute("tool.response.success", True)
            if fail_pricing:
                payment.set_status(Status(StatusCode.ERROR, "synthetic invalid amount"))


def main() -> None:
    load_dotenv(Path(__file__).resolve().parents[1] / ".env")
    credential = DefaultAzureCredential(exclude_interactive_browser_credential=True)
    configure_azure_monitor(
        connection_string=os.environ["APPLICATIONINSIGHTS_CONNECTION_STRING"],
        credential=credential,
        sampling_ratio=1.0,
    )
    tracer = trace.get_tracer("adventure-works.synthetic-incident")
    emit_checkout(tracer, "SYN-SUCCESS-01", False)
    emit_checkout(tracer, "SYN-SUCCESS-02", False)
    emit_checkout(tracer, "SYN-FAILURE-01", True)
    emit_checkout(tracer, "SYN-FAILURE-02", True)
    if not trace.get_tracer_provider().force_flush(timeout_millis=30_000):
        raise RuntimeError("Timed out while flushing synthetic telemetry")
    print("Emitted and flushed four bounded synthetic traces. Allow several minutes for ingestion.")


if __name__ == "__main__":
    main()