import uuid

import httpx
from chromadb.api.types import QueryRequest
from fastapi import FastAPI, HTTPException
from loguru import logger
from typing import List
import requests
from mcp.server.fastmcp import FastMCP
from tools import uuid_tool,math_tool
from models import ToolInfo,InvokeRequest

# from dotenv import load_dotenv
# import os
#
#
# env_path = Path(__file__).parent / ".env"
# print(env_path)
# load_dotenv(dotenv_path=env_path)
#
# MCP_API_BASE = os.getenv("MCP_API_BASE")
# MCP_API_TOKEN = os.getenv("MCP_API_TOKEN")

app = FastAPI(title="MCP API Server", version="1.0")
mcp = FastMCP("MCP Server")

TOOLS = {
    uuid_tool.TOOL_META["name"]: uuid_tool,
    math_tool.TOOL_META["name"]: math_tool,

}

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
