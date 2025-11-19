import json
import uuid

import httpx
from docutils.nodes import description

from fastapi import FastAPI, HTTPException, Query, Body
from langsmith import traceable
from loguru import logger
from typing import List, Dict, Any, Optional
import requests
from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel
from requests.auth import HTTPBasicAuth
from pydantic import BaseModel
from tools import uuid_tool,math_tool
from tools.jira_api_service import  JiraTool
from models import ToolInfo,InvokeRequest
from tools.jira_api_model import  JiraRouterRequest
app = FastAPI(title="MCP API Server", version="1.0")
mcp = FastMCP("MCP Server")

TOOLS = {
    uuid_tool.TOOL_META["name"]: uuid_tool,
    math_tool.TOOL_META["name"]: math_tool,

}
JIRA_BASE_URL = "https://agent-ui-ai.atlassian.net"  # e.g. https://your-domain.atlassian.net
JIRA_EMAIL = "ajay.jamiahamdard@gmail.com"
JIRA_API_TOKEN = "ATATT3xFfGF0KKWs_PbNLGm8T7VIvSGJ6Tg98FuGb36IRpBpwNFGbE0NYTVhGb0xX_DUHttQ8Q-ic7lBYwX34d5IhBrTyx4sutNJRcLWjybzmpA5UTxLm9R9TF3ZARSZhJ25ALQxHA79xXgmIjRyXSUHCoABCNJGPuIu-bXhS8jdIAd5w32MGcc=05D45BEB"
JIRA_PROJECT_KEY = "AG"

class CreateJiraRequest(BaseModel):
    payload: dict
    # summary: str
    # description: str
    # priority: Optional[str] = "Medium"
    # issue_type: Optional[str] = "Task"
    # labels: Optional[list[str]]| None = None
    # assignee: Optional[str] = None  # email or accountId depending on your Jira config
 # idempotency key (recommended)



@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/stocks/{symbol}",operation_id="stock_price")
@app.get("/stock/{symbol}",operation_id="stock_price")
@app.get("/stock/{symbol}/price",operation_id="stock_price")
@mcp.tool(name="get_stock_price",description="Get stock price")
def get_stock_price(symbol: str) -> dict:
    """
    Fetch latest stock price for a given symbol (e.g. 'AAPL', 'TSLA')
    using Alpha Vantage with API key in the URL.
    """
    url = f"https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol={symbol}&apikey=C9PE94QUEW9VWGFM"
    r = requests.get(url)
    return r.json()

@mcp.tool()
def calculator(first_num: float, second_num: float, operation: str) -> dict:
    """
    Perform a basic arithmetic operation on two numbers.
    Supported operations: add, sub, mul, div
    """
    try:
        if operation == "add":
            result = first_num + second_num
        elif operation == "sub":
            result = first_num - second_num
        elif operation == "mul":
            result = first_num * second_num
        elif operation == "div":
            if second_num == 0:
                return {"error": "Division by zero is not allowed"}
            result = first_num / second_num
        else:
            return {"error": f"Unsupported operation '{operation}'"}

        return {"first_num": first_num, "second_num": second_num, "operation": operation, "result": result}
    except Exception as e:
        return {"error": str(e)}


@app.get("/uuid/generate",operation_id="generate_uuid")
@mcp.tool("generate_uuid", description="Generate UUIDs")
def generate_uuid():
    return str(uuid.uuid4())
async def get_uuids(count: int = 1):
    return {"uuids": [str(uuid.uuid4()) for _ in range(count)]}

@app.get("/weather/{city}",operation_id="weather")
@mcp.tool("get_weather",description="Get weather data")
async def get_weather(city: str) -> dict:
    """
    Returns weather information for a given city.
    """
    print("Searching city...",city)
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(
            "https://api.openweathermap.org/data/2.5/weather",
            params={"q": city, "appid": '903cf87ba4566f790e8489ea401bb270', "units": "metric"}
        )
        print("response", resp.json())
        if resp.status_code != 200:
            return {"error": "City not found or API error"}

        data = resp.json()

        return {
            "city": city,
            "temperature": data["main"]["temp"],
            "feels_like": data["main"]["feels_like"],
            "humidity": data["main"]["humidity"],
            "weather": data["weather"][0]["description"],
        }


@app.get("/tools", response_model=List[ToolInfo])
def list_tools():
    """List all tools and metadata"""
    return [ToolInfo(**tool.TOOL_META) for tool in TOOLS.values()]

@app.post("/invoke")
def invoke_tool(req: InvokeRequest):
    """Invoke a registered tool by name"""
    tool = TOOLS.get(req.tool)
    if not tool:
        raise HTTPException(status_code=404, detail=f"Tool {req.tool} not found")
    logger.info(f"Invoking tool {req.tool} with params {req.params}")
    try:
        return tool.run(req.params)
    except Exception as e:
        logger.exception("Error invoking tool")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/publish")
def publish_event(event: dict):
    """Simulated publish event"""
    logger.info(f"Published event: {event}")
    return {"status": "published", "event": event}


# app.include_router(mcp.fastapi_router, prefix="/mcp")

@app.middleware("http")
async def auth_middleware(request, call_next, MCP_API_TOKEN="9fc250cbc543263fb9668728c3a9ea4b0b2df539"):
    if request.url.path not in ["/health"]:
        key = request.headers.get("x-api-key")
        if key != MCP_API_TOKEN:
            raise HTTPException(status_code=401, detail="Invalid API key")
    return await call_next(request)

def _to_adf(text: str) -> Dict[str, Any]:
    # simple convert: each non-empty line -> paragraph
    lines = text.splitlines() or [text]
    content = []
    for line in lines:
        if line.strip():
            content.append({"type": "paragraph", "content": [{"type": "text", "text": line}]})
    if not content:
        content = [{"type": "paragraph", "content": [{"type": "text", "text": ""}]}]
    return {"type": "doc", "version": 1, "content": content}


def _call_jira(payload: Dict[str, Any]) -> Dict[str, Any]:
    if not (JIRA_BASE_URL and JIRA_EMAIL and JIRA_API_TOKEN):
        raise RuntimeError("Jira configuration missing: set JIRA_BASE_URL, JIRA_EMAIL, JIRA_API_TOKEN")

    url = f"{JIRA_BASE_URL.rstrip('/')}/rest/api/3/issue"
    headers = {"Accept": "application/json", "Content-Type": "application/json"}
    resp = requests.post(url, json=payload, auth=HTTPBasicAuth(JIRA_EMAIL, JIRA_API_TOKEN), headers=headers, timeout=30)
    try:
        body = resp.json()
    except ValueError:
        body = {"raw": resp.text}
    return {"status_code": resp.status_code, "body": body}

# traceable will record calls in LangSmith if configured
@traceable(name="mcp.jira_action", tags=["jira", "tool"])
@app.post("/jira/tools/action")
async def jira_action(
    name: str = Query(..., description="Jira action name"),
    body: JiraRouterRequest = Body(...)
):
    """
        Unified Jira action processor.
        Example:
        POST /jira/tools/action?name=create_issue
        Body: { "params": { "summary": "...", "description": "..." } }
        """
    print(f"Jira action:<--*************************-> {name}:{body}")
    jira = JiraTool()
    ACTION_DISPATCHER = {
        "jira.create_issue": jira.create_issue,
        "jira.add_comment": jira.add_comment,
        "jira.fetch_issue": jira.get_issue,
        # "assign_issue": assign_issue,
        # Add more actions here:
        # "transition_workflow": transition_issue,
        # "get_issue": get_issue,
    }
    if name not in ACTION_DISPATCHER:
        raise HTTPException(status_code=400, detail=f"Unknown Jira action: {name}")
    print(f"Jira action=>>>:<--*************************-> {name}")
    handler = ACTION_DISPATCHER[name]
    # params = body.payload if body else {}
    # jira_req = JiraRouterRequest(**body.payload)
    print(f"jira_req:<--*************************-> {body.payload}")
    response = await handler(body.payload)
    return {"action": name, "result": response}


# traceable will record calls in LangSmith if configured
@traceable(name="mcp.create_jira_task", tags=["jira", "tool"])
@app.post("/tools/create_jira_task")
def create_jira_task(req: CreateJiraRequest):
    """
    Tool endpoint used by LLM agent to create Jira issues.
    Returns {"success": True, "issue_key": "PROJ-123"} or raises HTTPException on failure.
    """
    print(f"MCP calling create_jira_task {req}")
    try:
        adf = _to_adf(req.description)
        fields = {
            "project": {"key": JIRA_PROJECT_KEY},
            "summary": req.summary,
            "description": adf,
            "issuetype": {"name": req.issue_type or "Task"},
            "priority": {"name": req.priority or "Medium"},
        }
        if req.labels:
            fields["labels"] = req.labels
        if req.assignee:
            # depending on Jira instance, assignee field accepts accountId or name/email — adjust accordingly
            fields["assignee"] = {"name": req.assignee}  # older instances; modern Cloud likely use accountId
        payload = {"fields": fields}

        # Idempotency: if client_request_id provided, could store in DB/cache to prevent duplicates. For brevity omitted.
        result = _call_jira(payload)
        status = result["status_code"]
        body = result["body"]
        if status == 201:
            issue_key = body.get("key")
            return {"success": True, "issue_key": issue_key, "response": body}
        else:
            logger.error("Jira create failed: {} {}", status, body)
            raise HTTPException(status_code=500, detail={"message": "Jira create failed", "status": status, "body": body})
    except Exception as e:
        logger.exception("Exception creating Jira issue")
        raise HTTPException(status_code=500, detail={"message": str(e)})