from types import SimpleNamespace

import requests

from app.backend.integration.openhands_adapter import OpenHandsAdapter


def make_settings(**overrides):
    defaults = {
        "openhands_mode": "mock",
        "openhands_base_url": None,
        "openhands_timeout_seconds": 30,
        "model_api_timeout_seconds": 60,
        "model_api_max_tokens": 1200,
    }
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def test_disabled_mode_returns_failed_result():
    adapter = OpenHandsAdapter(make_settings(openhands_mode="disabled"))

    result = adapter.run_task({"prompt": "anything"})

    assert result.status == "failed"
    assert result.provider == "disabled"
    assert result.error_message == "Adapter disabled"


def test_mock_mode_returns_deterministic_payload():
    adapter = OpenHandsAdapter(make_settings(openhands_mode="mock"))

    result = adapter.run_task(
        {
            "prompt": "Analyze backend",
            "preset_mode": "default",
            "repo_path": ".",
            "model": "gpt-5.4",
            "provider_id": "openai",
            "metadata": {
                "orchestration_stage": "backend",
                "orchestration_role": "backend",
            },
        }
    )

    assert result.status == "completed"
    assert result.provider == "mock-openhands"
    assert "received prompt: Analyze backend" in result.output
    assert "stage: backend" in result.output
    assert "model: gpt-5.4" in result.output
    assert result.metadata["mode"] == "mock"


def test_http_mode_success_response(monkeypatch):
    adapter = OpenHandsAdapter(
        make_settings(
            openhands_mode="http",
            openhands_base_url="http://openhands.local",
        )
    )

    class FakeResponse:
        status_code = 200

        def raise_for_status(self):
            return None

        def json(self):
            return {"status": "completed", "output": "ok"}

    def fake_post(url, json, timeout):
        assert url == "http://openhands.local/tasks"
        assert json["prompt"] == "ping"
        assert timeout == 30
        return FakeResponse()

    monkeypatch.setattr(requests, "post", fake_post)

    result = adapter.run_task({"prompt": "ping"})

    assert result.status == "completed"
    assert result.provider == "openhands-http"
    assert result.output == "ok"
    assert result.metadata["upstream_status"] == 200


def test_http_mode_request_error_returns_failed_result(monkeypatch):
    adapter = OpenHandsAdapter(
        make_settings(
            openhands_mode="http",
            openhands_base_url="http://openhands.local",
        )
    )

    def fake_post(url, json, timeout):
        raise requests.RequestException("network down")

    monkeypatch.setattr(requests, "post", fake_post)

    result = adapter.run_task({"prompt": "ping"})

    assert result.status == "failed"
    assert result.provider == "openhands-http"
    assert result.error_message == "network down"


def test_model_api_mode_calls_openai_compatible_endpoint(monkeypatch):
    adapter = OpenHandsAdapter(make_settings(openhands_mode="model-api"))
    monkeypatch.setenv("ARK_API_KEY", "test-secret")

    class FakeResponse:
        status_code = 200

        def raise_for_status(self):
            return None

        def json(self):
            return {
                "choices": [
                    {
                        "message": {
                            "content": "model api ok",
                        }
                    }
                ],
                "usage": {"total_tokens": 12},
            }

    def fake_post(url, headers, json, timeout):
        assert url == "https://ark.cn-beijing.volces.com/api/coding/v3/chat/completions"
        assert headers["Authorization"] == "Bearer test-secret"
        assert json["model"] == "doubao-seed-2.0-lite"
        assert json["messages"][1]["content"] == "ping"
        assert timeout == 60
        return FakeResponse()

    monkeypatch.setattr(requests, "post", fake_post)

    result = adapter.run_task(
        {
            "prompt": "ping",
            "model": "doubao-seed-2.0-lite",
            "provider_id": "volces-ark",
        }
    )

    assert result.status == "completed"
    assert result.provider == "model-api:volces-ark"
    assert result.output == "model api ok"
    assert result.metadata["usage"]["total_tokens"] == 12
