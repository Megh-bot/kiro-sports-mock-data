"""
Pydantic models for match events and fan engagement.
These models validate the fixture files and serve as the schema contract.
"""

from __future__ import annotations
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


# ── Shared ────────────────────────────────────────────────────────────────────

class MatchStatus(str, Enum):
    SCHEDULED = "SCHEDULED"
    LIVE = "LIVE"
    COMPLETED = "COMPLETED"
    ABANDONED = "ABANDONED"
    POSTPONED = "POSTPONED"


class EventType(str, Enum):
    GOAL = "GOAL"
    YELLOW_CARD = "YELLOW_CARD"
    RED_CARD = "RED_CARD"
    SUBSTITUTION = "SUBSTITUTION"
    ADDED_TIME = "ADDED_TIME"
    PENALTY_SHOOTOUT_RESULT = "PENALTY_SHOOTOUT_RESULT"


class GoalType(str, Enum):
    OPEN_PLAY = "OPEN_PLAY"
    PENALTY = "PENALTY"
    FREE_KICK = "FREE_KICK"
    HEADER = "HEADER"
    OWN_GOAL = "OWN_GOAL"


# ── Match Events ──────────────────────────────────────────────────────────────

class PlayerRef(BaseModel):
    id: str
    name: str
    shirt_number: Optional[int] = None


class Venue(BaseModel):
    id: str
    name: str
    city: str
    capacity: int
    surface: str


class TeamRef(BaseModel):
    id: str
    name: str
    short_name: str
    crest_url: str


class Score(BaseModel):
    home: int = Field(ge=0)
    away: int = Field(ge=0)
    half_time: Optional[dict] = None
    extra_time: Optional[dict] = None
    penalty_shootout: Optional[dict] = None


class MatchEvent(BaseModel):
    id: str
    type: EventType
    minute: int = Field(ge=0, le=120)
    extra_time_minute: Optional[int] = Field(None, ge=0, le=30)
    team_id: Optional[str] = None


class Match(BaseModel):
    id: str
    competition: str
    season: str
    status: MatchStatus
    venue: Venue
    scheduled_kickoff: str
    actual_kickoff: Optional[str] = None
    final_whistle: Optional[str] = None
    home_team: TeamRef
    away_team: TeamRef
    score: Optional[Score] = None
    attendance: Optional[int] = Field(None, ge=0)
    events: list[MatchEvent] = []


# ── Fan Engagement ────────────────────────────────────────────────────────────

class ReactionType(str, Enum):
    GOAL_CELEBRATION = "GOAL_CELEBRATION"
    DISBELIEF = "DISBELIEF"
    ANGER = "ANGER"
    JOY = "JOY"
    SADNESS = "SADNESS"


class FanReaction(BaseModel):
    id: str
    fan_id: str
    type: ReactionType
    emoji: str
    match_minute: int = Field(ge=0, le=120)
    team_id: Optional[str] = None
    event_id: Optional[str] = None
    timestamp: str


class PollOption(BaseModel):
    id: str
    label: str
    votes: int = Field(ge=0)
    percentage: float = Field(ge=0.0, le=100.0)


class Poll(BaseModel):
    id: str
    match_id: str
    question: str
    triggered_at_minute: int = Field(ge=0, le=120)
    closed_at_minute: int = Field(ge=0, le=120)
    status: str
    options: list[PollOption]
    total_votes: int = Field(ge=0)
    winning_option_id: Optional[str] = None


class SentimentPoint(BaseModel):
    minute: int = Field(ge=0, le=120)
    home_sentiment: float = Field(ge=0.0, le=1.0)
    away_sentiment: float = Field(ge=0.0, le=1.0)


class FanEngagementSession(BaseModel):
    match_id: str
    session_id: str
    platform: str
    total_active_fans: int = Field(ge=0)
    peak_concurrent_fans: int = Field(ge=0)
    peak_minute: int = Field(ge=0, le=120)
    reactions: list[FanReaction] = []
    polls: list[Poll] = []
    fan_of_the_match: Optional[dict] = None
    sentiment_timeline: list[SentimentPoint] = []
