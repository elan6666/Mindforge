from fastapi.testclient import TestClient

from app.backend.main import create_app


def test_health_endpoint_returns_liveness_payload():
    client = TestClient(create_app())

    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "multi-agent-assistant",
    }


def test_tasks_endpoint_returns_mock_openhands_response():
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


def test_tasks_endpoint_returns_structured_400_for_unknown_preset():
    client = TestClient(create_app())

    response = client.post(
        "/api/tasks",
        json={"prompt": "Analyze repository structure", "preset_mode": "bad-preset"},
    )

    body = response.json()

    assert response.status_code == 400
    assert body["status"] == "failed"
    assert "Unknown preset_mode" in body["error_message"]


def test_presets_endpoint_returns_available_presets():
    client = TestClient(create_app())

    response = client.get("/api/presets")

    body = response.json()

    assert response.status_code == 200
    assert any(item["preset_mode"] == "code-engineering" for item in body)
    assert any(item["preset_mode"] == "paper-revision" for item in body)


def test_code_engineering_tasks_endpoint_returns_orchestration_trace():
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
    assert body["data"]["metadata"]["repo_analysis"]["status"] == "analyzed"
