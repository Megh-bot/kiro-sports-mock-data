# Generating realistic test fixtures with Kiro

Every developer has been here: you need to test a feature, so you spend 45 minutes crafting a JSON fixture. You make up a score, invent a player name, stub out a few fields. The test passes. You ship.

Then production gets a 0-0 draw. Or an abandoned match. Or a fan who joined mid-game and never interacted. And your code crashes on data it never saw in testing.

The problem isn't the test — it's the fixture. Minimal placeholder data only tests the happy path. Realistic mock data tests the real world.

I described two data models to Kiro — live match events and fan engagement for a sports platform — and asked it to generate realistic fixtures, edge cases, and the tests to validate them. Here's what came out and why it matters.

---

## Data models

**Match events** capture everything that happens in a football match: goals, cards, substitutions, added time, penalty shootouts. The tricky part is that a match can be in many states — scheduled, live, completed, or abandoned — and each state has different nullable fields.

**Fan engagement** captures how fans interact during a live match: emoji reactions, live polls, sentiment scores, badges. The tricky part is that fans behave unpredictably — some never interact, some join mid-match, some watch until the final whistle.

Both models have one thing in common: minimal placeholder data hides entire categories of bugs.

---

## Realistic fixtures

The following fixture shows a completed match with accurate event sequencing, realistic player references, and domain rules applied throughout:

```json
{
  "match": {
    "id": "match_epl_2026_mci_liv_001",
    "status": "COMPLETED",
    "score": {
      "home": 3,
      "away": 2,
      "half_time": { "home": 2, "away": 1 }
    },
    "events": [
      {
        "id": "evt_001",
        "type": "GOAL",
        "minute": 14,
        "team_id": "team_mci",
        "player": { "id": "player_haaland", "name": "Erling Haaland", "shirt_number": 9 },
        "assist": { "id": "player_silva", "name": "Bernardo Silva", "shirt_number": 20 },
        "goal_type": "OPEN_PLAY"
      },
      {
        "id": "evt_003",
        "type": "GOAL",
        "minute": 38,
        "team_id": "team_liv",
        "player": { "id": "player_salah", "name": "Mohamed Salah", "shirt_number": 11 },
        "assist": null,
        "goal_type": "PENALTY"
      }
    ]
  }
}
```

Notice `"assist": null` on the penalty goal. That's a domain rule — penalties don't have assists. A hand-crafted fixture would likely set `"assist": "some_player"` without thinking about it, and your assist-counting logic would silently produce wrong numbers.

The fan engagement fixture is equally detailed. The following sentiment timeline shows values that spike after each goal, reflecting the relationship between match events and fan emotion:

```json
{
  "sentiment_timeline": [
    { "minute": 0,  "home_sentiment": 0.72, "away_sentiment": 0.71 },
    { "minute": 14, "home_sentiment": 0.94, "away_sentiment": 0.41 },
    { "minute": 89, "home_sentiment": 0.99, "away_sentiment": 0.18 }
  ]
}
```

Sentiment jumps to 0.94 at minute 14 — right after the first home goal. That's the kind of internal consistency that makes fixtures useful for testing real behaviour, not just schema compliance.

---

## Where it gets interesting: edge cases

Realistic typical data is useful. Edge cases are where bugs live.

I asked Kiro to generate edge cases for both data types — empty arrays, null values, boundary conditions, and states that only occur in specific scenarios. Here's what it produced and why each one matters.

### Match event edge cases

**Goalless draw — empty events array:**

```json
{
  "status": "COMPLETED",
  "score": { "home": 0, "away": 0 },
  "events": []
}
```

Any code that does `events[0]` or `events[-1]` to find the last goal crashes here. Minimal fixtures always have at least one event. This one doesn't.

**Abandoned match — null final whistle:**

```json
{
  "status": "ABANDONED",
  "abandon_reason": "Severe weather — waterlogged pitch",
  "abandon_minute": 67,
  "actual_kickoff": "2026-02-08T14:03:00Z",
  "final_whistle": null
}
```

Match duration calculations using `final_whistle - actual_kickoff` will throw a `TypeError` on `None`. This fixture makes that test explicit before it hits production.

**Scheduled future match — null score, null referee, no events:**

```json
{
  "status": "SCHEDULED",
  "score": null,
  "actual_kickoff": null,
  "referee": null,
  "events": []
}
```

Pre-match screens that unconditionally render `score.home` will crash. A minimal fixture always has a score because you filled it in. This one doesn't, because a scheduled match hasn't been played yet.

**Extra time goal — minute 90+4:**

```json
{
  "type": "GOAL",
  "minute": 90,
  "extra_time_minute": 4,
  "period": "SECOND_HALF_ADDED_TIME"
}
```

Minute 90+4 is not the same as minute 94. Display logic that ignores `extra_time_minute` will show the wrong timestamp on a last-minute winner. This is the kind of edge case that only surfaces in high-stakes matches — exactly when you can't afford a bug.

### Fan engagement edge cases

**Fan with zero engagement:**

```json
{
  "reactions": [],
  "polls_participated": [],
  "badges": [],
  "total_engagement_score": 0
}
```

Leaderboard logic that calls `max(reactions)` or `reactions[0]` crashes on a fan who watched the whole match but never tapped a button. These fans exist — they're just quiet.

**Poll with zero votes:**

```json
{
  "total_votes": 0,
  "winning_option_id": null,
  "options": [
    { "label": "Nothing stood out", "votes": 0, "percentage": 0.0 }
  ]
}
```

Percentage calculations divide by `total_votes`. Zero votes means `ZeroDivisionError`. This only happens in low-traffic matches or when a poll closes too fast — exactly the scenario your test suite never covers with a fixture that always has votes.

**Abandoned session — null fan of the match, empty polls:**

```json
{
  "session_status": "TERMINATED",
  "termination_reason": "MATCH_ABANDONED",
  "fan_of_the_match": null,
  "polls": []
}
```

Fan of the match is awarded at full time. An abandoned match never reaches full time. UI code that unconditionally renders this field will crash. The fixture makes the contract explicit.

**Sentiment at exact boundary values:**

```json
{ "minute": 89, "home_sentiment": 1.0, "away_sentiment": 0.0 }
```

Validation logic written as `sentiment < 1.0` instead of `sentiment <= 1.0` rejects a perfectly valid value. Boundary testing only works if your fixture actually hits the boundary.

---

## Tests that prove it

Each edge case has a test with a comment explaining the exact bug it prevents:

```python
def test_poll_with_zero_votes_has_null_winner(self):
    """
    WHY THIS MATTERS: Percentage calculations divide by total_votes.
    A poll with zero votes causes ZeroDivisionError. Minimal fixtures
    always have votes, so this only surfaces in low-traffic matches.
    """
    poll = self._get("zero votes")["poll"]
    assert poll["total_votes"] == 0
    assert poll["winning_option_id"] is None


def test_scheduled_match_has_null_score_and_no_events(self):
    """
    WHY THIS MATTERS: Pre-match screens must handle null score gracefully.
    Minimal fixtures always have a score, so this bug hides until production.
    """
    match = self._get("match_edge_004")
    assert match["score"] is None
    assert match["actual_kickoff"] is None
    assert match["events"] == []
```

28 tests. All passing. Each one covering a scenario that a hand-crafted fixture would have missed.

---

## How to ask for edge cases

The prompt that produced the match event edge cases:

> Generate edge case fixtures for a live match event model. Include: a goalless draw with an empty events array, an abandoned match with a null final whistle and partial events, a match with extra time and a penalty shootout, and a scheduled future match with null score and no referee. For each case, add a `_description` field explaining what makes it an edge case.

The prompt that produced the fan engagement edge cases:

> Generate edge case fixtures for a fan engagement session. Include: a fan with zero interactions, a poll that closed with zero votes, a session terminated due to match abandonment with null fan-of-the-match, sentiment values at exact boundary conditions (0.0 and 1.0), and a fan who joined mid-match. Explain why each case matters for production code.

The `_description` field is worth asking for explicitly — it makes the fixtures self-documenting and gives you the comment text for your tests.

---

## Conclusion

Kiro's fixture generation works because it reasons about your data model holistically — covering the null values, empty arrays, and boundary conditions that hand-crafted fixtures miss. When you describe a match that can be abandoned, Kiro generates a fixture where `final_whistle` is null and `score` is partial. When you describe a fan engagement session, it generates the fan who never interacted, not just the one who did everything.

The result is a test suite that catches real bugs before they reach production — not because you thought of every edge case, but because you didn't have to.

Fixtures, models, and all 28 tests are on [GitHub](https://github.com/Megh-bot/kiro-sports-mock-data).
