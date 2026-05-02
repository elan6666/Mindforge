import json

import pytest
from fastapi.testclient import TestClient

from app.backend.core.config import clear_settings_cache
from app.backend.services.coordinator_selection_service import (
    clear_coordinator_selection_service_cache,
)
from app.backend.services.academic_context_service import clear_academic_context_service_cache
from app.backend.services.approval_service import clear_approval_service_cache
from app.backend.services.artifact_service import clear_artifact_service_cache
from app.backend.services.github_context_service import clear_github_context_service_cache
from app.backend.services.file_context_service import clear_file_context_service_cache
from app.backend.services.history_service import clear_history_service_cache
from app.backend.services.mcp_service import clear_mcp_service_cache
from app.backend.services.model_registry_service import clear_model_registry_service_cache
from app.backend.services.model_routing_service import clear_model_routing_service_cache
from app.backend.services.project_space_service import clear_project_space_service_cache
from app.backend.services.rule_template_service import clear_rule_template_service_cache
from app.backend.services.skill_registry_service import clear_skill_registry_service_cache
from app.backend.main import create_app
from app.backend.services.task_service import clear_task_service_cache


@pytest.fixture()
def isolated_model_control_storage(tmp_path, monkeypatch):
    control_dir = tmp_path / "model_control"
    control_dir.mkdir(parents=True, exist_ok=True)
    overrides_path = control_dir / "model_overrides.json"
    provider_overrides_path = control_dir / "provider_overrides.json"
    provider_secrets_path = control_dir / "provider_secrets.json"
    templates_path = control_dir / "rule_templates.json"
    overrides_path.write_text('{"models": {}}', encoding="utf-8")
    provider_overrides_path.write_text('{"providers": {}}', encoding="utf-8")
    provider_secrets_path.write_text('{"api_keys": {}}', encoding="utf-8")
    templates_path.write_text(json.dumps({"templates": []}, indent=2), encoding="utf-8")

    from app.backend.services import model_loader, rule_template_loader

    monkeypatch.setattr(model_loader, "MODEL_CONTROL_DIR", control_dir)
    monkeypatch.setattr(model_loader, "MODEL_OVERRIDES_PATH", overrides_path)
    monkeypatch.setattr(model_loader, "PROVIDER_OVERRIDES_PATH", provider_overrides_path)
    monkeypatch.setattr(model_loader, "PROVIDER_SECRETS_PATH", provider_secrets_path)
    monkeypatch.setattr(rule_template_loader, "RULE_TEMPLATES_PATH", templates_path)

    clear_model_registry_service_cache()
    clear_model_routing_service_cache()
    clear_rule_template_service_cache()
    clear_coordinator_selection_service_cache()
    clear_academic_context_service_cache()
    clear_task_service_cache()

    yield

    clear_model_registry_service_cache()
    clear_model_routing_service_cache()
    clear_rule_template_service_cache()
    clear_coordinator_selection_service_cache()
    clear_academic_context_service_cache()
    clear_task_service_cache()


@pytest.fixture()
def isolated_history_storage(tmp_path, monkeypatch):
    db_path = tmp_path / "mindforge-test.db"
    file_storage_path = tmp_path / "files"
    artifact_storage_path = tmp_path / "artifacts"
    mcp_registry_path = tmp_path / "mcp_servers.json"
    project_spaces_path = tmp_path / "project_spaces.json"
    skill_settings_path = tmp_path / "skill_settings.json"
    monkeypatch.setenv("SQLITE_DB_PATH", str(db_path))
    monkeypatch.setenv("FILE_STORAGE_PATH", str(file_storage_path))
    monkeypatch.setenv("ARTIFACT_STORAGE_PATH", str(artifact_storage_path))
    monkeypatch.setenv("MCP_REGISTRY_PATH", str(mcp_registry_path))
    monkeypatch.setenv("PROJECT_SPACES_PATH", str(project_spaces_path))
    monkeypatch.setenv("SKILL_SETTINGS_PATH", str(skill_settings_path))
    monkeypatch.setenv("OPENHANDS_MODE", "mock")
    clear_settings_cache()
    clear_history_service_cache()
    clear_file_context_service_cache()
    clear_artifact_service_cache()
    clear_mcp_service_cache()
    clear_project_space_service_cache()
    clear_skill_registry_service_cache()
    clear_approval_service_cache()
    clear_github_context_service_cache()
    clear_academic_context_service_cache()
    clear_task_service_cache()

    yield

    clear_task_service_cache()
    clear_academic_context_service_cache()
    clear_approval_service_cache()
    clear_file_context_service_cache()
    clear_artifact_service_cache()
    clear_mcp_service_cache()
    clear_project_space_service_cache()
    clear_skill_registry_service_cache()
    clear_history_service_cache()
    clear_github_context_service_cache()
    clear_settings_cache()


@pytest.fixture()
def mocked_github_api(monkeypatch):
    class DummyResponse:
        def __init__(self, status_code, payload):
            self.status_code = status_code
            self._payload = payload

        def json(self):
            return self._payload

    def fake_get(url, headers=None, timeout=None):
        if url.endswith("/repos/openai/openai-python"):
            return DummyResponse(
                200,
                {
                    "full_name": "openai/openai-python",
                    "description": "OpenAI Python SDK",
                    "html_url": "https://github.com/openai/openai-python",
                    "default_branch": "main",
                    "language": "Python",
                    "stargazers_count": 100,
                    "forks_count": 50,
                    "open_issues_count": 25,
                    "visibility": "public",
                },
            )
        if url.endswith("/repos/openai/openai-python/issues/123"):
            return DummyResponse(
                200,
                {
                    "number": 123,
                    "title": "Bug report",
                    "state": "open",
                    "html_url": "https://github.com/openai/openai-python/issues/123",
                    "user": {"login": "octocat"},
                    "labels": [{"name": "bug"}],
                    "comments": 4,
                    "body": "Issue body for testing",
                },
            )
        if url.endswith("/repos/openai/openai-python/pulls/9"):
            return DummyResponse(
                200,
                {
                    "number": 9,
                    "title": "Fix bug",
                    "state": "open",
                    "html_url": "https://github.com/openai/openai-python/pull/9",
                    "user": {"login": "octocat"},
                    "labels": [{"name": "enhancement"}],
                    "comments": 2,
                    "review_comments": 1,
                    "draft": False,
                    "merged": False,
                    "head": {"ref": "feature-branch"},
                    "base": {"ref": "main"},
                    "body": "PR body for testing",
                },
            )
        return DummyResponse(404, {"message": "Not Found"})

    monkeypatch.setattr(
        "app.backend.services.github_context_service.requests.get",
        fake_get,
    )
    clear_github_context_service_cache()
    clear_task_service_cache()
    yield
    clear_task_service_cache()
    clear_github_context_service_cache()


@pytest.fixture()
def mocked_academic_pages(monkeypatch):
    class DummyResponse:
        status_code = 200
        text = ""

        def __init__(self, text):
            self.text = text

        def raise_for_status(self):
            return None

    def fake_get(url, timeout=None, headers=None):
        if "guidelines" in url:
            return DummyResponse(
                "<html><title>Author Guidelines</title><body>Use structured abstracts and concise language.</body></html>"
            )
        return DummyResponse(
            "<html><title>Reference Paper</title><body>The paper foregrounds contributions before method details.</body></html>"
        )

    monkeypatch.setattr(
        "app.backend.services.academic_context_service.requests.get",
        fake_get,
    )
    clear_academic_context_service_cache()
    clear_task_service_cache()
    yield
    clear_task_service_cache()
    clear_academic_context_service_cache()


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


def test_tasks_endpoint_routes_chat_to_adapter_without_local_preset_answer(
    isolated_history_storage,
):
    client = TestClient(create_app())

    response = client.post(
        "/api/tasks",
        json={
            "prompt": "你能做什么",
            "conversation_id": "conversation-chat-1",
            "conversation_history": [
                {"role": "user", "content": "hi"},
                {
                    "role": "assistant",
                    "content": "你好！我是 Mindforge。",
                },
            ],
        },
    )

    body = response.json()

    assert response.status_code == 200
    assert body["data"]["provider"] == "mock-openhands"
    assert body["data"]["metadata"]["resolved_preset_mode"] == "default"
    assert "你能做什么" in body["data"]["output"]
    assert "mindforge-intake" not in body["data"]["provider"]


def test_tasks_endpoint_persists_composer_metadata_to_history(
    isolated_history_storage,
    monkeypatch,
):
    client = TestClient(create_app())

    class FakeSearchResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "Heading": "Uploaded notes",
                "AbstractText": "Search context for uploaded notes.",
                "AbstractURL": "https://example.test/notes",
                "RelatedTopics": [],
            }

    monkeypatch.setattr(
        "app.backend.services.task_service.requests.get",
        lambda *args, **kwargs: FakeSearchResponse(),
    )

    response = client.post(
        "/api/tasks",
        json={
            "prompt": "Use attached context without prompt stuffing",
            "attachments": [
                {
                    "id": "upload-1",
                    "name": "notes.txt",
                    "mime_type": "text/plain",
                    "size_bytes": 42,
                    "excerpt": "Important uploaded notes",
                    "metadata": {"source": "composer", "line_count": 2},
                }
            ],
            "tool_flags": {"deep_analysis": True},
            "web_search": True,
            "canvas": True,
        },
    )

    body = response.json()
    task_id = body["data"]["metadata"]["task_id"]

    assert response.status_code == 200
    assert body["data"]["metadata"]["attachments"][0]["text_excerpt"] == (
        "Important uploaded notes"
    )
    assert body["data"]["metadata"]["tool_flags"]["web_search"] is True
    assert body["data"]["metadata"]["tool_flags"]["deep_analysis"] is True
    assert body["data"]["metadata"]["tool_flags"]["canvas"] is True
    assert body["data"]["metadata"]["tool_context"]["web_search"]["status"] == "fetched"
    assert body["data"]["metadata"]["canvas_artifacts"][0]["kind"] == "markdown"
    assert body["data"]["metadata"]["task_model_selection"]["model_id"] == "gpt-5.4"

    history_response = client.get(f"/api/history/tasks/{task_id}")
    history_body = history_response.json()

    assert history_response.status_code == 200
    assert history_body["metadata"]["attachments"][0]["metadata"]["source"] == "composer"
    assert history_body["metadata"]["tool_flags"]["web_search"] is True
    assert history_body["metadata"]["tool_flags"]["canvas"] is True
    assert history_body["metadata"]["tool_context"]["web_search"]["results"][0][
        "title"
    ] == "Uploaded notes"
    assert history_body["metadata"]["canvas_artifacts"][0]["editable"] is True
    assert history_body["metadata"]["task_model_selection"]["model_id"] == "gpt-5.4"

    artifact_id = history_body["metadata"]["canvas_artifacts"][0]["artifact_id"]
    update_response = client.patch(
        f"/api/history/tasks/{task_id}/canvas-artifacts/{artifact_id}",
        json={"title": "Edited canvas", "content": "Edited artifact content"},
    )
    update_body = update_response.json()

    assert update_response.status_code == 200
    assert update_body["metadata"]["canvas_artifacts"][0]["title"] == "Edited canvas"
    assert update_body["metadata"]["canvas_artifacts"][0]["content"] == (
        "Edited artifact content"
    )
    assert update_body["metadata"]["canvas_artifacts"][0]["updated_at"]


def test_files_endpoint_parses_upload_and_task_retrieves_chunks(
    isolated_history_storage,
):
    client = TestClient(create_app())

    upload_response = client.post(
        "/api/files",
        files={
            "file": (
                "research-notes.md",
                b"Mindforge file retrieval should cite parsed chunks for uploaded notes.",
                "text/markdown",
            )
        },
    )
    upload_body = upload_response.json()

    assert upload_response.status_code == 201
    assert upload_body["status"] == "parsed"
    assert upload_body["parser"] == "plain-text"
    assert upload_body["chunk_count"] == 1
    assert "raw_path" not in upload_body["metadata"]

    task_response = client.post(
        "/api/tasks",
        json={
            "prompt": "Summarize the uploaded retrieval notes.",
            "attachments": [
                {
                    "file_id": upload_body["file_id"],
                    "name": upload_body["name"],
                    "mime_type": upload_body["mime_type"],
                    "size_bytes": upload_body["size_bytes"],
                    "parsed_status": upload_body["status"],
                    "chunk_count": upload_body["chunk_count"],
                }
            ],
        },
    )
    task_body = task_response.json()

    assert task_response.status_code == 200
    file_context = task_body["data"]["metadata"]["file_context"]
    assert file_context["status"] == "retrieved"
    assert file_context["files"][0]["file_id"] == upload_body["file_id"]
    assert "raw_path" not in file_context["files"][0]["metadata"]
    assert "parsed chunks" in file_context["chunks"][0]["text"]
    assert "Uploaded file context:" in task_body["data"]["output"]


def test_files_endpoint_lists_and_deletes_uploads(isolated_history_storage):
    client = TestClient(create_app())

    upload_response = client.post(
        "/api/files",
        files={"file": ("notes.txt", b"delete me", "text/plain")},
    )
    file_id = upload_response.json()["file_id"]

    list_response = client.get("/api/files")
    delete_response = client.delete(f"/api/files/{file_id}")
    after_delete_response = client.get(f"/api/files/{file_id}")

    assert upload_response.status_code == 201
    assert any(item["file_id"] == file_id for item in list_response.json())
    assert delete_response.status_code == 204
    assert after_delete_response.status_code == 404


def test_artifacts_endpoint_exports_downloadable_documents(isolated_history_storage):
    client = TestClient(create_app())

    created = []
    for format_name in ["md", "tex", "docx", "pdf"]:
        response = client.post(
            "/api/artifacts/export",
            json={
                "title": "Mindforge report",
                "content": "# Summary\n- verified export",
                "format": format_name,
            },
        )
        body = response.json()

        assert response.status_code == 201
        assert body["format"] == format_name
        assert body["size_bytes"] > 0
        created.append(body)

        download_response = client.get(body["download_url"])
        assert download_response.status_code == 200
        assert download_response.content

    list_response = client.get("/api/artifacts")
    assert list_response.status_code == 200
    assert {item["artifact_id"] for item in list_response.json()} == {
        item["artifact_id"] for item in created
    }


def test_tasks_endpoint_generates_document_artifact_from_prompt(
    isolated_history_storage,
    monkeypatch,
):
    client = TestClient(create_app())

    class FakeSearchResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "Heading": "GitHub trending",
                "AbstractText": "Current GitHub hot repositories.",
                "AbstractURL": "https://example.test/github-trending",
                "RelatedTopics": [],
            }

    monkeypatch.setattr(
        "app.backend.services.task_service.requests.get",
        lambda *args, **kwargs: FakeSearchResponse(),
    )

    response = client.post(
        "/api/tasks",
        json={"prompt": "帮我做一个 GitHub 热点的 PDF"},
    )
    body = response.json()
    task_id = body["data"]["metadata"]["task_id"]
    artifact = body["data"]["metadata"]["generated_artifacts"][0]

    assert response.status_code == 200
    assert body["data"]["metadata"]["document_generation"]["format"] == "pdf"
    assert body["data"]["metadata"]["tool_flags"]["web_search"] is True
    assert artifact["format"] == "pdf"
    assert artifact["download_url"] in body["data"]["output"]
    assert client.get(artifact["download_url"]).status_code == 200

    history_response = client.get(f"/api/history/tasks/{task_id}")
    history_body = history_response.json()

    assert history_response.status_code == 200
    assert history_body["metadata"]["generated_artifacts"][0]["artifact_id"] == (
        artifact["artifact_id"]
    )


def test_skills_endpoint_discovers_local_skill(tmp_path, monkeypatch):
    skill_root = tmp_path / "skills"
    skill_dir = skill_root / "frontend-design"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(
        "---\nname: frontend-design\ndescription: Polish UI.\n---\n\nUse refined visual design.",
        encoding="utf-8",
    )
    monkeypatch.setenv("SKILL_ROOTS", json.dumps([str(skill_root)]))
    monkeypatch.setenv("SKILL_SETTINGS_PATH", str(tmp_path / "skill_settings.json"))
    clear_settings_cache()
    clear_skill_registry_service_cache()

    client = TestClient(create_app())
    list_response = client.get("/api/skills")
    detail_response = client.get("/api/skills/frontend-design")

    assert list_response.status_code == 200
    assert list_response.json()[0]["skill_id"] == "frontend-design"
    assert detail_response.status_code == 200
    assert "Use refined visual design" in detail_response.json()["content_excerpt"]
    update_response = client.patch(
        "/api/skills/frontend-design",
        json={"enabled": False, "trust_level": "disabled", "notes": "test off"},
    )
    list_after_update = client.get("/api/skills")

    assert update_response.status_code == 200
    assert update_response.json()["enabled"] is False
    assert update_response.json()["trust_level"] == "disabled"
    assert list_after_update.json()[0]["enabled"] is False

    clear_skill_registry_service_cache()
    clear_settings_cache()


def test_mcp_endpoints_manage_servers_and_tools(isolated_history_storage, monkeypatch):
    client = TestClient(create_app())

    class FakeMCPResponse:
        def __init__(self, payload):
            self._payload = payload

        def raise_for_status(self):
            return None

        def json(self):
            return self._payload

    def fake_post(url, headers=None, json=None, timeout=None):
        assert url == "http://mcp.example/rpc"
        assert headers["X-Test"] == "1"
        method = json["method"]
        if method == "initialize":
            return FakeMCPResponse({"jsonrpc": "2.0", "id": json["id"], "result": {}})
        if method == "tools/list":
            return FakeMCPResponse(
                {
                    "jsonrpc": "2.0",
                    "id": json["id"],
                    "result": {
                        "tools": [
                            {
                                "name": "read_file",
                                "description": "Read a file",
                                "inputSchema": {"type": "object"},
                            }
                        ]
                    },
                }
            )
        if method == "tools/call":
            return FakeMCPResponse(
                {
                    "jsonrpc": "2.0",
                    "id": json["id"],
                    "result": {"content": [{"type": "text", "text": "file text"}]},
                }
            )
        raise AssertionError(method)

    monkeypatch.setattr("app.backend.services.mcp_service.requests.post", fake_post)

    create_response = client.post(
        "/api/mcp/servers",
        json={
            "server_id": "filesystem",
            "display_name": "Filesystem",
            "endpoint_url": "http://mcp.example/rpc",
            "enabled": True,
            "headers": {"X-Test": "1"},
            "allowed_tools": ["read_file"],
            "blocked_tools": ["delete_file"],
            "tool_call_requires_approval": True,
            "notes": "local files",
        },
    )
    tools_response = client.get("/api/mcp/servers/filesystem/tools")
    approval_response = client.post(
        "/api/mcp/servers/filesystem/tools/call",
        json={"tool_name": "read_file", "arguments": {"path": "README.md"}},
    )
    blocked_response = client.post(
        "/api/mcp/servers/filesystem/tools/call",
        json={
            "tool_name": "delete_file",
            "arguments": {"path": "README.md"},
            "approved": True,
        },
    )
    call_response = client.post(
        "/api/mcp/servers/filesystem/tools/call",
        json={
            "tool_name": "read_file",
            "arguments": {"path": "README.md"},
            "approved": True,
            "approval_comment": "test approval",
        },
    )
    task_response = client.post(
        "/api/tasks",
        json={"prompt": "Use MCP tools", "mcp_server_ids": ["filesystem"]},
    )

    assert create_response.status_code == 201
    listed_server = client.get("/api/mcp/servers").json()[0]
    assert listed_server["server_id"] == "filesystem"
    assert listed_server["headers"] == {"X-Test": "***"}
    assert listed_server["headers_configured"] is True
    assert listed_server["tool_call_requires_approval"] is True
    assert listed_server["allowed_tools"] == ["read_file"]
    assert listed_server["blocked_tools"] == ["delete_file"]
    assert tools_response.status_code == 200
    assert tools_response.json()["tools"][0]["name"] == "read_file"
    assert call_response.status_code == 200
    assert approval_response.json()["status"] == "approval_required"
    assert blocked_response.json()["status"] == "blocked"
    assert call_response.json()["status"] == "ok"
    audit_response = client.get("/api/mcp/audit")
    assert audit_response.status_code == 200
    audit_statuses = {item["status"] for item in audit_response.json()}
    assert {"approval_required", "blocked", "ok"}.issubset(audit_statuses)
    assert task_response.status_code == 200
    assert task_response.json()["data"]["metadata"]["mcp_context"]["status"] == "ready"


def test_mcp_endpoint_accepts_stdio_server_config(isolated_history_storage):
    client = TestClient(create_app())

    create_response = client.post(
        "/api/mcp/servers",
        json={
            "server_id": "stdio-files",
            "display_name": "stdio files",
            "transport": "stdio",
            "command": "python",
            "args": ["-m", "fake_mcp"],
            "env": {"TOKEN": "secret"},
            "enabled": True,
            "tool_call_requires_approval": True,
        },
    )
    list_response = client.get("/api/mcp/servers")

    assert create_response.status_code == 201
    body = list_response.json()[0]
    assert body["transport"] == "stdio"
    assert body["command"] == "python"
    assert body["env"] == {"TOKEN": "***"}
    assert body["env_configured"] is True


def test_project_spaces_inject_project_context_into_tasks(isolated_history_storage):
    client = TestClient(create_app())

    create_response = client.post(
        "/api/projects",
        json={
            "project_id": "mindforge-dev",
            "display_name": "Mindforge Dev",
            "description": "Build the Mindforge web app.",
            "instructions": "Answer in concise Chinese and preserve product decisions.",
            "memory": "MCP calls require approval and audit.",
            "repo_path": ".",
            "skill_ids": ["frontend-design"],
            "mcp_server_ids": ["filesystem"],
            "tags": ["dev"],
            "enabled": True,
        },
    )
    task_response = client.post(
        "/api/tasks",
        json={"prompt": "继续优化产品", "project_id": "mindforge-dev"},
    )

    assert create_response.status_code == 201
    assert client.get("/api/projects").json()[0]["project_id"] == "mindforge-dev"
    body = task_response.json()
    assert task_response.status_code == 200
    assert body["data"]["metadata"]["project_id"] == "mindforge-dev"
    assert body["data"]["metadata"]["project_context"]["status"] == "ready"
    assert "Project space context:" in body["data"]["output"]
    assert "MCP calls require approval and audit." in body["data"]["output"]


def test_canvas_artifact_updates_create_versions(isolated_history_storage):
    client = TestClient(create_app())

    task_response = client.post(
        "/api/tasks",
        json={"prompt": "生成画布", "tool_flags": {"canvas": True}},
    )
    task_body = task_response.json()
    task_id = task_body["data"]["metadata"]["task_id"]
    artifact = task_body["data"]["metadata"]["canvas_artifacts"][0]

    update_response = client.patch(
        f"/api/history/tasks/{task_id}/canvas-artifacts/{artifact['artifact_id']}",
        json={"title": "新版画布", "content": "第二版内容"},
    )
    updated_artifact = update_response.json()["metadata"]["canvas_artifacts"][0]

    assert task_response.status_code == 200
    assert update_response.status_code == 200
    assert updated_artifact["version"] == 2
    assert len(updated_artifact["versions"]) == 2
    assert updated_artifact["versions"][-1]["content"] == "第二版内容"


def test_tasks_endpoint_persists_conversation_context_to_history(isolated_history_storage):
    client = TestClient(create_app())

    response = client.post(
        "/api/tasks",
        json={
            "prompt": "Continue with implementation risks",
            "conversation_id": "conversation-web-1",
            "conversation_history": [
                {"role": "user", "content": "Plan this feature", "task_id": "task-1"},
                {
                    "role": "assistant",
                    "content": "Use a staged rollout",
                    "task_id": "task-1",
                },
            ],
        },
    )

    body = response.json()
    task_id = body["data"]["metadata"]["task_id"]

    assert response.status_code == 200
    assert body["data"]["metadata"]["conversation_id"] == "conversation-web-1"
    assert body["data"]["metadata"]["conversation_turn_count"] == 3

    history_response = client.get(f"/api/history/tasks/{task_id}")
    history_body = history_response.json()

    assert history_response.status_code == 200
    assert history_body["request_payload"]["conversation_id"] == "conversation-web-1"
    assert history_body["metadata"]["conversation_history"][1]["role"] == "assistant"
    assert history_body["metadata"]["conversation_history"][1]["content"] == (
        "Use a staged rollout"
    )


def test_tasks_endpoint_persists_requested_skills_to_history(isolated_history_storage):
    client = TestClient(create_app())

    response = client.post(
        "/api/tasks",
        json={
            "prompt": "Improve the UI",
            "skills": ["frontend-design", "gsd-do", "frontend-design"],
        },
    )

    body = response.json()
    task_id = body["data"]["metadata"]["task_id"]

    assert response.status_code == 200
    assert body["data"]["metadata"]["skills"] == ["frontend-design", "gsd-do"]

    history_response = client.get(f"/api/history/tasks/{task_id}")
    assert history_response.status_code == 200
    assert history_response.json()["metadata"]["skills"] == [
        "frontend-design",
        "gsd-do",
    ]


def test_history_endpoint_groups_conversation_task_turns(isolated_history_storage):
    client = TestClient(create_app())

    first_response = client.post(
        "/api/tasks",
        json={
            "prompt": "First turn",
            "conversation_id": "conversation-history-1",
        },
    )
    second_response = client.post(
        "/api/tasks",
        json={
            "prompt": "Second turn",
            "conversation_id": "conversation-history-1",
            "conversation_history": [
                {"role": "user", "content": "First turn"},
                {
                    "role": "assistant",
                    "content": first_response.json()["data"]["output"],
                },
            ],
        },
    )

    assert first_response.status_code == 200
    assert second_response.status_code == 200

    list_response = client.get("/api/history/tasks")
    list_body = list_response.json()
    assert list_response.status_code == 200
    conversation_rows = [
        item
        for item in list_body
        if item["conversation_id"] == "conversation-history-1"
    ]
    assert len(conversation_rows) == 2
    assert {item["conversation_turn_count"] for item in conversation_rows} == {1, 3}

    conversation_response = client.get(
        "/api/history/conversations/conversation-history-1/tasks"
    )
    conversation_body = conversation_response.json()

    assert conversation_response.status_code == 200
    assert [item["prompt"] for item in conversation_body] == [
        "First turn",
        "Second turn",
    ]
    assert conversation_body[1]["metadata"]["conversation_id"] == (
        "conversation-history-1"
    )


def test_history_endpoint_deletes_conversation_turns(isolated_history_storage):
    client = TestClient(create_app())

    first_response = client.post(
        "/api/tasks",
        json={
            "prompt": "First turn",
            "conversation_id": "conversation-delete-1",
        },
    )
    second_response = client.post(
        "/api/tasks",
        json={
            "prompt": "Second turn",
            "conversation_id": "conversation-delete-1",
        },
    )

    assert first_response.status_code == 200
    assert second_response.status_code == 200

    delete_response = client.delete(
        "/api/history/conversations/conversation-delete-1"
    )
    assert delete_response.status_code == 204

    conversation_response = client.get(
        "/api/history/conversations/conversation-delete-1/tasks"
    )
    assert conversation_response.status_code == 404


def test_history_endpoint_deletes_single_task_without_conversation(isolated_history_storage):
    client = TestClient(create_app())

    response = client.post("/api/tasks", json={"prompt": "Standalone task"})
    task_id = response.json()["data"]["metadata"]["task_id"]

    delete_response = client.delete(f"/api/history/tasks/{task_id}")
    assert delete_response.status_code == 204
    assert client.get(f"/api/history/tasks/{task_id}").status_code == 404


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
    assert any(item["provider_id"] == "volces-ark" for item in provider_response.json())

    assert model_response.status_code == 200
    assert any(item["model_id"] == "gpt-5.4" for item in model_response.json())
    assert any(
        item["model_id"] == "doubao-seed-2.0-lite"
        for item in model_response.json()
    )


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


def test_paper_revision_tasks_endpoint_persists_academic_context(
    isolated_history_storage,
    mocked_academic_pages,
):
    client = TestClient(create_app())

    response = client.post(
        "/api/tasks",
        json={
            "prompt": "Revise this paper abstract for the target journal.",
            "preset_mode": "paper-revision",
            "task_type": "writing",
            "journal_name": "Example Journal",
            "journal_url": "https://journal.example/guidelines",
            "reference_paper_urls": ["https://paper.example/reference"],
        },
    )

    body = response.json()
    task_id = body["data"]["metadata"]["task_id"]

    assert response.status_code == 200
    assert body["data"]["provider"] == "multi-stage-orchestrator"
    trace = body["data"]["metadata"]["orchestration"]
    assert trace["strategy"] == "serial-paper-revision"
    assert len(trace["stages"]) == 6
    assert trace["stages"][0]["role"] == "standards-editor"
    assert trace["stages"][-1]["role"] == "final-reviewer"
    assert body["data"]["metadata"]["academic_context"]["journal"]["title"] == (
        "Author Guidelines"
    )
    assert body["data"]["metadata"]["academic_context"]["reference_papers"][0]["title"] == (
        "Reference Paper"
    )

    history_response = client.get(f"/api/history/tasks/{task_id}")
    assert history_response.status_code == 200
    assert history_response.json()["metadata"]["academic_context"]["journal"]["status"] == (
        "fetched"
    )


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


def test_control_providers_endpoint_updates_provider_config(
    isolated_model_control_storage,
    monkeypatch,
):
    client = TestClient(create_app())
    monkeypatch.setenv("MIND_TEST_OPENAI_KEY", "secret-value")

    update_response = client.put(
        "/api/control/providers/openai",
        json={
            "enabled": False,
            "api_base_url": "https://openai.test/v1",
            "api_key_env": "MIND_TEST_OPENAI_KEY",
            "protocol": "openai",
            "anthropic_api_base_url": "https://openai.test/anthropic",
        },
    )
    control_response = client.get("/api/control/providers")
    registry_response = client.get("/api/providers")

    assert update_response.status_code == 200
    body = update_response.json()
    assert body["provider_id"] == "openai"
    assert body["enabled"] is False
    assert body["api_base_url"] == "https://openai.test/v1"
    assert body["api_key_env"] == "MIND_TEST_OPENAI_KEY"
    assert body["api_key_configured"] is True
    assert body["protocol"] == "openai"
    assert body["anthropic_api_base_url"] == "https://openai.test/anthropic"
    assert "secret-value" not in str(body)
    assert any(
        item["provider_id"] == "openai"
        and item["api_base_url"] == "https://openai.test/v1"
        for item in control_response.json()
    )
    assert any(
        item["provider_id"] == "openai" and item["enabled"] is False
        for item in registry_response.json()
    )
    from app.backend.services import model_loader

    saved_overrides = model_loader.PROVIDER_OVERRIDES_PATH.read_text(encoding="utf-8")
    assert "MIND_TEST_OPENAI_KEY" in saved_overrides
    assert "secret-value" not in saved_overrides


def test_control_provider_connection_endpoint_can_be_mocked(
    isolated_model_control_storage,
    monkeypatch,
):
    client = TestClient(create_app())
    monkeypatch.setenv("OPENAI_API_KEY", "secret-value")

    class FakeResponse:
        status_code = 200

    def fake_get(url, headers, timeout):
        assert url == "https://api.openai.com/v1/models"
        assert headers["Authorization"] == "Bearer secret-value"
        assert timeout == 10
        return FakeResponse()

    monkeypatch.setattr(
        "app.backend.services.model_control_service.requests.get",
        fake_get,
    )

    response = client.post("/api/control/providers/openai/test")

    assert response.status_code == 200
    body = response.json()
    assert body["provider_id"] == "openai"
    assert body["ok"] is True
    assert body["status"] == "connected"
    assert body["api_key_env"] == "OPENAI_API_KEY"
    assert body["api_key_configured"] is True
    assert body["upstream_status"] == 200
    assert "secret-value" not in str(body)


def test_control_provider_update_rejects_invalid_protocol(isolated_model_control_storage):
    client = TestClient(create_app())

    response = client.put(
        "/api/control/providers/openai",
        json={"protocol": "unsupported-protocol"},
    )

    assert response.status_code == 400
    assert "Unsupported provider protocol" in response.json()["detail"]


def test_control_provider_update_rejects_invalid_url(isolated_model_control_storage):
    client = TestClient(create_app())

    response = client.put(
        "/api/control/providers/openai",
        json={"api_base_url": "not-a-url"},
    )

    assert response.status_code == 400
    assert "Provider URLs must start" in response.json()["detail"]


def test_control_user_provider_and_model_crud(isolated_model_control_storage):
    client = TestClient(create_app())

    provider_response = client.post(
        "/api/control/providers",
        json={
            "provider_id": "custom-ark",
            "display_name": "Custom Ark",
            "description": "User provider",
            "api_base_url": "https://ark.example/v3",
            "protocol": "openai-compatible",
            "api_key": "secret-value",
            "api_key_env": "CUSTOM_ARK_KEY",
        },
    )
    model_response = client.post(
        "/api/control/models",
        json={
            "model_id": "custom-doubao",
            "display_name": "Custom Doubao",
            "provider_id": "custom-ark",
            "upstream_model": "doubao-seed-2.0-lite",
            "priority": "high",
            "supported_preset_modes": ["code-engineering"],
        },
    )
    providers_response = client.get("/api/control/user-providers")
    models_response = client.get("/api/control/user-models")

    assert provider_response.status_code == 201
    provider_body = provider_response.json()
    assert provider_body["provider_id"] == "custom-ark"
    assert provider_body["is_custom"] is True
    assert provider_body["api_key_configured"] is True
    assert "secret-value" not in str(provider_body)
    assert model_response.status_code == 201
    assert model_response.json()["is_custom"] is True
    assert any(item["provider_id"] == "custom-ark" for item in providers_response.json())
    assert any(item["model_id"] == "custom-doubao" for item in models_response.json())

    delete_response = client.delete("/api/control/providers/custom-ark")
    assert delete_response.status_code == 204
    assert client.get("/api/control/user-providers").json() == []
    assert client.get("/api/control/user-models").json() == []


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


def test_rule_template_update_endpoint_persists_changes(isolated_model_control_storage):
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
            "trigger_keywords": ["paper"],
            "assignments": [
                {
                    "role": "style-reviewer",
                    "responsibility": "Review style",
                    "model_id": "kimi-2.5",
                }
            ],
            "notes": "initial",
        },
    )

    update_response = client.put(
        "/api/control/rule-templates/paper-style",
        json={
            "template_id": "paper-style",
            "display_name": "Paper Style Updated",
            "description": "Updated paper review template",
            "preset_mode": "paper-revision",
            "task_types": ["writing", "review"],
            "default_coordinator_model_id": "gpt-5.4",
            "enabled": True,
            "is_default": False,
            "trigger_keywords": ["paper", "journal"],
            "assignments": [
                {
                    "role": "content-reviewer",
                    "responsibility": "Review content",
                    "model_id": "glm-5.1",
                }
            ],
            "notes": "updated",
        },
    )
    list_response = client.get("/api/control/rule-templates")

    assert update_response.status_code == 200
    assert update_response.json()["display_name"] == "Paper Style Updated"
    assert update_response.json()["assignments"][0]["model_id"] == "glm-5.1"
    assert any(
        item["template_id"] == "paper-style"
        and item["display_name"] == "Paper Style Updated"
        and item["assignments"][0]["role"] == "content-reviewer"
        for item in list_response.json()
    )


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


def test_history_endpoint_filters_pending_approval_items(isolated_history_storage):
    client = TestClient(create_app())

    pending_response = client.post(
        "/api/tasks",
        json={
            "prompt": "Apply risky repository write",
            "metadata": {
                "requires_approval": True,
                "approval_actions": ["execute shell"],
            },
        },
    )
    completed_response = client.post(
        "/api/tasks",
        json={
            "prompt": "Read repository summary",
        },
    )

    pending_task_id = pending_response.json()["data"]["metadata"]["task_id"]
    completed_task_id = completed_response.json()["data"]["metadata"]["task_id"]

    filtered_response = client.get("/api/history/tasks", params={"status": "pending_approval"})

    assert filtered_response.status_code == 200
    filtered_task_ids = {item["task_id"] for item in filtered_response.json()}
    assert pending_task_id in filtered_task_ids
    assert completed_task_id not in filtered_task_ids


def test_github_read_only_endpoints_return_summaries(
    isolated_history_storage,
    mocked_github_api,
):
    client = TestClient(create_app())

    repo_response = client.get("/api/github/repositories/openai/openai-python")
    issue_response = client.get("/api/github/repositories/openai/openai-python/issues/123")
    pr_response = client.get("/api/github/repositories/openai/openai-python/pulls/9")

    assert repo_response.status_code == 200
    assert repo_response.json()["full_name"] == "openai/openai-python"
    assert issue_response.status_code == 200
    assert issue_response.json()["number"] == 123
    assert pr_response.status_code == 200
    assert pr_response.json()["number"] == 9


def test_tasks_endpoint_persists_github_context(
    isolated_history_storage,
    mocked_github_api,
):
    client = TestClient(create_app())

    response = client.post(
        "/api/tasks",
        json={
            "prompt": "Review upstream issue and PR context",
            "github_repo": "openai/openai-python",
            "github_issue_number": 123,
            "github_pr_number": 9,
        },
    )

    body = response.json()
    task_id = body["data"]["metadata"]["task_id"]

    assert response.status_code == 200
    assert body["data"]["metadata"]["github_context"]["repository"]["full_name"] == (
        "openai/openai-python"
    )
    assert body["data"]["metadata"]["github_context"]["issue"]["number"] == 123
    assert body["data"]["metadata"]["github_context"]["pull_request"]["number"] == 9

    history_response = client.get(f"/api/history/tasks/{task_id}")
    assert history_response.status_code == 200
    assert (
        history_response.json()["metadata"]["github_context"]["repository"]["full_name"]
        == "openai/openai-python"
    )
