import uuid

def run(params: dict):
    """Generate UUIDs"""
    count = params.get("count", 1)
    return {"uuids": [str(uuid.uuid4()) for _ in range(count)]}

TOOL_META = {
    "name": "uuid_generator",
    "description": "Generate one or more UUID values",
    "endpoint": "/invoke",
    "method": "POST",
}
