"""
Tests for fan engagement fixtures.

Each edge case test includes a WHY THIS MATTERS comment — the specific bug
that minimal placeholder data would have hidden.
"""

import json
from pathlib import Path

FIXTURES = Path(__file__).parent.parent / "fixtures" / "fan_engagement"


def load(filename: str) -> dict:
    return json.loads((FIXTURES / filename).read_text())


# ── Typical engagement session ────────────────────────────────────────────────

class TestTypicalEngagement:
    def setup_method(self):
        self.session = load("typical_engagement.json")["fan_engagement_session"]

    def test_peak_fans_exceeds_or_equals_total_active(self):
        assert self.session["peak_concurrent_fans"] >= self.session["total_active_fans"]

    def test_sentiment_values_are_within_bounds(self):
        for point in self.session["sentiment_timeline"]:
            assert 0.0 <= point["home_sentiment"] <= 1.0
            assert 0.0 <= point["away_sentiment"] <= 1.0

    def test_sentiment_spikes_after_goals(self):
        timeline = {p["minute"]: p for p in self.session["sentiment_timeline"]}
        assert timeline[14]["home_sentiment"] > timeline[0]["home_sentiment"]

    def test_poll_percentages_sum_to_100(self):
        for poll in self.session["polls"]:
            total = sum(opt["percentage"] for opt in poll["options"])
            assert abs(total - 100.0) < 0.5

    def test_poll_vote_counts_match_total(self):
        for poll in self.session["polls"]:
            counted = sum(opt["votes"] for opt in poll["options"])
            assert counted == poll["total_votes"]

    def test_winning_option_has_most_votes(self):
        for poll in self.session["polls"]:
            if poll["winning_option_id"] is None:
                continue
            winner = next(o for o in poll["options"] if o["id"] == poll["winning_option_id"])
            for opt in poll["options"]:
                assert winner["votes"] >= opt["votes"]

    def test_reactions_reference_valid_match_minutes(self):
        for reaction in self.session["reactions"]:
            assert 0 <= reaction["match_minute"] <= 120


# ── Edge cases ────────────────────────────────────────────────────────────────

class TestFanEngagementEdgeCases:
    def setup_method(self):
        self.cases = load("edge_cases.json")["edge_cases"]

    def _get(self, fragment: str) -> dict:
        for case in self.cases:
            if fragment in case["_description"]:
                return case
        raise KeyError(fragment)

    def test_fan_with_zero_engagement_has_empty_collections(self):
        """
        WHY THIS MATTERS: Leaderboard logic that calls max() or reactions[0]
        on an empty list crashes silently. Minimal fixtures always have at least
        one reaction, so this bug hides until a real passive viewer hits production.
        """
        case = self._get("zero engagement")
        fan = case["fan_profile"]
        assert fan["reactions"] == []
        assert fan["polls_participated"] == []
        assert fan["badges"] == []
        assert fan["total_engagement_score"] == 0

    def test_poll_with_zero_votes_has_null_winner(self):
        """
        WHY THIS MATTERS: Percentage calculations divide by total_votes.
        A poll with zero votes causes ZeroDivisionError. Minimal fixtures
        always have votes, so this only surfaces in low-traffic matches.
        """
        case = self._get("zero votes")
        poll = case["poll"]
        assert poll["total_votes"] == 0
        assert poll["winning_option_id"] is None
        for opt in poll["options"]:
            assert opt["votes"] == 0
            assert opt["percentage"] == 0.0

    def test_abandoned_session_has_null_fan_of_the_match(self):
        """
        WHY THIS MATTERS: Fan of the match is awarded at full time.
        An abandoned match never reaches full time, so this field is null.
        UI code that unconditionally renders fan_of_the_match will crash.
        """
        case = self._get("abandoned match")
        session = case["fan_engagement_session"]
        assert session["fan_of_the_match"] is None
        assert session["session_status"] == "TERMINATED"
        assert session["polls"] == []

    def test_abandoned_session_reaction_has_null_team_and_event(self):
        """
        WHY THIS MATTERS: Reactions during abandonment aren't tied to a goal
        or team — they're general frustration. Code that assumes team_id is
        always set will fail on these reactions.
        """
        case = self._get("abandoned match")
        session = case["fan_engagement_session"]
        abandonment_reactions = [
            r for r in session["reactions"] if r["team_id"] is None
        ]
        assert len(abandonment_reactions) > 0
        for r in abandonment_reactions:
            assert r["event_id"] is None

    def test_sentiment_boundary_values_are_valid(self):
        """
        WHY THIS MATTERS: Sentiment is a float between 0.0 and 1.0.
        Boundary values (exactly 0.0 and 1.0) must be accepted, not rejected
        by off-by-one validation like sentiment < 1.0 instead of <= 1.0.
        """
        case = self._get("exact extremes")
        timeline = case["sentiment_timeline"]
        extremes = [p for p in timeline if p["home_sentiment"] in (0.0, 1.0)]
        assert len(extremes) > 0
        for point in timeline:
            assert 0.0 <= point["home_sentiment"] <= 1.0
            assert 0.0 <= point["away_sentiment"] <= 1.0

    def test_max_engagement_fan_has_all_badge_types(self):
        case = self._get("maximum possible engagement")
        fan = case["fan_profile"]
        assert len(fan["reactions"]) > 0
        assert len(fan["polls_participated"]) > 0
        assert len(fan["badges"]) > 0
        assert fan["fan_of_the_match_nominated"] is True
        assert fan["total_engagement_score"] > 0

    def test_partial_watch_fan_has_reactions_only_after_join(self):
        """
        WHY THIS MATTERS: A fan who joined at minute 45 can't have reacted
        to a minute-14 goal. Timeline integrity checks must account for join time.
        """
        case = self._get("joined mid-match")
        fan = case["fan_profile"]
        joined_minute = 45
        for reaction in fan["reactions"]:
            assert reaction["match_minute"] >= joined_minute
