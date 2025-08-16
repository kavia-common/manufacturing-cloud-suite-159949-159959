import json
import os

from src.api.main import app

# Get the OpenAPI schema (note: all REST routes are under /api/v1)
openapi_schema = app.openapi()

# Ensure Reports tag metadata is present
tags = openapi_schema.get("tags", [])
if not any(t.get("name") == "Reports" for t in tags):
    tags.append({"name": "Reports", "description": "Exportable business reports (CSV/Excel/PDF)."})
openapi_schema["tags"] = tags

# Inject non-standard extension with WebSocket endpoint docs
openapi_schema["x-websocket-endpoints"] = [
    {
        "path": "/ws/dashboard",
        "summary": "Real-time dashboard KPI snapshots",
        "query": ["token"],
        "headers": ["X-Tenant-ID"],
        "messages": {"server_to_client": ["kpi.snapshot"]},
    },
    {
        "path": "/ws/scheduler",
        "summary": "Real-time collaborative scheduler board",
        "query": ["token", "board?"],
        "headers": ["X-Tenant-ID"],
        "messages": {
            "client_to_server": ["schedule.update", "operation.move", "operation.assign", "ping"],
            "server_to_client": ["scheduler.schedule.update", "scheduler.operation.move", "scheduler.operation.assign", "kpi.snapshot"],
        },
    },
]

# Write to file
output_dir = "interfaces"
os.makedirs(output_dir, exist_ok=True)
output_path = os.path.join(output_dir, "openapi.json")

with open(output_path, "w") as f:
    json.dump(openapi_schema, f, indent=2)
