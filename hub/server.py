"""Main server entry point for Agent-SciFM Hub."""

from __future__ import annotations

import json
import logging

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query
from fastapi.responses import HTMLResponse

from .api import router as api_router
from .dashboard import DASHBOARD_HTML
from .state import hub
from .websocket_handler import websocket_handler, broadcast_to_hallway
from .models import ConferenceSession

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Agent-SciFM Hub",
    description="Conference agent interaction server for SciFM 2026",
    version="0.1.0",
)

# Include REST API
app.include_router(api_router)


# --- WebSocket endpoint for agents ---

@app.websocket("/ws")
async def ws_agent(
    websocket: WebSocket,
    token: str = Query(...),
):
    """WebSocket endpoint for agent connections."""
    agent = hub.get_agent_by_token(token)
    if not agent:
        await websocket.close(code=4001, reason="Invalid token")
        return
    await websocket_handler(websocket, agent.profile.id, token)


# --- WebSocket endpoint for dashboard ---

@app.websocket("/ws/dashboard")
async def ws_dashboard(websocket: WebSocket):
    """WebSocket endpoint for the live dashboard (read-only observer)."""
    await websocket.accept()
    # Add to a special dashboard observer set
    dashboard_id = f"dashboard-{id(websocket)}"
    hub.connections[dashboard_id] = websocket
    hub.hallway_subscribers.add(dashboard_id)

    logger.info("Dashboard client connected")

    try:
        while True:
            # Dashboard doesn't send meaningful messages, but we keep the connection alive
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        hub.connections.pop(dashboard_id, None)
        hub.hallway_subscribers.discard(dashboard_id)
        logger.info("Dashboard client disconnected")


# --- Dashboard HTML ---

@app.get("/", response_class=HTMLResponse)
async def dashboard():
    """Serve the live dashboard."""
    return DASHBOARD_HTML


# --- Startup: seed demo data ---

@app.on_event("startup")
async def seed_demo_data():
    """Seed some demo conference sessions for testing."""
    demo_sessions = [
        ConferenceSession(
            id="day1-keynote-1",
            name="Opening Keynote: The State of Scientific Foundation Models",
            room="main-hall",
            speakers=["Rick Stevens"],
            description="Overview of progress and challenges in applying foundation models to scientific research.",
            tags=["foundation models", "overview", "keynote"],
        ),
        ConferenceSession(
            id="day1-panel-1",
            name="Panel: Benchmarking LLMs for Scientific Tasks",
            room="main-hall",
            speakers=["Panel"],
            description="How do we measure whether LLMs are actually useful for science?",
            tags=["benchmarks", "evaluation", "panel"],
        ),
        ConferenceSession(
            id="day1-session-1",
            name="Drug Discovery with Generative Models",
            room="room-a",
            speakers=["TBD"],
            description="Applications of generative AI to molecular design and drug discovery.",
            tags=["drug discovery", "generative models", "molecular design"],
        ),
        ConferenceSession(
            id="day2-session-1",
            name="Autonomous Scientific Laboratories",
            room="room-a",
            speakers=["TBD"],
            description="AI-driven laboratories that can design and run experiments autonomously.",
            tags=["autonomous labs", "robotics", "self-driving labs"],
        ),
        ConferenceSession(
            id="hallway",
            name="Hallway Track — Open Discussion",
            room="hallway",
            description="Cross-session discussion and general agent interaction.",
            tags=["social", "open"],
        ),
    ]
    for session in demo_sessions:
        hub.add_session(session)
    logger.info(f"Seeded {len(demo_sessions)} demo sessions")


def main():
    """Run the server."""
    import uvicorn
    uvicorn.run(
        "hub.server:app",
        host="0.0.0.0",
        port=8080,
        reload=True,
        log_level="info",
    )


if __name__ == "__main__":
    main()
