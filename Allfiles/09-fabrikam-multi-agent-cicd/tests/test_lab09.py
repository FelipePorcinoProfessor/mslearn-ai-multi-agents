from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

import yaml
import httpx
from azure.core.credentials import AccessToken

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dashboard.app import render_page
from scripts.apply_canary_decision import select_traffic
from scripts.capture_release_set import bind_deployments
from scripts.export_release import MODEL_POLICY, build_release_set, load_definitions
from scripts.release_manifest import validate_verified_manifest
from src.responses_client import _agent_urls, invoke_responses_endpoint, version_endpoint
from src.deployment_graph import rollback_closure
from src.versioning import parse_version


class HostedManifestTests(unittest.TestCase):
    def test_only_dashboard_is_a_container_app(self) -> None:
        config = yaml.safe_load((ROOT / "azure.yaml").read_text(encoding="utf-8"))
        services = config["services"]
        self.assertEqual(
            [name for name, service in services.items() if service.get("host") == "containerapp"],
            ["dashboard"],
        )
        for name in ("scanner", "reviewer", "orchestrator"):
            service = services[name]
            self.assertEqual(service["host"], "azure.ai.agent")
            self.assertEqual(service["kind"], "hosted")
            self.assertEqual(service["codeConfiguration"]["runtime"], "python_3_13")
            self.assertEqual(service["protocols"], [{"protocol": "responses", "version": "2.0.0"}])
            self.assertNotIn("docker", service)

    def test_exact_model_policy_and_release_shape(self) -> None:
        definitions = load_definitions(ROOT / "agents")
        release_set, contracts = build_release_set(
            definitions,
            source_commit="abc123",
            environment="development",
            status="validated",
        )
        self.assertEqual(release_set["model"], MODEL_POLICY)
        self.assertTrue(release_set["reviewed_release_id"].startswith("reviewed-"))
        self.assertEqual(set(release_set["agents"]), {"scanner", "reviewer", "orchestrator"})
        self.assertTrue(release_set["contract_digest"].startswith("sha256:"))
        self.assertEqual(release_set["evaluation"]["dataset_version"], "1")
        self.assertEqual(set(contracts), set(release_set["agents"]))
        for metadata in release_set["agents"].values():
            parse_version(metadata["logical_version"])
            self.assertEqual(metadata["hosted_manifest"]["protocol_version"], "2.0.0")

    def test_binding_requires_all_immutable_outputs(self) -> None:
        release_set, _ = build_release_set(
            load_definitions(ROOT / "agents"),
            source_commit="abc123",
            environment="development",
            status="validated",
        )
        values = {}
        for service in ("scanner", "reviewer", "orchestrator"):
            name = f"fabrikam-{service}"
            values[f"AGENT_{service.upper()}_NAME"] = name
            values[f"AGENT_{service.upper()}_VERSION"] = "7"
            values[f"AGENT_{service.upper()}_RESPONSES_ENDPOINT"] = (
                f"https://account.services.ai.azure.com/api/projects/project/agents/{name}"
                "/endpoint/protocols/openai/responses"
            )
        bound = bind_deployments(release_set, values)
        self.assertTrue(bound["release_set_id"].startswith("development-"))
        self.assertEqual(bound["status"], "deployed")
        self.assertEqual(
            bound["dashboard"]["target_orchestrator"],
            bound["agents"]["orchestrator"]["hosted_deployment"],
        )
        self.assertTrue(
            bound["agents"]["orchestrator"]["hosted_deployment"]["version_endpoint"].endswith(
                "/versions/7"
            )
        )

    def test_version_specific_session_urls(self) -> None:
        endpoint = (
            "https://account.services.ai.azure.com/api/projects/project/agents/scanner"
            "/endpoint/protocols/openai/responses"
        )
        session_url, responses_url = _agent_urls(endpoint, "scanner")
        self.assertIn("/agents/scanner/endpoint/sessions", session_url)
        self.assertIn("api-version=v1", session_url)
        self.assertIn("/agents/scanner/endpoint/protocols/openai/responses", responses_url)
        self.assertTrue(version_endpoint(endpoint, "scanner", "9").endswith("/versions/9"))


class DeliveryBoundaryTests(unittest.TestCase):
    def test_canary_uses_persisted_stable_revision(self) -> None:
        revisions = [
            {"name": "dashboard--stable", "fqdn": "stable.example.test"},
            {"name": "dashboard--candidate", "fqdn": "candidate.example.test"},
        ]
        plan = select_traffic(revisions, stable_revision="dashboard--stable", strategy="canary")
        self.assertEqual(plan["weights"], {"dashboard--stable": 75, "dashboard--candidate": 25})
        with self.assertRaises(ValueError):
            select_traffic(revisions, stable_revision=None, strategy="canary")
        initial = select_traffic(
            revisions,
            stable_revision=None,
            strategy="canary",
            initial_revision="dashboard--candidate",
        )
        self.assertEqual(initial["weights"], {"dashboard--stable": 0, "dashboard--candidate": 100})

    def test_dashboard_identifies_exact_target(self) -> None:
        environment = {
            "RELEASE_SET_ID": "development-1234",
            "CONTAINER_APP_REVISION": "dashboard--candidate",
            "ORCHESTRATOR_AGENT_NAME": "fabrikam-review-orchestrator",
            "ORCHESTRATOR_AGENT_VERSION": "7",
            "ORCHESTRATOR_RESPONSES_ENDPOINT": "https://example.test/versions/7/responses",
        }
        with patch.dict(os.environ, environment, clear=False):
            page = render_page(host="candidate---dashboard.example.test")
        for value in environment.values():
            self.assertIn(value, page)
        self.assertIn("75/25", page)
        self.assertIn("label URLs", page)
        self.assertIn("CANDIDATE", page)
        with patch.dict(os.environ, environment, clear=False):
            promoted = render_page(host="stable---dashboard.example.test")
        self.assertIn("STABLE", promoted)

    def test_verified_manifest_validation_fails_closed(self) -> None:
        release_set, _ = build_release_set(
            load_definitions(ROOT / "agents"),
            source_commit="abc123",
            environment="development",
            status="validated",
        )
        values = {}
        for service in ("scanner", "reviewer", "orchestrator"):
            name = f"fabrikam-{service}"
            values[f"AGENT_{service.upper()}_NAME"] = name
            values[f"AGENT_{service.upper()}_VERSION"] = "7"
            values[f"AGENT_{service.upper()}_RESPONSES_ENDPOINT"] = (
                f"https://account.services.ai.azure.com/api/projects/project/agents/{name}"
                "/endpoint/protocols/openai/responses"
            )
        manifest = bind_deployments(release_set, values)
        manifest["status"] = "verified"
        manifest["dashboard"].update(
            {
                "app_name": "dashboard",
                "revision": "dashboard--abc",
                "release_channel": "stable",
                "stable_label_url": "https://stable---dashboard.example.test",
            }
        )
        validate_verified_manifest(manifest, environment="development", app_name="dashboard")
        manifest["environment"] = "production"
        with self.assertRaises(ValueError):
            validate_verified_manifest(manifest, environment="development", app_name="dashboard")

    def test_reverse_dependency_rollback_closure(self) -> None:
        graph = {
            "scanner": {"depends_on": {}},
            "reviewer": {"depends_on": {}},
            "orchestrator": {"depends_on": {"scanner": ">=1,<2", "reviewer": ">=1,<2"}},
        }
        self.assertEqual(rollback_closure(graph, "scanner"), ["orchestrator", "scanner"])


class VersionBoundInvocationTests(unittest.IsolatedAsyncioTestCase):
    async def test_session_pins_and_verifies_immutable_version(self) -> None:
        requests: list[httpx.Request] = []

        async def handler(request: httpx.Request) -> httpx.Response:
            requests.append(request)
            if request.url.path.endswith("/endpoint/sessions"):
                return httpx.Response(
                    200,
                    json={
                        "agent_session_id": "session-123",
                        "version_indicator": {
                            "type": "version_ref",
                            "agent_version": "7",
                        },
                    },
                )
            return httpx.Response(
                200,
                headers={"x-ms-agent-version": "7"},
                json={"id": "resp-123", "output_text": "ready"},
            )

        class Credential:
            async def get_token(self, *_scopes: str) -> AccessToken:
                return AccessToken("token", 4_000_000_000)

        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            evidence = await invoke_responses_endpoint(
                "https://account.services.ai.azure.com/api/projects/project/agents/orchestrator"
                "/endpoint/protocols/openai/responses",
                "orchestrator",
                "7",
                "hello",
                credential=Credential(),
                client=client,
            )

        self.assertEqual(evidence.served_version, "7")
        self.assertEqual(evidence.agent_session_id, "session-123")
        self.assertEqual(len(requests), 2)
        self.assertIn('"agent_version":"7"', requests[0].content.decode())
        self.assertIn('"agent_session_id":"session-123"', requests[1].content.decode())


if __name__ == "__main__":
    unittest.main()
