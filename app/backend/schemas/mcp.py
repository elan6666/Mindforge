"""Schemas for MCP server registry and tool calls."""

from typing import Any, Literal

from pydantic import BaseModel, Field

MCPTransport = Literal["http-jsonrpc", "stdio"]


class MCPServerUpsert(BaseModel):
    """Create or update one MCP server connection."""

    server_id: str = Field(..., min_length=1)
    display_name: str = Field(..., min_length=1)
    transport: MCPTransport = "http-jsonrpc"
    endpoint_url: str = ""
    command: str | None = None
    args: list[str] = Field(default_factory=list)
    env: dict[str, str] = Field(default_factory=dict)
    working_directory: str | None = None
    enabled: bool = True
    headers: dict[str, str] = Field(default_factory=dict)
    allowed_tools: list[str] = Field(default_factory=list)
    blocked_tools: list[str] = Field(default_factory=list)
    tool_call_requires_approval: bool = True
    notes: str = ""


class MCPServerSummary(MCPServerUpsert):
    """Stored MCP server metadata."""

    status: str = "configured"
    tool_count: int | None = None
    headers_configured: bool = False
    env_configured: bool = False


class MCPToolSummary(BaseModel):
    """One MCP tool returned by tools/list."""

    name: str
    description: str = ""
    input_schema: dict[str, Any] = Field(default_factory=dict)


class MCPToolListResult(BaseModel):
    """Tools available on one MCP server."""

    server_id: str
    status: str
    tools: list[MCPToolSummary] = Field(default_factory=list)
    error_message: str | None = None


class MCPToolCallRequest(BaseModel):
    """Call one MCP tool with JSON arguments."""

    tool_name: str = Field(..., min_length=1)
    arguments: dict[str, Any] = Field(default_factory=dict)
    approved: bool = False
    approval_comment: str | None = None


class MCPToolCallResult(BaseModel):
    """Result returned from tools/call."""

    server_id: str
    tool_name: str
    status: str
    result: Any = None
    error_message: str | None = None
    audit_id: str | None = None


class MCPToolAuditRecord(BaseModel):
    """One auditable MCP tool call attempt."""

    audit_id: str
    server_id: str
    tool_name: str
    status: str
    approved: bool = False
    blocked_reason: str | None = None
    arguments_preview: str = ""
    error_message: str | None = None
    duration_ms: int | None = None
    created_at: str
