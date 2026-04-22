"""
Tests for match event fixtures.

These tests demonstrate WHY realistic mock data matters:
- Minimal placeholder data (score: 1-0, one event) misses entire categories of bugs
- Realistic data exercises the actual logic your production code will face
"""

import json
import pytest
from pathlib import Path

FIXTURES = Path(__file__).parent.parent / "fixtures" / "match_events"


def load(filename: str) -> dict:
    return json.loads((FIXTURES / filename).read_text())


# ── Typical match ─────────────────────────────────────────────────────────────

class TestTypicalMatch:
    def setup_method(self):
        self.match = load("typical_match.json")["match"]

    def test_match_has_correct_final_score(self):
        assert self.match["score"]["home"] == 3
        assert self.match["score"]["away"] == 2

    def test_half_time_score_is_subset_of_final_score(self):
        ht = self.match["score"]["half_time"]
        final = self.match["score"]
        # Half-time score can't exceed final score
        assert ht["home"] <= final["home"]
        assert ht["away"] <= final["away"]

    def test_goal_count_matches_score(self):
        goals_home = sum(
            1 for e in self.match["events"]
            if e["type"] == "GOAL" and e["team_id"] == "team_mci"
        )
        goals_away = sum(
            1 for e in self.match["events"]
            if e["type"] == "GOAL" and e["team_id"] == "team_liv"
        )
        assert goals_home == self.match["score"]["home"]
        assert goals_away == self.match["score"]["away"]

    def test_events_are_in_chronological_order(self):
        minutes = [e["minute"] for e in self.match["events"]]
        assert minutes == sorted(minutes)

    def test_penalty_goal_has_no_assist(self):
        """Penalty goals should never have an assist — a realistic data rule."""
        penalty_goals = [
            e for e in self.match["events"]
            if e["type"] == "GOAL" and e.get("goal_type") == "PENALTY"
        ]
        assert len(penalty_goals) > 0, "Fixture should contain a penalty goal"
        for goal in penalty_goals:
            assert goal["assist"] is None, "Penalty goals must not have an assist"

    def test_substitution_has_player_on_and_off(self):
        subs = [e for e in self.match["events"] if e["type"] == "SUBSTITUTION"]
        assert len(subs) > 0
        for sub in subs:
            assert "player_off" in sub
            assert "player_on" in sub
            assert sub["player_off"]["id"] != sub["player_on"]["id"]

    def test_attendance_does_not_exceed_venue_capacity(self):
        assert self.match["attendance"] <= self.match["venue"]["capacity"]

    def test_completed_match_has_actual_kickoff_and_final_whistle(self):
        assert self.match["status"] == "COMPLETED"
        assert self.match["actual_kickoff"] is not None
        assert self.match["final_whistle"] is not None


# ── Edge cases ────────────────────────────────────────────────────────────────

class TestMatchEdgeCases:
    def setup_method(self):
        self.cases = load("edge_cases.json")["edge_cases"]
        self.by_id = {c["match"]["id"]: c["match"] for c in self.cases}

    def test_goalless_draw_has_empty_events_list(self):
        """
        WHY THIS MATTERS: Code that does events[0] or assumes at least one event
        will crash on a 0-0 match. Minimal fixtures never catch this.
        """
        match = self.by_id["match_edge_001"]
        assert match["score"]["home"] == 0
        assert match["score"]["away"] == 0
        assert match["events"] == []

    def test_abandoned_match_has_null_final_whistle(self):
        """
        WHY THIS MATTERS: Duration calculations using final_whistle - actual_kickoff
        must handle None. A minimal fixture always has both fields populated.
        """
        match = self.by_id["match_edge_002"]
        assert match["status"] == "ABANDONED"
        assert match["final_whistle"] is None
        assert match["abandon_minute"] == 67

    def test_abandoned_match_has_partial_events(self):
        match = self.by_id["match_edge_002"]
        # Events exist but match didn't finish — partial data is valid
        assert len(match["events"]) > 0
        for event in match["events"]:
            assert event["minute"] < match["abandon_minute"]

    def test_extra_time_goal_has_extra_time_minute(self):
        """
        WHY THIS MATTERS: Minute 90+4 is different from minute 94.
        Display logic that ignores extra_time_minute will show wrong timestamps.
        """
        match = self.by_id["match_edge_003"]
        et_goals = [
            e for e in match["events"]
            if e["type"] == "GOAL" and e.get("extra_time_minute") is not None
        ]
        assert len(et_goals) > 0
        for goal in et_goals:
            assert goal["minute"] == 90
            assert goal["extra_time_minute"] > 0

    def test_penalty_shootout_has_winner(self):
        match = self.by_id["match_edge_003"]
        assert match.get("winner") is not None
        assert match.get("winner_method") == "PENALTY_SHOOTOUT"

    def test_scheduled_match_has_null_score_and_no_events(self):
        """
        WHY THIS MATTERS: Pre-match screens must handle null score gracefully.
        Minimal fixtures always have a score, so this bug hides until production.
        """
        match = self.by_id["match_edge_004"]
        assert match["status"] == "SCHEDULED"
        assert match["score"] is None
        assert match["actual_kickoff"] is None
        assert match["referee"] is None
        assert match["events"] == []
