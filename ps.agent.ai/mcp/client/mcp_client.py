import json
import os
from typing import Dict, Any

import httpx
from langsmith import traceable
from loguru import logger
from dotenv import load_dotenv

load_dotenv()

MCP_API_BASE = "http://localhost:9185/";#os.getenv("MCP_API_BASE")
MCP_API_TOKEN = os.getenv("MCP_API_TOKEN")

HEADERS = {
    "x-api-key": "9fc250cbc543263fb9668728c3a9ea4b0b2df539",
    "Content-Type": "application/json",
}

@traceable(run_type="retriever")
async def call_mcp_api(endpoint: str, method: str = "GET", payload=None):
    url = MCP_API_BASE.rstrip("/") + "/" + endpoint.lstrip("/")
    logger.info(f"MCP request===>: {url}")
    async with httpx.AsyncClient(timeout=10) as client:
        logger.info(f"Calling MCP {method} {url}")
        resp = await client.request(method, url, json=payload, headers=HEADERS)
        resp.raise_for_status()
        return resp.json()

@traceable(name="client.call_mcp_create_jira", tags=["mcp", "http"])
async def call_mcp_create_jira(llm_json: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    spec is a dict validated by JiraIssueSpec
    This function is kept synchronous for StructuredTool compatibility; agent will call it synchronously.
    """
    print(f"llm_json ---- : {llm_json}")
    action = llm_json.get("action")
    payload = llm_json.get("args", {})
    print(f"llm_json=>> {action},{payload}")
    url = f"{MCP_API_BASE.rstrip('/')}/jira/tools/action?name={action}"
    print(f"call_mcp_create_jira=>{url}, payload={payload}")
    async with httpx.AsyncClient(timeout=10) as client:
        try:
            logger.info(f"Calling MCP POST {url},{payload}")
            resp = await client.request("POST", url, json={"payload":payload}, headers=HEADERS)
            resp.raise_for_status()
            return resp.json()
        except ValueError:
            body = {"raw": resp.text}
        if resp.status_code == 200:
            return {"success": True, "result": body}
        else:
            # bubble up error for agent to handle
            return {"success": False, "status_code": resp.status_code, "result": body}

async def list_tools():
    """Fetch list of tools registered on the MCP server"""
    return await call_mcp_api("/tools")
