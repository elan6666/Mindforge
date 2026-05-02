"""MCP registry and tool call endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status

from app.backend.schemas.mcp import (
    MCPServerSummary,
    MCPServerUpsert,
    MCPToolAuditRecord,
    MCPToolCallRequest,
    MCPToolCallResult,
    MCPToolListResult,
)
from app.backend.services.mcp_service import MCPService, get_mcp_service

router = APIRouter()


@router.get("/servers", response_model=list[MCPServerSummary])
def list_servers(service: MCPService = Depends(get_mcp_service)) -> list[MCPServerSummary]:
    """List configured MCP servers."""
    return service.list_servers()


@router.get("/audit", response_model=list[MCPToolAuditRecord])
def list_audit_records(
    service: MCPService = Depends(get_mcp_service),
) -> list[MCPToolAuditRecord]:
    """List recent MCP tool-call audit records."""
    return service.list_audit_records()


@router.post("/servers", response_model=MCPServerSummary, status_code=status.HTTP_201_CREATED)
def upsert_server(
    payload: MCPServerUpsert,
    service: MCPService = Depends(get_mcp_service),
) -> MCPServerSummary:
    """Create or update one MCP server."""
    return service.upsert_server(payload)


@router.delete("/servers/{server_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_server(
    server_id: str,
    service: MCPService = Depends(get_mcp_service),
) -> None:
    """Delete one MCP server."""
    if not service.delete_server(server_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Unknown MCP server '{server_id}'.",
        )


@router.get("/servers/{server_id}/tools", response_model=MCPToolListResult)
def list_tools(
    server_id: str,
    service: MCPService = Depends(get_mcp_service),
) -> MCPToolListResult:
    """List tools from one MCP server."""
    return service.list_tools(server_id)


@router.post("/servers/{server_id}/tools/call", response_model=MCPToolCallResult)
def call_tool(
    server_id: str,
    payload: MCPToolCallRequest,
    service: MCPService = Depends(get_mcp_service),
) -> MCPToolCallResult:
    """Call one MCP tool directly."""
    return service.call_tool(
        server_id,
        tool_name=payload.tool_name,
        arguments=payload.arguments,
        approved=payload.approved,
        approval_comment=payload.approval_comment,
    )
