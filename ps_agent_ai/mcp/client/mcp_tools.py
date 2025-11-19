import json
from types import coroutine
from typing import Dict, Any

from langchain_core.tools import StructuredTool
from langsmith import traceable
from pydantic import BaseModel, Field
from loguru import logger
from . mcp_client import call_mcp_api,call_mcp_create_jira



class MCPInvokeInput(BaseModel):
    endpoint: str = Field(..., description="MCP API endpoint")
    method: str = Field("GET", description="HTTP method")
    payload: dict = Field(default_factory=dict, description="Request payload")

class JiraIssueSpec(BaseModel):
    # summary: str
    # description: str
    # priority: str = "Medium"
    # issue_type: str = "Task"
    # labels: list[str] | None = None
    # assignee: str | None = None
    payload: dict


async def invoke_mcp(endpoint: str, method: str = "GET", payload: dict = None):
    """Async call to MCP API"""
    logger.debug(f"MCPInvokeInput: {endpoint}, {method}, {payload}")
    result = await call_mcp_api(endpoint, method, payload)
    logger.info(f"MCP response>>: {result}")
    return result

async def invoke_mcp_create_jira(payload: dict):
    """Async call to MCP API"""
    print(f"MCPInvokeInput: {payload}")
    result = await call_mcp_create_jira(payload)
    logger.info(f"MCP response: {result}")
    return result

async def decide_tool(query: str) -> str:
    query_lower = query.lower()
    rag_keywords = ["document", "pdf", "kafka", "ksql", "partitions","topic","java","data structures","Algorithm"]
    tool_keywords = ["weather", "math", "UUID"]
    jira_keywords = ["jira", "JIRA","create ticket"]
    if any(k in query_lower for k in rag_keywords):
        print(f"🔥 Rag node triggered with query: {str}")
        return "rag"
    elif any(k in query_lower for k in tool_keywords):
        print(f"🔥 MCP Chat node triggered with query: {str}")
        return "mcp"
    elif any(k in query_lower for k in jira_keywords):
        print(f"🔥 JIRA Chat node triggered with query: {str}")
        return "jira"
    else:
        print(f"🔥 Chat node triggered with query: {str}")
        return "chat"

def get_mcp_tool() -> StructuredTool:
    """Return MCP as a StructuredTool"""
    return StructuredTool.from_function(
        func=invoke_mcp,
        name="call_mcp_api",
        description="Call any MCP API endpoint and return JSON result",
        args_schema=MCPInvokeInput,
        coroutine=invoke_mcp,  # this marks it as async
    )

def get_jira_tool() -> StructuredTool:
    """Return MCP as a StructuredTool"""
    print(f"get_jira_tool =>> {get_jira_tool}")
    return StructuredTool.from_function(
        func=invoke_mcp_create_jira,
        name="create_jira_task",
        description="Create a Jira task. Expects fields summary, description_text, priority, issue_type, labels, assignee, client_request_id",
        args_schema=JiraIssueSpec,
        coroutine=invoke_mcp_create_jira
    )
