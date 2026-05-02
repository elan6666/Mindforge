"""MCP server registry and minimal HTTP JSON-RPC client."""

from __future__ import annotations

from datetime import UTC, datetime
from functools import lru_cache
import ipaddress
import json
import os
from pathlib import Path
import subprocess
import time
from typing import Any
from urllib.parse import urlparse
from uuid import uuid4

import requests

from app.backend.core.config import Settings, get_settings
from app.backend.schemas.mcp import (
    MCPServerSummary,
    MCPServerUpsert,
    MCPToolAuditRecord,
    MCPToolCallResult,
    MCPToolListResult,
    MCPToolSummary,
)


class MCPService:
    """Manage MCP server connections and direct tool calls."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.registry_path = Path(settings.mcp_registry_path)
        self.audit_path = self.registry_path.with_name("mcp_audit.json")
        self.registry_path.parent.mkdir(parents=True, exist_ok=True)

    def list_servers(self) -> list[MCPServerSummary]:
        """Return configured MCP servers."""
        return [self._sanitize_server(server) for server in self._load().values()]

    def get_server(self, server_id: str) -> MCPServerSummary | None:
        """Return one MCP server config."""
        return self._load().get(server_id)

    def upsert_server(self, payload: MCPServerUpsert) -> MCPServerSummary:
        """Create or update one MCP server."""
        self._validate_server_config(payload)
        servers = self._load()
        normalized_payload = payload.model_copy(
            update={
                "allowed_tools": self._normalize_tool_names(payload.allowed_tools),
                "blocked_tools": self._normalize_tool_names(payload.blocked_tools),
            }
        )
        server = MCPServerSummary(
            **normalized_payload.model_dump(),
            status="configured",
            headers_configured=bool(normalized_payload.headers),
            env_configured=bool(normalized_payload.env),
        )
        servers[normalized_payload.server_id] = server
        self._save(servers)
        return self._sanitize_server(server)

    def delete_server(self, server_id: str) -> bool:
        """Delete one MCP server config."""
        servers = self._load()
        if server_id not in servers:
            return False
        servers.pop(server_id)
        self._save(servers)
        return True

    def list_tools(self, server_id: str) -> MCPToolListResult:
        """Call MCP tools/list for one server."""
        server = self.get_server(server_id)
        if server is None:
            return MCPToolListResult(
                server_id=server_id,
                status="not_found",
                error_message=f"Unknown MCP server '{server_id}'.",
            )
        if not server.enabled:
            return MCPToolListResult(server_id=server_id, status="disabled")
        try:
            if server.transport == "stdio":
                payload = self._stdio_jsonrpc_sequence(
                    server,
                    [
                        (
                            "initialize",
                            {
                                "protocolVersion": "2024-11-05",
                                "capabilities": {},
                                "clientInfo": {"name": "Mindforge", "version": "0.1.0"},
                            },
                        ),
                        ("tools/list", {}),
                    ],
                )
            else:
                self._initialize(server)
                payload = self._jsonrpc(server, "tools/list", {})
            raw_tools = payload.get("tools", []) if isinstance(payload, dict) else []
            tools = [
                MCPToolSummary(
                    name=str(tool.get("name") or ""),
                    description=str(tool.get("description") or ""),
                    input_schema=tool.get("inputSchema") or tool.get("input_schema") or {},
                )
                for tool in raw_tools
                if isinstance(tool, dict) and tool.get("name")
            ]
            return MCPToolListResult(server_id=server_id, status="ok", tools=tools)
        except Exception as exc:
            return MCPToolListResult(
                server_id=server_id,
                status="failed",
                error_message=str(exc),
            )

    def call_tool(
        self,
        server_id: str,
        *,
        tool_name: str,
        arguments: dict[str, Any],
        approved: bool = False,
        approval_comment: str | None = None,
    ) -> MCPToolCallResult:
        """Call MCP tools/call for one server."""
        start = time.perf_counter()
        server = self.get_server(server_id)
        if server is None:
            audit_id = self._append_audit(
                server_id=server_id,
                tool_name=tool_name,
                arguments=arguments,
                status="not_found",
                approved=approved,
                error_message=f"Unknown MCP server '{server_id}'.",
                duration_ms=self._duration_ms(start),
            )
            return MCPToolCallResult(
                server_id=server_id,
                tool_name=tool_name,
                status="not_found",
                error_message=f"Unknown MCP server '{server_id}'.",
                audit_id=audit_id,
            )
        if not server.enabled:
            audit_id = self._append_audit(
                server_id=server_id,
                tool_name=tool_name,
                arguments=arguments,
                status="disabled",
                approved=approved,
                blocked_reason="server_disabled",
                duration_ms=self._duration_ms(start),
            )
            return MCPToolCallResult(
                server_id=server_id,
                tool_name=tool_name,
                status="disabled",
                audit_id=audit_id,
            )
        blocked_reason = self._tool_policy_block_reason(server, tool_name)
        if blocked_reason is not None:
            audit_id = self._append_audit(
                server_id=server_id,
                tool_name=tool_name,
                arguments=arguments,
                status="blocked",
                approved=approved,
                blocked_reason=blocked_reason,
                duration_ms=self._duration_ms(start),
            )
            return MCPToolCallResult(
                server_id=server_id,
                tool_name=tool_name,
                status="blocked",
                error_message=blocked_reason,
                audit_id=audit_id,
            )
        if server.tool_call_requires_approval and not approved:
            audit_id = self._append_audit(
                server_id=server_id,
                tool_name=tool_name,
                arguments=arguments,
                status="approval_required",
                approved=False,
                blocked_reason="tool_call_requires_approval",
                duration_ms=self._duration_ms(start),
            )
            return MCPToolCallResult(
                server_id=server_id,
                tool_name=tool_name,
                status="approval_required",
                error_message="MCP tool call requires explicit approval.",
                audit_id=audit_id,
            )
        try:
            if server.transport == "stdio":
                result = self._stdio_jsonrpc_sequence(
                    server,
                    [
                        (
                            "initialize",
                            {
                                "protocolVersion": "2024-11-05",
                                "capabilities": {},
                                "clientInfo": {"name": "Mindforge", "version": "0.1.0"},
                            },
                        ),
                        ("tools/call", {"name": tool_name, "arguments": arguments}),
                    ],
                )
            else:
                self._initialize(server)
                result = self._jsonrpc(
                    server,
                    "tools/call",
                    {"name": tool_name, "arguments": arguments},
                )
            audit_id = self._append_audit(
                server_id=server_id,
                tool_name=tool_name,
                arguments=arguments,
                status="ok",
                approved=approved,
                duration_ms=self._duration_ms(start),
            )
            return MCPToolCallResult(
                server_id=server_id,
                tool_name=tool_name,
                status="ok",
                result=result,
                audit_id=audit_id,
            )
        except Exception as exc:
            audit_id = self._append_audit(
                server_id=server_id,
                tool_name=tool_name,
                arguments=arguments,
                status="failed",
                approved=approved,
                error_message=str(exc),
                duration_ms=self._duration_ms(start),
            )
            return MCPToolCallResult(
                server_id=server_id,
                tool_name=tool_name,
                status="failed",
                error_message=str(exc),
                audit_id=audit_id,
            )

    def list_audit_records(self, limit: int = 100) -> list[MCPToolAuditRecord]:
        """Return recent MCP tool-call audit records, newest first."""
        records = self._load_audit_records()
        return sorted(records, key=lambda item: item.created_at, reverse=True)[:limit]

    def prompt_context(self, server_ids: list[str]) -> dict[str, Any]:
        """Return a compact task prompt context for selected MCP servers."""
        selected = [server_id.strip() for server_id in server_ids if server_id.strip()]
        if not selected:
            return {"status": "skipped", "servers": []}
        results = [self.list_tools(server_id) for server_id in selected]
        return {
            "status": "ready" if any(item.status == "ok" for item in results) else "unavailable",
            "servers": [item.model_dump(mode="json") for item in results],
        }

    def _initialize(self, server: MCPServerSummary) -> None:
        self._jsonrpc(
            server,
            "initialize",
            {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "Mindforge", "version": "0.1.0"},
            },
        )

    def _jsonrpc(
        self,
        server: MCPServerSummary,
        method: str,
        params: dict[str, Any],
    ) -> Any:
        self._validate_endpoint_url(server.endpoint_url)
        response = requests.post(
            server.endpoint_url,
            headers={
                "Content-Type": "application/json",
                **server.headers,
            },
            json={
                "jsonrpc": "2.0",
                "id": str(uuid4()),
                "method": method,
                "params": params,
            },
            timeout=20,
        )
        response.raise_for_status()
        body = response.json()
        if body.get("error"):
            raise RuntimeError(body["error"])
        return body.get("result", {})

    def _stdio_jsonrpc_sequence(
        self,
        server: MCPServerSummary,
        calls: list[tuple[str, dict[str, Any]]],
    ) -> Any:
        """Run a short-lived stdio MCP session and return the final result."""
        if not server.command:
            raise ValueError("stdio MCP server requires command.")
        command = [server.command, *server.args]
        env = os.environ.copy()
        env.update(server.env)
        process = subprocess.Popen(
            command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=server.working_directory or None,
            env=env,
            shell=False,
        )
        try:
            final_result: Any = {}
            for method, params in calls:
                request_id = str(uuid4())
                self._write_stdio_message(
                    process,
                    {
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "method": method,
                        "params": params,
                    },
                )
                body = self._read_stdio_message(process)
                if body.get("error"):
                    raise RuntimeError(body["error"])
                final_result = body.get("result", {})
            return final_result
        finally:
            try:
                process.terminate()
            except ProcessLookupError:
                pass

    @staticmethod
    def _write_stdio_message(
        process: subprocess.Popen[bytes],
        payload: dict[str, Any],
    ) -> None:
        if process.stdin is None:
            raise RuntimeError("stdio MCP stdin is unavailable.")
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        header = f"Content-Length: {len(body)}\r\n\r\n".encode("ascii")
        process.stdin.write(header + body)
        process.stdin.flush()

    @staticmethod
    def _read_stdio_message(process: subprocess.Popen[bytes]) -> dict[str, Any]:
        if process.stdout is None:
            raise RuntimeError("stdio MCP stdout is unavailable.")
        headers: dict[str, str] = {}
        while True:
            line = process.stdout.readline()
            if not line:
                stderr = b""
                if process.stderr is not None:
                    stderr = process.stderr.read(2000)
                raise RuntimeError(
                    "stdio MCP server closed stdout before a response."
                    + (f" stderr={stderr.decode(errors='replace')}" if stderr else "")
                )
            stripped = line.strip()
            if not stripped:
                break
            text = stripped.decode("ascii", errors="replace")
            if ":" in text:
                key, value = text.split(":", 1)
                headers[key.lower()] = value.strip()
        content_length = int(headers.get("content-length") or "0")
        if content_length <= 0:
            raise RuntimeError("stdio MCP response is missing Content-Length.")
        body = process.stdout.read(content_length)
        return json.loads(body.decode("utf-8"))

    @staticmethod
    def _tool_policy_block_reason(
        server: MCPServerSummary,
        tool_name: str,
    ) -> str | None:
        normalized = tool_name.strip()
        if normalized in server.blocked_tools:
            return f"Tool '{tool_name}' is blocked by this MCP server policy."
        if server.allowed_tools and normalized not in server.allowed_tools:
            return f"Tool '{tool_name}' is not in this MCP server allow list."
        return None

    @staticmethod
    def _sanitize_server(server: MCPServerSummary) -> MCPServerSummary:
        """Return public server metadata without leaking configured secrets."""
        return server.model_copy(
            update={
                "headers": {
                    key: "***"
                    for key, value in server.headers.items()
                    if str(value).strip()
                },
                "headers_configured": any(
                    str(value).strip() for value in server.headers.values()
                ),
                "env": {
                    key: "***"
                    for key, value in server.env.items()
                    if str(value).strip()
                },
                "env_configured": any(
                    str(value).strip() for value in server.env.values()
                ),
            }
        )

    def _append_audit(
        self,
        *,
        server_id: str,
        tool_name: str,
        arguments: dict[str, Any],
        status: str,
        approved: bool,
        blocked_reason: str | None = None,
        error_message: str | None = None,
        duration_ms: int | None = None,
    ) -> str:
        audit_id = str(uuid4())
        records = self._load_audit_records()
        records.append(
            MCPToolAuditRecord(
                audit_id=audit_id,
                server_id=server_id,
                tool_name=tool_name,
                status=status,
                approved=approved,
                blocked_reason=blocked_reason,
                arguments_preview=self._arguments_preview(arguments),
                error_message=error_message,
                duration_ms=duration_ms,
                created_at=datetime.now(UTC).isoformat(),
            )
        )
        self._save_audit_records(records[-500:])
        return audit_id

    def _load_audit_records(self) -> list[MCPToolAuditRecord]:
        if not self.audit_path.exists():
            return []
        payload = json.loads(self.audit_path.read_text(encoding="utf-8"))
        return [
            MCPToolAuditRecord.model_validate(item)
            for item in payload.get("records", [])
        ]

    def _save_audit_records(self, records: list[MCPToolAuditRecord]) -> None:
        temp_path = self.audit_path.with_suffix(self.audit_path.suffix + ".tmp")
        temp_path.write_text(
            json.dumps(
                {"records": [record.model_dump(mode="json") for record in records]},
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        os.replace(temp_path, self.audit_path)

    @staticmethod
    def _arguments_preview(arguments: dict[str, Any]) -> str:
        try:
            value = json.dumps(arguments, ensure_ascii=False, sort_keys=True)
        except TypeError:
            value = str(arguments)
        return value[:1000]

    @staticmethod
    def _duration_ms(start: float) -> int:
        return int((time.perf_counter() - start) * 1000)

    @staticmethod
    def _normalize_tool_names(values: list[str]) -> list[str]:
        normalized: list[str] = []
        seen: set[str] = set()
        for value in values:
            item = str(value).strip()
            if not item or item in seen:
                continue
            seen.add(item)
            normalized.append(item)
        return normalized

    @classmethod
    def _validate_server_config(cls, payload: MCPServerUpsert) -> None:
        if payload.transport == "stdio":
            if not (payload.command or "").strip():
                raise ValueError("stdio MCP server requires command.")
            return
        cls._validate_endpoint_url(payload.endpoint_url)

    @staticmethod
    def _validate_endpoint_url(endpoint_url: str) -> None:
        """Reject clearly unsafe MCP endpoint URLs before sending headers."""
        parsed = urlparse(endpoint_url)
        if parsed.scheme not in {"http", "https"}:
            raise ValueError("MCP endpoint_url must use http or https.")
        if not parsed.hostname:
            raise ValueError("MCP endpoint_url must include a host.")
        host = parsed.hostname.strip("[]").lower()
        try:
            address = ipaddress.ip_address(host)
        except ValueError:
            address = None
        if address is not None and (
            address.is_link_local
            or address.is_multicast
            or address.is_unspecified
            or address.is_reserved
            or str(address) == "169.254.169.254"
        ):
            raise ValueError("MCP endpoint_url points to a blocked network address.")

    def _load(self) -> dict[str, MCPServerSummary]:
        if not self.registry_path.exists():
            return {}
        payload = json.loads(self.registry_path.read_text(encoding="utf-8"))
        return {
            server_id: MCPServerSummary.model_validate(item)
            for server_id, item in payload.get("servers", {}).items()
        }

    def _save(self, servers: dict[str, MCPServerSummary]) -> None:
        payload = {
            "servers": {
                server_id: server.model_dump(mode="json")
                for server_id, server in servers.items()
            }
        }
        temp_path = self.registry_path.with_suffix(self.registry_path.suffix + ".tmp")
        temp_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        os.replace(temp_path, self.registry_path)


@lru_cache(maxsize=1)
def get_mcp_service() -> MCPService:
    """Return cached MCP service."""
    return MCPService(get_settings())


def clear_mcp_service_cache() -> None:
    """Clear cached MCP service after settings changes."""
    get_mcp_service.cache_clear()
