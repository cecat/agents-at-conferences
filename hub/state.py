"""In-memory state for the hub. Replace with a database for production."""

from __future__ import annotations

import time
from collections import defaultdict
from datetime import datetime, timezone
from typing import Optional

from fastapi import WebSocket

from .models import (
    AgentMessage,
    AgentState,
    Acknowledgment,
    ConferenceSession,
    TranscriptChunk,
)


class HubState:
    """Holds all runtime state for the hub server."""

    def __init__(self):
        # Agent registry: token -> AgentState
        self.agents_by_token: dict[str, AgentState] = {}
        # Agent registry: agent_id -> AgentState
        self.agents_by_id: dict[str, AgentState] = {}

        # WebSocket connections: agent_id -> WebSocket
        self.connections: dict[str, WebSocket] = {}

        # Conference sessions: session_id -> ConferenceSession
        self.sessions: dict[str, ConferenceSession] = {}

        # Subscriptions: session_id -> set of agent_ids
        self.subscriptions: dict[str, set[str]] = defaultdict(set)
        # Hallway subscribers (all connected agents by default)
        self.hallway_subscribers: set[str] = set()

        # Message history: session_id -> list of AgentMessage
        # "" key = hallway
        self.messages: dict[str, list[AgentMessage]] = defaultdict(list)

        # Transcript history: session_id -> list of TranscriptChunk
        self.transcripts: dict[str, list[TranscriptChunk]] = defaultdict(list)

        # Acknowledgments: message_id -> list of Acknowledgment
        self.acks: dict[str, list[Acknowledgment]] = defaultdict(list)

        # Rate limiting: agent_id -> list of timestamps (last N messages)
        self.rate_limits: dict[str, list[float]] = defaultdict(list)

    # --- Agent management ---

    def register_agent(self, agent_state: AgentState) -> None:
        self.agents_by_token[agent_state.token] = agent_state
        self.agents_by_id[agent_state.profile.id] = agent_state

    def get_agent_by_token(self, token: str) -> Optional[AgentState]:
        return self.agents_by_token.get(token)

    def get_agent_by_id(self, agent_id: str) -> Optional[AgentState]:
        return self.agents_by_id.get(agent_id)

    def connect_agent(self, agent_id: str, ws: WebSocket) -> None:
        self.connections[agent_id] = ws
        agent = self.agents_by_id.get(agent_id)
        if agent:
            agent.connected = True
            agent.connected_at = datetime.now(timezone.utc)
        self.hallway_subscribers.add(agent_id)

    def disconnect_agent(self, agent_id: str) -> None:
        self.connections.pop(agent_id, None)
        agent = self.agents_by_id.get(agent_id)
        if agent:
            agent.connected = False
        # Remove from all subscriptions
        for session_id in list(self.subscriptions.keys()):
            self.subscriptions[session_id].discard(agent_id)
        self.hallway_subscribers.discard(agent_id)

    def get_connected_agents(self) -> list[AgentState]:
        return [a for a in self.agents_by_id.values() if a.connected]

    def get_all_agents(self) -> list[AgentState]:
        return list(self.agents_by_id.values())

    # --- Session management ---

    def add_session(self, session: ConferenceSession) -> None:
        self.sessions[session.id] = session

    def get_sessions(self) -> list[ConferenceSession]:
        return list(self.sessions.values())

    # --- Subscriptions ---

    def subscribe(self, agent_id: str, session_id: str) -> bool:
        if session_id not in self.sessions:
            return False
        self.subscriptions[session_id].add(agent_id)
        agent = self.agents_by_id.get(agent_id)
        if agent and session_id not in agent.subscriptions:
            agent.subscriptions.append(session_id)
        return True

    def unsubscribe(self, agent_id: str, session_id: str) -> None:
        self.subscriptions[session_id].discard(agent_id)
        agent = self.agents_by_id.get(agent_id)
        if agent and session_id in agent.subscriptions:
            agent.subscriptions.remove(session_id)

    def get_subscribers(self, session_id: str) -> set[str]:
        return self.subscriptions.get(session_id, set())

    # --- Messages ---

    def add_message(self, msg: AgentMessage) -> None:
        channel = msg.session_id or ""
        self.messages[channel].append(msg)
        agent = self.agents_by_id.get(msg.from_agent)
        if agent:
            agent.message_count += 1
            agent.last_message_at = msg.timestamp

    def get_messages(self, session_id: str = "", limit: int = 50, before: Optional[str] = None) -> list[AgentMessage]:
        channel = session_id or ""
        msgs = self.messages.get(channel, [])
        if before:
            idx = next((i for i, m in enumerate(msgs) if m.id == before), len(msgs))
            msgs = msgs[:idx]
        return msgs[-limit:]

    # --- Transcripts ---

    def add_transcript(self, chunk: TranscriptChunk) -> None:
        self.transcripts[chunk.session_id].append(chunk)

    def get_transcript(self, session_id: str, limit: int = 100) -> list[TranscriptChunk]:
        return self.transcripts.get(session_id, [])[-limit:]

    # --- Acknowledgments ---

    def add_ack(self, ack: Acknowledgment) -> None:
        self.acks[ack.message_id].append(ack)

    def get_ack_count(self, message_id: str) -> int:
        return len(self.acks.get(message_id, []))

    # --- Rate limiting ---

    def check_rate_limit(self, agent_id: str, max_per_minute: int = 5) -> bool:
        """Returns True if the agent is within rate limits."""
        now = time.time()
        timestamps = self.rate_limits[agent_id]
        # Prune old entries
        self.rate_limits[agent_id] = [t for t in timestamps if now - t < 60]
        return len(self.rate_limits[agent_id]) < max_per_minute

    def record_message(self, agent_id: str) -> None:
        self.rate_limits[agent_id].append(time.time())


# Global singleton
hub = HubState()
