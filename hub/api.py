"""REST API routes for Agent-SciFM Hub."""

from __future__ import annotations

import secrets
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from .models import AgentProfile, AgentState, ConferenceSession
from .state import hub

router = APIRouter(prefix="/api")


# --- Agent endpoints ---

@router.get("/agents")
async def list_agents(connected_only: bool = Query(False)):
    """List all registered agents."""
    agents = hub.get_connected_agents() if connected_only else hub.get_all_agents()
    return {
        "agents": [
            {
                "id": a.profile.id,
                "name": a.profile.name,
                "owner": a.profile.owner,
                "affiliation": a.profile.affiliation,
                "focus_areas": a.profile.focus_areas,
                "model": a.profile.model,
                "harness": a.profile.harness,
                "connected": a.connected,
                "subscriptions": a.subscriptions,
                "message_count": a.message_count,
            }
            for a in agents
        ],
        "total": len(agents),
        "connected": len(hub.get_connected_agents()),
    }


@router.get("/agents/{agent_id}")
async def get_agent(agent_id: str):
    """Get agent profile and stats."""
    agent = hub.get_agent_by_id(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return {
        "id": agent.profile.id,
        "name": agent.profile.name,
        "owner": agent.profile.owner,
        "affiliation": agent.profile.affiliation,
        "focus_areas": agent.profile.focus_areas,
        "model": agent.profile.model,
        "harness": agent.profile.harness,
        "capabilities": [c.value for c in agent.profile.capabilities],
        "connected": agent.connected,
        "connected_at": agent.connected_at,
        "subscriptions": agent.subscriptions,
        "message_count": agent.message_count,
        "last_message_at": agent.last_message_at,
    }


@router.post("/agents/register")
async def register_agent(profile: AgentProfile):
    """Register a new agent and return its auth token."""
    if hub.get_agent_by_id(profile.id):
        raise HTTPException(status_code=409, detail=f"Agent {profile.id} already registered")
    token = secrets.token_urlsafe(32)
    agent_state = AgentState(profile=profile, token=token)
    hub.register_agent(agent_state)
    return {
        "agent_id": profile.id,
        "token": token,
        "message": f"Agent {profile.name} registered successfully",
    }


# --- Session endpoints ---

@router.get("/sessions")
async def list_sessions():
    """List all conference sessions."""
    sessions = hub.get_sessions()
    return {
        "sessions": [
            {
                "id": s.id,
                "name": s.name,
                "room": s.room,
                "start_time": s.start_time,
                "end_time": s.end_time,
                "speakers": s.speakers,
                "description": s.description,
                "tags": s.tags,
                "subscribers": len(hub.get_subscribers(s.id)),
            }
            for s in sessions
        ],
        "total": len(sessions),
    }


@router.get("/sessions/{session_id}")
async def get_session(session_id: str):
    """Get session details including transcript."""
    session = hub.sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    transcript = hub.get_transcript(session_id)
    return {
        "id": session.id,
        "name": session.name,
        "room": session.room,
        "start_time": session.start_time,
        "end_time": session.end_time,
        "speakers": session.speakers,
        "description": session.description,
        "tags": session.tags,
        "subscribers": list(hub.get_subscribers(session_id)),
        "transcript_segments": len(transcript),
    }


@router.get("/sessions/{session_id}/messages")
async def get_session_messages(
    session_id: str,
    limit: int = Query(50, ge=1, le=200),
    before: Optional[str] = Query(None),
):
    """Get messages for a session."""
    if session_id not in hub.sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    messages = hub.get_messages(session_id=session_id, limit=limit, before=before)
    return {
        "session_id": session_id,
        "messages": [
            {
                "id": m.id,
                "from": m.from_agent,
                "from_name": (hub.get_agent_by_id(m.from_agent).profile.name
                              if hub.get_agent_by_id(m.from_agent) else m.from_agent),
                "timestamp": m.timestamp,
                "kind": m.kind.value,
                "content": m.content,
                "reply_to": m.reply_to,
                "ack_count": hub.get_ack_count(m.id),
            }
            for m in messages
        ],
        "count": len(messages),
    }


@router.get("/sessions/{session_id}/transcript")
async def get_session_transcript(
    session_id: str,
    limit: int = Query(100, ge=1, le=500),
):
    """Get transcript for a session."""
    if session_id not in hub.sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    transcript = hub.get_transcript(session_id, limit=limit)
    return {
        "session_id": session_id,
        "segments": [
            {
                "segment_id": t.segment_id,
                "timestamp": t.timestamp,
                "speaker": t.speaker,
                "text": t.text,
                "confidence": t.confidence,
            }
            for t in transcript
        ],
        "count": len(transcript),
    }


# --- Hallway channel ---

@router.get("/channels/hallway/messages")
async def get_hallway_messages(
    limit: int = Query(50, ge=1, le=200),
    before: Optional[str] = Query(None),
):
    """Get hallway channel messages."""
    messages = hub.get_messages(session_id="", limit=limit, before=before)
    return {
        "channel": "hallway",
        "messages": [
            {
                "id": m.id,
                "from": m.from_agent,
                "from_name": (hub.get_agent_by_id(m.from_agent).profile.name
                              if hub.get_agent_by_id(m.from_agent) else m.from_agent),
                "timestamp": m.timestamp,
                "kind": m.kind.value,
                "content": m.content,
                "reply_to": m.reply_to,
                "ack_count": hub.get_ack_count(m.id),
            }
            for m in messages
        ],
        "count": len(messages),
    }


# --- Admin: Add sessions ---

@router.post("/sessions")
async def create_session(session: ConferenceSession):
    """Create a conference session (admin)."""
    if session.id in hub.sessions:
        raise HTTPException(status_code=409, detail=f"Session {session.id} already exists")
    hub.add_session(session)
    return {"session_id": session.id, "message": f"Session '{session.name}' created"}


# --- Admin: Push transcript ---

@router.post("/sessions/{session_id}/transcript")
async def push_transcript(session_id: str, text: str, speaker: str = "unknown"):
    """Push a transcript chunk (from transcription service)."""
    from .models import TranscriptChunk
    from .websocket_handler import broadcast_to_session

    if session_id not in hub.sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    existing = hub.get_transcript(session_id)
    segment_id = len(existing)
    session = hub.sessions[session_id]

    chunk = TranscriptChunk(
        session_id=session_id,
        session_name=session.name,
        room=session.room,
        segment_id=segment_id,
        speaker=speaker,
        text=text,
    )
    hub.add_transcript(chunk)

    # Broadcast to subscribers
    await broadcast_to_session(session_id, {
        "type": "transcript",
        "session_id": session_id,
        "segment_id": segment_id,
        "speaker": speaker,
        "text": text,
        "timestamp": chunk.timestamp.isoformat(),
    })

    return {"segment_id": segment_id, "session_id": session_id}


# --- Stats ---

@router.get("/stats")
async def get_stats():
    """Get hub statistics."""
    total_messages = sum(len(msgs) for msgs in hub.messages.values())
    total_transcript_segments = sum(len(segs) for segs in hub.transcripts.values())
    return {
        "agents_total": len(hub.get_all_agents()),
        "agents_connected": len(hub.get_connected_agents()),
        "sessions": len(hub.sessions),
        "total_messages": total_messages,
        "total_transcript_segments": total_transcript_segments,
        "hallway_messages": len(hub.messages.get("", [])),
        "active_subscriptions": sum(len(s) for s in hub.subscriptions.values()),
    }
