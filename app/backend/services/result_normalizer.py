"""Convert raw adapter results into API response objects."""

from app.backend.integration.openhands_adapter import AdapterResult
from app.backend.schemas.task import TaskResponse, TaskResponseData


def normalize_task_result(result: AdapterResult) -> TaskResponse:
    """Map adapter output into the stable TaskResponse contract."""
    message = (
        "Task executed successfully."
        if result.status == "completed"
        else "Task execution failed."
    )
    return TaskResponse(
        status=result.status,
        message=message,
        data=TaskResponseData(
            output=result.output,
            provider=result.provider,
            metadata=result.metadata,
        ),
        error_message=result.error_message,
    )

