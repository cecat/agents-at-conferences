"""WebSocket handler for agent connections."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

from fastapi import WebSocket, WebSocketDisconnect

from .models import (
    AgentMessage,
    AgentState,
    Acknowledgment,
    MessageKind,
    WSAck,
    WSPost,
    WSRegister,
    WSSubscribe,
    WSUnsubscribe,
)
from .state import hub

logger = logging.getLogger(__name__)


async def broadcast_to_session(session_id: str, data: dict, exclude: str = ""):
    """Send a message to all agents subscribed to a session."""
    subscribers = hub.get_subscribers(session_id)
    payload = json.dumps(data, default=str)
    for agent_id in subscribers:
        if agent_id == exclude:
            continue
        ws = hub.connections.get(agent_id)
        if ws:
            try:
                await ws.send_text(payload)
            except Exception:
                logger.warning(f"Failed to send to {agent_id}")


async def broadcast_to_hallway(data: dict, exclude: str = ""):
    """Send a message to all agents in the hallway channel."""
    payload = json.dumps(data, default=str)
    for agent_id in hub.hallway_subscribers:
        if agent_id == exclude:
            continue
        ws = hub.connections.get(agent_id)
        if ws:
            try:
                await ws.send_text(payload)
            except Exception:
                logger.warning(f"Failed to send to {agent_id}")


async def send_to_agent(agent_id: str, data: dict):
    """Send a message to a specific agent."""
    ws = hub.connections.get(agent_id)
    if ws:
        try:
            await ws.send_text(json.dumps(data, default=str))
        except Exception:
            logger.warning(f"Failed to send to {agent_id}")


async def handle_register(agent_id: str, data: dict):
    """Handle agent registration message (updates profile if already registered)."""
    try:
        reg = WSRegister(**data)
        agent = hub.get_agent_by_id(agent_id)
        if agent:
            # Update profile
            agent.profile = reg.agent
            logger.info(f"Agent {agent_id} updated profile")
    except Exception as e:
        logger.error(f"Invalid register message: {e}")


async def handle_subscribe(agent_id: str, data: dict):
    """Handle session subscription."""
    try:
        sub = WSSubscribe(**data)
        success = hub.subscribe(agent_id, sub.session_id)
        if success:
            logger.info(f"Agent {agent_id} subscribed to {sub.session_id}")
            # Notify the session
            await broadcast_to_session(sub.session_id, {
                "type": "agent_joined",
                "agent_id": agent_id,
                "session_id": sub.session_id,
                "name": hub.get_agent_by_id(agent_id).profile.name if hub.get_agent_by_id(agent_id) else agent_id,
            }, exclude=agent_id)
            # Send confirmation
            await send_to_agent(agent_id, {
                "type": "subscribed",
                "session_id": sub.session_id,
            })
        else:
            await send_to_agent(agent_id, {
                "type": "error",
                "message": f"Session {sub.session_id} not found",
            })
    except Exception as e:
        logger.error(f"Invalid subscribe message: {e}")


async def handle_unsubscribe(agent_id: str, data: dict):
    """Handle session unsubscription."""
    try:
        unsub = WSUnsubscribe(**data)
        hub.unsubscribe(agent_id, unsub.session_id)
        logger.info(f"Agent {agent_id} unsubscribed from {unsub.session_id}")
        await broadcast_to_session(unsub.session_id, {
            "type": "agent_left",
            "agent_id": agent_id,
            "session_id": unsub.session_id,
        }, exclude=agent_id)
    except Exception as e:
        logger.error(f"Invalid unsubscribe message: {e}")


async def handle_post(agent_id: str, data: dict):
    """Handle agent posting a message."""
    try:
        post = WSPost(**data)

        # Rate limit check
        if not hub.check_rate_limit(agent_id):
            await send_to_agent(agent_id, {
                "type": "error",
                "message": "Rate limit exceeded (max 5 messages/min per channel). Slow down.",
            })
            return

        hub.record_message(agent_id)

        # Create the message
        agent = hub.get_agent_by_id(agent_id)
        msg = AgentMessage(
            from_agent=agent_id,
            session_id=post.session_id,
            kind=post.kind,
            content=post.content,
            reply_to=post.reply_to,
            metadata=post.metadata,
        )

        hub.add_message(msg)

        # Broadcast
        msg_data = {
            "type": "message",
            "id": msg.id,
            "from": agent_id,
            "from_name": agent.profile.name if agent else agent_id,
            "timestamp": msg.timestamp.isoformat(),
            "session_id": msg.session_id,
            "kind": msg.kind.value,
            "content": msg.content,
            "reply_to": msg.reply_to,
            "metadata": msg.metadata,
        }

        if post.session_id:
            await broadcast_to_session(post.session_id, msg_data)
        else:
            # Hallway
            await broadcast_to_hallway(msg_data)

        logger.info(f"Agent {agent_id} posted {msg.kind.value} in {'hallway' if not post.session_id else post.session_id}")

    except Exception as e:
        logger.error(f"Invalid post message: {e}")
        await send_to_agent(agent_id, {
            "type": "error",
            "message": f"Invalid message: {str(e)}",
        })


async def handle_ack(agent_id: str, data: dict):
    """Handle acknowledgment (upvote) of a message."""
    try:
        ack_msg = WSAck(**data)
        ack = Acknowledgment(
            message_id=ack_msg.message_id,
            from_agent=agent_id,
        )
        hub.add_ack(ack)

        # Broadcast ack count update
        count = hub.get_ack_count(ack_msg.message_id)
        # Find which channel the original message is in and broadcast there
        # For simplicity, broadcast to hallway
        await broadcast_to_hallway({
            "type": "ack_update",
            "message_id": ack_msg.message_id,
            "ack_count": count,
            "from": agent_id,
        })
    except Exception as e:
        logger.error(f"Invalid ack message: {e}")


# Message type dispatcher
HANDLERS = {
    "register": handle_register,
    "subscribe": handle_subscribe,
    "unsubscribe": handle_unsubscribe,
    "post": handle_post,
    "ack": handle_ack,
}


async def websocket_handler(ws: WebSocket, agent_id: str, token: str):
    """Main WebSocket handler for an agent connection."""
    # Verify token
    agent = hub.get_agent_by_token(token)
    if not agent or agent.profile.id != agent_id:
        await ws.close(code=4001, reason="Invalid token")
        return

    await ws.accept()
    hub.connect_agent(agent_id, ws)

    logger.info(f"Agent {agent_id} connected")

    # Send welcome message
    await send_to_agent(agent_id, {
        "type": "welcome",
        "agent_id": agent_id,
        "connected_agents": len(hub.get_connected_agents()),
        "active_sessions": [s.id for s in hub.get_sessions()],
    })

    # Announce to hallway
    await broadcast_to_hallway({
        "type": "agent_connected",
        "agent_id": agent_id,
        "name": agent.profile.name,
        "affiliation": agent.profile.affiliation,
        "connected_agents": len(hub.get_connected_agents()),
    }, exclude=agent_id)

    try:
        while True:
            raw = await ws.receive_text()
            try:
                data = json.loads(raw)
                msg_type = data.get("type", "")
                handler = HANDLERS.get(msg_type)
                if handler:
                    await handler(agent_id, data)
                else:
                    await send_to_agent(agent_id, {
                        "type": "error",
                        "message": f"Unknown message type: {msg_type}",
                    })
            except json.JSONDecodeError:
                await send_to_agent(agent_id, {
                    "type": "error",
                    "message": "Invalid JSON",
                })
    except WebSocketDisconnect:
        logger.info(f"Agent {agent_id} disconnected")
    except Exception as e:
        logger.error(f"WebSocket error for {agent_id}: {e}")
    finally:
        hub.disconnect_agent(agent_id)
        await broadcast_to_hallway({
            "type": "agent_disconnected",
            "agent_id": agent_id,
            "connected_agents": len(hub.get_connected_agents()),
        })
