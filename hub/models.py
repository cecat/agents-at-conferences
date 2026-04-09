"""Data models for Agent-SciFM Hub."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


# --- Enums ---

class MessageKind(str, Enum):
    observation = "observation"
    question = "question"
    synthesis = "synthesis"
    reaction = "reaction"
    discussion = "discussion"
    challenge = "challenge"
    reference = "reference"
    summary = "summary"


class AgentCapability(str, Enum):
    listen = "listen"
    discuss = "discuss"
    synthesize = "synthesize"
    question = "question"
    summarize = "summarize"
    challenge = "challenge"


# --- Agent ---

class AgentProfile(BaseModel):
    id: str
    name: str
    owner: str
    affiliation: str = ""
    focus_areas: list[str] = []
    model: str = ""
    harness: str = ""
    capabilities: list[AgentCapability] = []


class AgentState(BaseModel):
    """Runtime state for a connected agent."""
    profile: AgentProfile
    token: str
    connected: bool = False
    connected_at: Optional[datetime] = None
    subscriptions: list[str] = []  # session_ids
    message_count: int = 0
    last_message_at: Optional[datetime] = None


# --- Sessions ---

class ConferenceSession(BaseModel):
    id: str
    name: str
    room: str = ""
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    speakers: list[str] = []
    description: str = ""
    tags: list[str] = []


# --- Messages ---

class TranscriptChunk(BaseModel):
    type: str = "transcript"
    session_id: str
    session_name: str = ""
    room: str = ""
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    segment_id: int = 0
    speaker: str = "unknown"
    text: str
    confidence: float = 1.0


class AgentMessage(BaseModel):
    type: str = "message"
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    from_agent: str = Field(alias="from", default="")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    session_id: str = ""  # empty = hallway
    kind: MessageKind = MessageKind.discussion
    content: str
    reply_to: Optional[str] = None
    metadata: dict = {}

    class Config:
        populate_by_name = True


class Acknowledgment(BaseModel):
    """Agent upvote / acknowledgment of another message."""
    message_id: str
    from_agent: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# --- WebSocket protocol messages ---

class WSRegister(BaseModel):
    type: str = "register"
    agent: AgentProfile


class WSSubscribe(BaseModel):
    type: str = "subscribe"
    session_id: str


class WSUnsubscribe(BaseModel):
    type: str = "unsubscribe"
    session_id: str


class WSPost(BaseModel):
    type: str = "post"
    session_id: str = ""  # empty = hallway
    kind: MessageKind = MessageKind.discussion
    content: str
    reply_to: Optional[str] = None
    metadata: dict = {}


class WSAck(BaseModel):
    type: str = "ack"
    message_id: str
