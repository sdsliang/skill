#!/usr/bin/env python3
"""Minimal MCP streamable-HTTP client (stdlib only).

Shared by ``pull_results.py`` and ``meeting_pull.py``. Two endpoints matter and
they are **not** interchangeable:

* ``MCP_PHARMCUBE_ENDPOINT_URL`` -- the Tool Smith data server (in-cluster). This
  is the one that exposes ``query-clinical-result-with-params``, i.e. the only
  supported way to pull a whole conference's result rows.
* ``MCP_OPENAPI_URL`` (default ``https://mcp-openapi.pharmcube.com/mcp``) -- the
  public Pharmcube MCP. It has ``medicalMeeting`` / ``trialResultTC`` but **no**
  conference-wide result query, so it cannot be used as the row source.

Nothing here guesses tool names: ``find_tool()`` asks the server.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional

TS_MCP_URL = os.environ.get("MCP_PHARMCUBE_ENDPOINT_URL") or "http://172.17.26.74:30080/mcp/"
OPEN_MCP_URL = os.environ.get("MCP_OPENAPI_URL") or "https://mcp-openapi.pharmcube.com/mcp"
SECRET_FILE = os.path.expanduser("~/.pi/agent/pharmcube-mcp-appkey")


def app_key() -> str:
    key = (os.environ.get("PHARMCUBE_MCP_APP_KEY") or "").strip()
    if key:
        return key
    try:
        with open(SECRET_FILE, "r", encoding="utf-8") as fh:
            return fh.read().strip()
    except OSError:
        return ""


def _parse_body(raw: str) -> Dict[str, Any]:
    """Accept a plain JSON body or an SSE frame stream."""
    raw = raw.strip()
    if raw.startswith("{"):
        return json.loads(raw)
    for line in raw.splitlines():
        if line.startswith("data:"):
            payload = line[5:].strip()
            if payload and payload != "[DONE]":
                return json.loads(payload)
    raise RuntimeError(f"unparsable MCP response: {raw[:300]}")


class Mcp:
    """initialize once, then tools/call. One instance per endpoint."""

    def __init__(self, url: Optional[str] = None, key: Optional[str] = None,
                 timeout: int = 120):
        self.url = url or TS_MCP_URL
        self.key = app_key() if key is None else key
        self.timeout = timeout
        self.session_id: Optional[str] = None
        self._id = 0

    def _post(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        req = urllib.request.Request(self.url, data=json.dumps(payload).encode("utf-8"),
                                     method="POST")
        req.add_header("Content-Type", "application/json")
        req.add_header("Accept", "application/json, text/event-stream")
        if self.key:
            req.add_header("Authorization", "Bearer " + self.key)
        if self.session_id:
            req.add_header("mcp-session-id", self.session_id)
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                self.session_id = resp.headers.get("mcp-session-id") or self.session_id
                raw = resp.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", "replace")[:400]
            raise RuntimeError(f"MCP HTTP {exc.code} at {self.url}: {detail}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(
                f"cannot reach MCP endpoint {self.url}: {exc.reason}. "
                "Set MCP_PHARMCUBE_ENDPOINT_URL to the in-cluster data server; the "
                "public mcp-openapi endpoint has no conference-wide result query."
            ) from exc
        return _parse_body(raw)

    def init(self) -> None:
        if self.session_id:
            return
        self._id += 1
        self._post({
            "jsonrpc": "2.0", "id": self._id, "method": "initialize",
            "params": {
                "protocolVersion": "2025-03-26",
                "capabilities": {},
                "clientInfo": {"name": "conference-result-triage", "version": "0.3"},
            },
        })

    def list_tools(self) -> List[Dict[str, Any]]:
        self.init()
        self._id += 1
        out = self._post({"jsonrpc": "2.0", "id": self._id,
                          "method": "tools/list", "params": {}})
        return (out.get("result") or {}).get("tools") or []

    def find_tool(self, needle: str) -> str:
        """Return the server's own name for the single tool containing ``needle``."""
        hits = [t["name"] for t in self.list_tools() if needle in t["name"]]
        if len(hits) == 1:
            return hits[0]
        if not hits:
            raise RuntimeError(
                f"no tool matching '{needle}' at {self.url}; "
                f"available: {[t['name'] for t in self.list_tools()][:20]}")
        raise RuntimeError(f"ambiguous tools for '{needle}': {hits}")

    def call(self, name: str, arguments: Dict[str, Any]) -> Any:
        self.init()
        self._id += 1
        out = self._post({
            "jsonrpc": "2.0", "id": self._id, "method": "tools/call",
            "params": {"name": name, "arguments": arguments},
        })
        if "error" in out:
            raise RuntimeError(f"MCP error: {out['error']}")
        for part in (out.get("result") or {}).get("content") or []:
            if part.get("type") == "text":
                return json.loads(part["text"])
        return {}
