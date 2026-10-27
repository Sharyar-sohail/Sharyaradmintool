"""
ApexSys Backend Server & Real-time Command Hub
FastAPI web application orchestrating WebSocket connections for agents & dashboard,
providing REST management APIs, and serving the Futuristic Master IT Commander UI.
"""

import asyncio
import json
import os
import time
from typing import Any, Dict, List, Optional, Set
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from backend.node_manager import node_manager
from backend.remediation_engine import remediation_engine, RemediationCatalog
from backend.security import security_engine

app = FastAPI(
    title="ApexSys Autonomous Remote IT Commander",
    description="Enterprise-grade Master IT Doctor & Autonomous Deep Remediation Platform",
    version="2.0-APEX",
)

# Enable CORS for cross-origin management / companion dashboards
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Directory paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")

# Dashboard WebSocket subscribers
dashboard_sockets: Set[WebSocket] = set()


class CommandRequest(BaseModel):
    action: str
    params: Optional[Dict[str, Any]] = None


async def broadcast_to_dashboards(message: Dict[str, Any]):
    """Broadcast real-time updates to all connected browser dashboards."""
    if not dashboard_sockets:
        return
    text = json.dumps(message)
    dead_sockets = set()
    for ws in dashboard_sockets:
        try:
            await ws.send_text(text)
        except Exception:
            dead_sockets.add(ws)
    for ws in dead_sockets:
        dashboard_sockets.discard(ws)


# ---------------- REST ENDPOINTS ----------------

@app.get("/api/health")
async def health_check():
    return {
        "status": "ONLINE",
        "service": "ApexSys Remote IT Commander",
        "version": "2.0-APEX",
        "timestamp": time.time(),
        "connected_nodes": len(node_manager._nodes),
    }


@app.get("/api/catalog")
async def get_remediation_catalog():
    """Returns available remediation actions and metadata."""
    return {"tasks": RemediationCatalog.TASKS}


@app.get("/api/nodes")
async def list_nodes():
    """List all registered client endpoints."""
    return {"nodes": node_manager.list_nodes()}


@app.get("/api/nodes/{client_id}")
async def get_node_detail(client_id: str):
    """Retrieve exhaustive diagnostics, issues, telemetry, and terminal logs for a node."""
    node = node_manager.get(client_id)
    if not node:
        raise HTTPException(status_code=404, detail="Client node not found.")
    return node.to_detail()


@app.post("/api/nodes/{client_id}/scan")
async def trigger_scan(client_id: str):
    """Dispatch an on-demand Master Scan command."""
    node = node_manager.get(client_id)
    if not node or not node.websocket:
        raise HTTPException(status_code=400, detail="Target node is offline or disconnected.")

    success = await remediation_engine.dispatch_command(node, "SCAN_MASTER")
    if not success:
        raise HTTPException(status_code=500, detail="Failed to dispatch scan payload.")

    await broadcast_to_dashboards({
        "event": "NODE_STATUS_CHANGE",
        "client_id": client_id,
        "status": "SCANNING",
    })
    return {"status": "SUCCESS", "message": "Master Scan command dispatched."}


@app.post("/api/nodes/{client_id}/remediate")
async def execute_remediation(client_id: str, cmd: CommandRequest):
    """Dispatch a targeted remediation action."""
    node = node_manager.get(client_id)
    if not node or not node.websocket:
        raise HTTPException(status_code=400, detail="Target node is offline or disconnected.")

    action = cmd.action
    if action not in RemediationCatalog.TASKS and not action.startswith("FIX_KILL_PROCESS"):
        raise HTTPException(status_code=400, detail=f"Unrecognized remediation action: {action}")

    success = await remediation_engine.dispatch_command(node, action, cmd.params)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to dispatch remediation command.")

    await broadcast_to_dashboards({
        "event": "REMEDIATION_STARTED",
        "client_id": client_id,
        "action": action,
    })
    return {"status": "SUCCESS", "action": action, "message": "Remediation dispatched."}


@app.post("/api/nodes/{client_id}/fix-all")
async def execute_fix_all(client_id: str):
    """One-Click Master Remediation: sequences all fixes followed by verification scan."""
    node = node_manager.get(client_id)
    if not node or not node.websocket:
        raise HTTPException(status_code=400, detail="Target node is offline or disconnected.")

    success = await remediation_engine.dispatch_command(node, "FIX_ALL")
    if not success:
        raise HTTPException(status_code=500, detail="Failed to dispatch Fix All pipeline.")

    await broadcast_to_dashboards({
        "event": "REMEDIATION_STARTED",
        "client_id": client_id,
        "action": "FIX_ALL",
    })
    return {"status": "SUCCESS", "message": "Autonomous Master Remediation pipeline engaged."}


@app.post("/api/nodes/{client_id}/self-destruct")
async def trigger_self_destruct(client_id: str):
    """Triggers secure multi-pass wipe and zero-footprint uninstallation."""
    node = node_manager.get(client_id)
    if not node or not node.websocket:
        raise HTTPException(status_code=400, detail="Target node is offline or disconnected.")

    success = await remediation_engine.dispatch_command(node, "SELF_DESTRUCT")
    if not success:
        raise HTTPException(status_code=500, detail="Failed to dispatch Self-Destruct protocol.")

    return {"status": "SUCCESS", "message": "Self-Destruct payload verified and dispatched."}


# ---------------- WEBSOCKET ENDPOINTS ----------------

@app.websocket("/ws/dashboard")
async def websocket_dashboard(websocket: WebSocket):
    """WebSocket endpoint for real-time dashboard UI clients."""
    await websocket.accept()
    dashboard_sockets.add(websocket)
    try:
        # Push initial fleet state
        initial_state = {
            "event": "FLEET_SNAPSHOT",
            "nodes": node_manager.list_nodes(),
        }
        await websocket.send_text(json.dumps(initial_state))

        while True:
            # Keep-alive ping/pong
            msg = await websocket.receive_text()
            if msg == "ping":
                await websocket.send_text("pong")
    except (WebSocketDisconnect, asyncio.CancelledError):
        pass
    finally:
        dashboard_sockets.discard(websocket)


@app.websocket("/ws/agent/{client_id}")
async def websocket_agent(websocket: WebSocket, client_id: str):
    """WebSocket endpoint for client agents (Python or PowerShell)."""
    await websocket.accept()
    node = node_manager.get_or_create(client_id, websocket)
    node.status = "ONLINE"

    await broadcast_to_dashboards({
        "event": "NODE_CONNECTED",
        "client_id": client_id,
        "node": node.to_summary(),
    })

    try:
        while True:
            raw_text = await websocket.receive_text()
            try:
                msg = json.loads(raw_text)
            except Exception:
                continue

            msg_type = msg.get("type")

            if msg_type == "HANDSHAKE":
                node.system_info = msg.get("system_info", node.system_info)
                node.last_seen = time.time()
                await broadcast_to_dashboards({
                    "event": "NODE_UPDATED",
                    "client_id": client_id,
                    "node": node.to_summary(),
                })

            elif msg_type == "TELEMETRY":
                telemetry_data = msg.get("data", {})
                node.update_telemetry(telemetry_data)
                await broadcast_to_dashboards({
                    "event": "TELEMETRY_TICK",
                    "client_id": client_id,
                    "telemetry": telemetry_data,
                })

            elif msg_type == "DIAGNOSTIC_REPORT":
                report = msg.get("data", {})
                node.process_diagnostics(report)
                node.status = "ONLINE"
                node.active_task = None
                await broadcast_to_dashboards({
                    "event": "DIAGNOSTICS_UPDATED",
                    "client_id": client_id,
                    "health_score": node.health_score,
                    "category_scores": node.category_scores,
                    "issues": node.issues,
                    "node": node.to_summary(),
                })

            elif msg_type == "TERMINAL_LOG":
                stream = msg.get("stream", "stdout")
                text = msg.get("text", "")
                node.append_terminal_log(text, stream)
                await broadcast_to_dashboards({
                    "event": "TERMINAL_STREAM",
                    "client_id": client_id,
                    "stream": stream,
                    "text": text,
                    "ts": time.strftime("%H:%M:%S"),
                })

            elif msg_type == "REMEDIATION_PROGRESS":
                pct = msg.get("progress", 0)
                action = msg.get("action", "")
                node.remediation_progress = pct
                await broadcast_to_dashboards({
                    "event": "REMEDIATION_PROGRESS",
                    "client_id": client_id,
                    "progress": pct,
                    "action": action,
                })

            elif msg_type == "VERIFICATION_COMPLETE":
                report = msg.get("report", {})
                node.process_diagnostics(report)
                node.status = "ONLINE"
                node.active_task = None
                node.post_repair_score = node.health_score
                delta_report = remediation_engine.compute_verification_delta(node)

                await broadcast_to_dashboards({
                    "event": "VERIFICATION_COMPLETE",
                    "client_id": client_id,
                    "delta": delta_report,
                    "node": node.to_detail(),
                })

            elif msg_type == "SELF_DESTRUCT_INITIATED":
                node.status = "OFFLINE"
                await broadcast_to_dashboards({
                    "event": "NODE_SELF_DESTRUCTED",
                    "client_id": client_id,
                })
                node_manager.remove_node(client_id)
                break

    except (WebSocketDisconnect, asyncio.CancelledError):
        pass
    finally:
        node.websocket = None
        node.status = "OFFLINE"
        await broadcast_to_dashboards({
            "event": "NODE_DISCONNECTED",
            "client_id": client_id,
        })


# Mount Static Files & Web Dashboard
if os.path.exists(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/")
async def root():
    index_file = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    return {"message": "ApexSys Remote IT Commander Backend Online"}
