"""
Unit tests for AI Reasoning Layer (Prompt 3).
All Gemini API calls are mocked, allowing tests to run completely offline without API keys or quota consumption.
"""
import json
import pytest
from unittest.mock import MagicMock, patch

from app.main import run_cluster_investigation, InvestigationRequest
from app.ai.prompt_builder import PromptBuilder
from app.ai.gemini_client import GeminiClient
from app.ai.root_cause_analyzer import RootCauseAnalyzer
from app.schemas.diagnosis import DiagnosisResponse


# ---------------------------------------------------------------------------
# 1. PromptBuilder Tests
# ---------------------------------------------------------------------------

def test_prompt_builder_structure():
    evidence = {
        "pods": {
            "problematic_pods": [
                {
                    "name": "payment-api",
                    "namespace": "default",
                    "status": "CrashLoopBackOff",
                    "restart_count": 5
                }
            ]
        },
        "logs": {
            "collected_logs": [
                {
                    "pod": "payment-api",
                    "relevant_lines": ["FATAL: Connection refused to postgres://db.internal:5432"]
                }
            ]
        },
        "events": {
            "events": [
                {"type": "Warning", "reason": "BackOff", "message": "Back-off restarting failed container"}
            ]
        },
        "deployments": {"deployments": []},
        "network": {"services": []}
    }

    prompt = PromptBuilder.build_troubleshooting_prompt(evidence)
    assert "Senior Kubernetes Site Reliability Engineer" in prompt
    assert "payment-api" in prompt
    assert "CrashLoopBackOff" in prompt
    assert "Connection refused" in prompt
    assert "Response Schema" in prompt


# ---------------------------------------------------------------------------
# 2. GeminiClient Tests (HTTPX Mocking & Retries)
# ---------------------------------------------------------------------------

def test_gemini_client_missing_key():
    client = GeminiClient(api_key="")
    res = client.generate_content("test prompt")
    assert res["success"] is False
    assert "not configured" in res["error"].lower()


@patch("httpx.Client.post")
def test_gemini_client_success(mock_post):
    sample_ai_json = {
        "root_cause": "Database connection refused",
        "explanation": "The pod failed because postgres is unreachable.",
        "supporting_evidence": [
            {"source": "logs", "resource": "payment-api", "detail": "Connection refused"}
        ],
        "alternative_causes": [],
        "suggested_fix": "Verify Postgres service is running.",
        "kubectl_commands": [
            {"command": "kubectl get svc postgres", "purpose": "Check service", "risk": "read-only"}
        ],
        "yaml_proposal": None,
        "prevention_recommendations": ["Add retry logic to db connection"],
        "confidence": 95,
        "confidence_level": "high",
        "evidence_gaps": []
    }

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "candidates": [
            {"content": {"parts": [{"text": json.dumps(sample_ai_json)}]}}
        ]
    }
    mock_post.return_value = mock_resp

    client = GeminiClient(api_key="test-api-key")
    res = client.generate_content("test prompt")

    assert res["success"] is True
    assert res["data"]["root_cause"] == "Database connection refused"
    assert res["data"]["confidence"] == 95


def test_clean_json_response_markdown_fences():
    raw_markdown = "```json\n{\"root_cause\": \"OOMKilled\"}\n```"
    cleaned = GeminiClient.clean_json_response(raw_markdown)
    assert cleaned == '{"root_cause": "OOMKilled"}'


@patch("httpx.Client.post")
def test_gemini_client_non_retryable_401(mock_post):
    mock_resp = MagicMock()
    mock_resp.status_code = 401
    mock_resp.text = "API key not valid"
    mock_post.return_value = mock_resp

    client = GeminiClient(api_key="invalid-key", max_retries=2)
    res = client.generate_content("test prompt")

    assert res["success"] is False
    assert "HTTP 401" in res["error"]
    assert mock_post.call_count == 1  # Should not retry 401!


# ---------------------------------------------------------------------------
# 3. RootCauseAnalyzer Tests
# ---------------------------------------------------------------------------

def test_root_cause_analyzer_healthy_cluster_bypass():
    """If cluster has zero problematic pods/deployments/services, do not call Gemini."""
    healthy_evidence = {
        "pods": {"healthy": True, "total_pods": 5, "problematic_pods": []},
        "logs": {"collected_logs": []},
        "events": {"events": []},
        "deployments": {"healthy": True, "deployments": []},
        "network": {"healthy": True, "services": []}
    }

    mock_gemini = MagicMock()
    analyzer = RootCauseAnalyzer(client=mock_gemini)
    diagnosis = analyzer.analyze(healthy_evidence)

    assert "No active Kubernetes failures" in diagnosis["root_cause"]
    assert diagnosis["confidence"] == 100
    assert diagnosis["confidence_level"] == "high"
    assert mock_gemini.generate_content.call_count == 0  # Zero API calls!


def test_root_cause_analyzer_failing_cluster():
    failing_evidence = {
        "pods": {
            "healthy": False,
            "problematic_pods": [{"name": "broken-pod", "status": "CrashLoopBackOff"}]
        },
        "logs": {"collected_logs": []},
        "events": {"events": []},
        "deployments": {"deployments": []},
        "network": {"services": []}
    }

    mock_gemini = MagicMock()
    mock_gemini.generate_content.return_value = {
        "success": True,
        "data": {
            "root_cause": "Container crashed due to missing configuration",
            "explanation": "Container exits immediately after start.",
            "supporting_evidence": [
                {"source": "pods", "resource": "broken-pod", "detail": "CrashLoopBackOff"}
            ],
            "alternative_causes": [],
            "suggested_fix": "Add configuration environment variables",
            "kubectl_commands": [
                {"command": "kubectl logs broken-pod", "purpose": "Check error", "risk": "read-only"}
            ],
            "yaml_proposal": None,
            "prevention_recommendations": ["Validate config on startup"],
            "confidence": 88,
            "confidence_level": "high",
            "evidence_gaps": []
        }
    }

    analyzer = RootCauseAnalyzer(client=mock_gemini)
    diagnosis = analyzer.analyze(failing_evidence)

    assert diagnosis["root_cause"] == "Container crashed due to missing configuration"
    assert diagnosis["confidence"] == 88
    assert mock_gemini.generate_content.call_count == 1


# ---------------------------------------------------------------------------
# 4. POST /investigate Endpoint Integration
# ---------------------------------------------------------------------------

@patch("app.main.k8s_investigation_service.run_investigation")
@patch("app.main.root_cause_analyzer.analyze")
def test_investigate_with_diagnosis(mock_analyze, mock_investigate):
    mock_investigate.return_value = {
        "status": "success",
        "cluster_context": "kind-kubevora",
        "namespace": "default",
        "started_at": "2026-10-25T10:00:00Z",
        "completed_at": "2026-10-25T10:00:02Z",
        "duration_seconds": 2.0,
        "investigation": {
            "pods": {"problematic_pods": [{"name": "app-1", "status": "OOMKilled"}]},
            "logs": {"collected_logs": []},
            "events": {"events": []},
            "deployments": {"deployments": []},
            "network": {"services": []}
        },
        "component_status": {"pods": "success"},
        "errors": []
    }

    mock_analyze.return_value = {
        "root_cause": "Out of memory error (OOMKilled)",
        "explanation": "Container exceeded allocated memory limit.",
        "supporting_evidence": [{"source": "pods", "resource": "app-1", "detail": "OOMKilled"}],
        "alternative_causes": [],
        "suggested_fix": "Increase memory limits in deployment spec.",
        "kubectl_commands": [],
        "yaml_proposal": "limits:\n  memory: 512Mi",
        "prevention_recommendations": [],
        "confidence": 96,
        "confidence_level": "high",
        "evidence_gaps": []
    }

    req = InvestigationRequest(namespace="default", include_logs=True)
    res = run_cluster_investigation(req)

    assert res["status"] == "success"
    assert "investigation" in res
    assert "diagnosis" in res
    assert res["diagnosis"]["root_cause"] == "Out of memory error (OOMKilled)"
    assert res["diagnosis"]["confidence"] == 96
