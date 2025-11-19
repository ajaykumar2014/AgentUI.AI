def run(params: dict):
    """Simple addition and subtraction"""
    a = float(params.get("a", 0))
    b = float(params.get("b", 0))
    op = params.get("op", "add")
    if op == "add":
        return {"result": a + b + 10}
    elif op == "sub":
        return {"result": a - b+100}
    else:
        return {"error": "Unsupported op"}

TOOL_META = {
    "name": "math_tool",
    "description": "Perform basic arithmetic operations (add/sub)",
    "endpoint": "/invoke",
    "method": "POST",
}
