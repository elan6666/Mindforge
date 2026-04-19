import json

import pytest
from fastapi.testclient import TestClient

from app.backend.core.config import clear_settings_cache
from app.backend.services.coordinator_selection_service import (
    clear_coordinator_selection_service_cache,
)
from app.backend.services.approval_service import clear_approval_service_cache
from app.backend.services.history_service import clear_history_service_cache
from app.backend.services.model_registry_service import clear_model_registry_service_cache
from app.backend.services.model_routing_service import clear_model_routing_service_cache
from app.backend.services.rule_template_service import clear_rule_template_service_cache
from app.backend.main import create_app
from app.backend.services.task_service import clear_task_service_cache


@pytest.fixture()
def isolated_model_control_storage(tmp_path, monkeypatch):
    control_dir = tmp_path / "model_control"
    control_dir.mkdir(parents=True, exist_ok=True)
    overrides_path = control_dir / "model_overrides.json"
    templates_path = control_dir / "rule_templates.json"
    overrides_path.write_text('{"models": {}}', encoding="utf-8")
    templates_path.write_text(json.dumps({"templates": []}, indent=2), encoding="utf-8")

    from app.backend.services import model_loader, rule_template_loader

    monkeypatch.setattr(model_loader, "MODEL_CONTROL_DIR", control_dir)
    monkeypatch.setattr(model_loader, "MODEL_OVERRIDES_PATH", overrides_path)
    monkeypatch.setattr(rule_template_loader, "RULE_TEMPLATES_PATH", templates_path)

    clear_model_registry_service_cache()
    clear_model_routing_service_cache()
    clear_rule_template_service_cache()
    clear_coordinator_selection_service_cache()
    clear_task_service_cache()

    yield

    clear_model_registry_service_cache()
    clear_model_routing_service_cache()
    clear_rule_template_service_cache()
    clear_coordinator_selection_service_cache()
    clear_task_service_cache()


@pytest.fixture()
def isolated_history_storage(tmp_path, monkeypatch):
    db_path = tmp_path / "mindforge-test.db"
    monkeypatch.setenv("SQLITE_DB_PATH", str(db_path))
    clear_settings_cache()
    clear_history_service_cache()
    clear_approval_service_cache()
    clear_task_service_cache()

    yield

    clear_task_service_cache()
    clear_approval_service_cache()
    clear_history_service_cache()
    clear_settings_cache()


def test_health_endpoint_returns_liveness_payload():
    client = TestClient(create_app())

    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "mindforge",
    }


def test_tasks_endpoint_returns_mock_openhands_response(isolated_history_storage):
    client = TestClient(create_app())

    response = client.post(
        "/api/tasks",
        json={"prompt": "Analyze repository structure"},
    )

    body = response.json()

    assert response.status_code == 200
    assert body["status"] == "completed"
    assert body["data"]["provider"] == "mock-openhands"
    assert body["data"]["metadata"]["resolved_preset_mode"] == "default"
    assert body["data"]["metadata"]["task_model_selection"]["model_id"] == "gpt-5.4"


def test_tasks_endpoint_returns_structured_400_for_unknown_preset(isolated_history_storage):
    client = TestClient(create_app())

    response = client.post(
        "/api/tasks",
        json={"prompt": "Analyze repository structure", "preset_mode": "bad-preset"},
    )

    body = response.json()

    assert response.status_code == 400
    assert body["status"] == "failed"
    assert "Unknown preset_mode" in body["error_message"]


def test_presets_endpoint_returns_available_presets(isolated_history_storage):
    client = TestClient(create_app())

    response = client.get("/api/presets")

    body = response.json()

    assert response.status_code == 200
    assert any(item["preset_mode"] == "code-engineering" for item in body)
    assert any(item["preset_mode"] == "paper-revision" for item in body)


def test_provider_and_model_endpoints_return_registry_data(isolated_history_storage):
    client = TestClient(create_app())

    provider_response = client.get("/api/providers")
    model_response = client.get("/api/models")

    assert provider_response.status_code == 200
    assert any(item["provider_id"] == "openai" for item in provider_response.json())

    assert model_response.status_code == 200
    assert any(item["model_id"] == "gpt-5.4" for item in model_response.json())


def test_code_engineering_tasks_endpoint_returns_orchestration_trace(isolated_history_storage):
    client = TestClient(create_app())

    response = client.post(
        "/api/tasks",
        json={
            "prompt": "Plan backend work",
            "preset_mode": "code-engineering",
            "repo_path": ".",
        },
    )

    body = response.json()

    assert response.status_code == 200
    assert body["data"]["provider"] == "multi-stage-orchestrator"
    trace = body["data"]["metadata"]["orchestration"]
    assert len(trace["stages"]) == 4
    assert trace["stages"][0]["role"] == "project-manager"
    assert trace["stages"][0]["model"] == "gpt-5.4"
    assert body["data"]["metadata"]["repo_analysis"]["status"] == "analyzed"
    assert body["data"]["metadata"]["task_model_selection"]["model_id"] == "gpt-5.4"


def test_tasks_endpoint_returns_400_for_unknown_model_override(isolated_history_storage):
    client = TestClient(create_app())

    response = client.post(
        "/api/tasks",
        json={
            "prompt": "Analyze repository structure",
            "model_override": "missing-model",
        },
    )

    body = response.json()

    assert response.status_code == 400
    assert body["status"] == "failed"
    assert "missing-model" in body["error_message"]


def test_code_engineering_api_honors_role_model_overrides(isolated_history_storage):
    client = TestClient(create_app())

    response = client.post(
        "/api/tasks",
        json={
            "prompt": "Plan backend work",
            "preset_mode": "code-engineering",
            "role_model_overrides": {"frontend": "gpt-5.4"},
        },
    )

    body = response.json()

    assert response.status_code == 200
    trace = body["data"]["metadata"]["orchestration"]
    assert trace["stages"][2]["role"] == "frontend"
    assert trace["stages"][2]["model"] == "gpt-5.4"
    assert (
        trace["stages"][2]["metadata"]["model_selection"]["selection_source"]
        == "explicit-role-override"
    )


def test_control_models_endpoint_updates_model_state(isolated_model_control_storage):
    client = TestClient(create_app())

    update_response = client.put(
        "/api/control/models/gpt-5.4",
        json={"priority": "low", "enabled": False},
    )
    models_response = client.get("/api/models")

    assert update_response.status_code == 200
    assert update_response.json()["priority"] == "low"
    assert update_response.json()["enabled"] is False
    assert any(
        item["model_id"] == "gpt-5.4"
        and item["priority"] == "low"
        and item["enabled"] is False
        for item in models_response.json()
    )


def test_rule_template_endpoints_support_crud(isolated_model_control_storage):
    client = TestClient(create_app())

    create_response = client.post(
        "/api/control/rule-templates",
        json={
            "template_id": "paper-style",
            "display_name": "Paper Style",
            "description": "Paper review template",
            "preset_mode": "paper-revision",
            "task_types": ["writing"],
            "default_coordinator_model_id": "gpt-5.4",
            "enabled": True,
            "is_default": True,
            "trigger_keywords": ["paper", "journal"],
            "assignments": [
                {
                    "role": "style-reviewer",
                    "responsibility": "Review style",
                    "model_id": "kimi-2.5",
                }
            ],
            "notes": "test template",
        },
    )
    list_response = client.get("/api/control/rule-templates")
    delete_response = client.delete("/api/control/rule-templates/paper-style")

    assert create_response.status_code == 201
    assert create_response.json()["template_id"] == "paper-style"
    assert list_response.status_code == 200
    assert any(item["template_id"] == "paper-style" for item in list_response.json())
    assert delete_response.status_code == 204


def test_tasks_endpoint_returns_rule_template_selection_metadata(
    isolated_model_control_storage,
    isolated_history_storage,
):
    client = TestClient(create_app())

    client.post(
        "/api/control/rule-templates",
        json={
            "template_id": "paper-style",
            "display_name": "Paper Style",
            "description": "Paper review template",
            "preset_mode": "paper-revision",
            "task_types": ["writing"],
            "default_coordinator_model_id": "gpt-5.4",
            "enabled": True,
            "is_default": True,
            "trigger_keywords": ["paper", "journal", "abstract"],
            "assignments": [
                {
                    "role": "style-reviewer",
                    "responsibility": "Review style",
                    "model_id": "kimi-2.5",
                }
            ],
            "notes": "test template",
        },
    )

    response = client.post(
        "/api/tasks",
        json={
            "prompt": "Please revise this journal paper abstract.",
            "preset_mode": "paper-revision",
            "task_type": "writing",
        },
    )

    body = response.json()

    assert response.status_code == 200
    assert body["data"]["metadata"]["rule_template_selection"]["template_id"] == "paper-style"
    assert (
        body["data"]["metadata"]["rule_template_selection"]["coordinator_model_id"]
        == "gpt-5.4"
    )


def test_pending_approval_can_be_approved_and_persisted(isolated_history_storage):
    client = TestClient(create_app())

    submit_response = client.post(
        "/api/tasks",
        json={
            "prompt": "Apply risky repository write",
            "preset_mode": "code-engineering",
            "metadata": {
                "requires_approval": True,
                "approval_actions": ["write files"],
            },
        },
    )

    submit_body = submit_response.json()
    task_id = submit_body["data"]["metadata"]["task_id"]

    assert submit_response.status_code == 200
    assert submit_body["status"] == "pending_approval"

    pending_response = client.get("/api/approvals/pending")
    assert pending_response.status_code == 200
    assert any(item["task_id"] == task_id for item in pending_response.json())

    approve_response = client.post(
        f"/api/approvals/{task_id}/approve",
        json={"comment": "Proceed"},
    )
    approve_body = approve_response.json()

    assert approve_response.status_code == 200
    assert approve_body["status"] == "completed"
    assert approve_body["data"]["metadata"]["approval"]["status"] == "approved"

    history_response = client.get(f"/api/history/tasks/{task_id}")
    history_body = history_response.json()

    assert history_response.status_code == 200
    assert history_body["status"] == "completed"
    assert history_body["approval"]["status"] == "approved"
    assert history_body["stages"]


def test_pending_approval_can_be_rejected(isolated_history_storage):
    client = TestClient(create_app())

    submit_response = client.post(
        "/api/tasks",
        json={
            "prompt": "Apply risky repository write",
            "metadata": {
                "requires_approval": True,
                "approval_actions": ["execute shell"],
            },
        },
    )
    task_id = submit_response.json()["data"]["metadata"]["task_id"]

    reject_response = client.post(
        f"/api/approvals/{task_id}/reject",
        json={"comment": "Stop here"},
    )
    reject_body = reject_response.json()

    assert reject_response.status_code == 200
    assert reject_body["status"] == "rejected"

    history_response = client.get("/api/history/tasks", params={"status": "rejected"})
    assert history_response.status_code == 200
    assert any(item["task_id"] == task_id for item in history_response.json())
