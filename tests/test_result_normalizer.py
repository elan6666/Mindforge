from app.backend.integration.openhands_adapter import AdapterResult
from app.backend.services.result_normalizer import normalize_task_result


def test_normalize_task_result_for_completed_status():
    result = AdapterResult(
        status="completed",
        output="done",
        provider="mock-openhands",
        metadata={"mode": "mock"},
    )

    response = normalize_task_result(result)

    assert response.status == "completed"
    assert response.message == "Task executed successfully."
    assert response.data.output == "done"
    assert response.data.provider == "mock-openhands"


def test_normalize_task_result_for_failed_status():
    result = AdapterResult(
        status="failed",
        output="bad",
        provider="openhands-http",
        metadata={"mode": "http"},
        error_message="boom",
    )

    response = normalize_task_result(result)

    assert response.status == "failed"
    assert response.message == "Task execution failed."
    assert response.error_message == "boom"
    assert response.data.metadata["mode"] == "http"
