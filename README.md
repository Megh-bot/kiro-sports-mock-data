# kiro-sports-mock-data

Realistic JSON fixtures for testing sports platform features — live match events and fan engagement data — generated with [Kiro](https://kiro.dev).

Covers two data types with both typical and edge case scenarios. Each edge case is documented with the specific production bug it prevents.

Read the full write-up on [Medium](#).

---

## Project structure

```
fixtures/
├── match_events/
│   ├── typical_match.json      # Completed match with goals, cards, substitutions
│   └── edge_cases.json         # Goalless draw, abandoned match, extra time + shootout, scheduled
└── fan_engagement/
    ├── typical_engagement.json # Full session: reactions, polls, sentiment timeline
    └── edge_cases.json         # Zero engagement, empty poll, abandoned session, boundary values
app/
└── models.py                   # Pydantic schema for both data types
tests/
├── test_match_events.py        # 14 tests
└── test_fan_engagement.py      # 14 tests
```

---

## Setup

Requires Python 3.10–3.12.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

---

## Run the tests

```bash
pytest tests/ -v
```

Expected output:

```
PASSED  TestTypicalEngagement::test_peak_fans_exceeds_or_equals_total_active
PASSED  TestTypicalEngagement::test_sentiment_values_are_within_bounds
PASSED  TestTypicalEngagement::test_sentiment_spikes_after_goals
PASSED  TestTypicalEngagement::test_poll_percentages_sum_to_100
PASSED  TestTypicalEngagement::test_poll_vote_counts_match_total
PASSED  TestTypicalEngagement::test_winning_option_has_most_votes
PASSED  TestTypicalEngagement::test_reactions_reference_valid_match_minutes
PASSED  TestFanEngagementEdgeCases::test_fan_with_zero_engagement_has_empty_collections
PASSED  TestFanEngagementEdgeCases::test_poll_with_zero_votes_has_null_winner
PASSED  TestFanEngagementEdgeCases::test_abandoned_session_has_null_fan_of_the_match
PASSED  TestFanEngagementEdgeCases::test_abandoned_session_reaction_has_null_team_and_event
PASSED  TestFanEngagementEdgeCases::test_sentiment_boundary_values_are_valid
PASSED  TestFanEngagementEdgeCases::test_max_engagement_fan_has_all_badge_types
PASSED  TestFanEngagementEdgeCases::test_partial_watch_fan_has_reactions_only_after_join
PASSED  TestTypicalMatch::test_match_has_correct_final_score
PASSED  TestTypicalMatch::test_half_time_score_is_subset_of_final_score
PASSED  TestTypicalMatch::test_goal_count_matches_score
PASSED  TestTypicalMatch::test_events_are_in_chronological_order
PASSED  TestTypicalMatch::test_penalty_goal_has_no_assist
PASSED  TestTypicalMatch::test_substitution_has_player_on_and_off
PASSED  TestTypicalMatch::test_attendance_does_not_exceed_venue_capacity
PASSED  TestTypicalMatch::test_completed_match_has_actual_kickoff_and_final_whistle
PASSED  TestMatchEdgeCases::test_goalless_draw_has_empty_events_list
PASSED  TestMatchEdgeCases::test_abandoned_match_has_null_final_whistle
PASSED  TestMatchEdgeCases::test_abandoned_match_has_partial_events
PASSED  TestMatchEdgeCases::test_extra_time_goal_has_extra_time_minute
PASSED  TestMatchEdgeCases::test_penalty_shootout_has_winner
PASSED  TestMatchEdgeCases::test_scheduled_match_has_null_score_and_no_events

28 passed in 0.05s
```

---

## Edge cases covered

### Match events

| Fixture | Edge case | Bug it prevents |
|---|---|---|
| Goalless draw | `events: []` | `IndexError` on `events[0]` |
| Abandoned match | `final_whistle: null` | `TypeError` in duration calculations |
| Scheduled match | `score: null`, `referee: null` | `NullPointerError` in pre-match UI |
| Extra time goal | `minute: 90, extra_time_minute: 4` | Wrong timestamp display on late goals |
| Penalty shootout | `winner_method: PENALTY_SHOOTOUT` | Missing winner logic for drawn matches |

### Fan engagement

| Fixture | Edge case | Bug it prevents |
|---|---|---|
| Zero engagement fan | `reactions: []`, `badges: []` | `IndexError` in leaderboard logic |
| Empty poll | `total_votes: 0`, `winning_option_id: null` | `ZeroDivisionError` in percentage calc |
| Abandoned session | `fan_of_the_match: null`, `polls: []` | `NullPointerError` in post-match UI |
| Boundary sentiment | `home_sentiment: 1.0`, `away_sentiment: 0.0` | Off-by-one in validation (`< 1.0` vs `<= 1.0`) |
| Partial watcher | Reactions only after join minute | Timeline integrity violations |
