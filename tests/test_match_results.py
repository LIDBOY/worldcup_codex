import unittest
import datetime as dt
from unittest.mock import patch

from app import pipeline
from app import validate as validator


def fifa_item(status="Scheduled", home_score=0, away_score=0):
    return {
        "IdMatch": "M-test",
        "Date": "2026-07-15T12:00:00Z",
        "CompetitionName": "FIFA World Cup",
        "SeasonName": "FIFA World Cup 2026",
        "StageName": "Round of 32",
        "MatchNumber": 73,
        "MatchStatus": status,
        "OfficialityStatus": "Official",
        "Home": {
            "TeamName": "France",
            "Abbreviation": "FRA",
            "IdCountry": "FRA",
            "Score": home_score,
        },
        "Away": {
            "TeamName": "Germany",
            "Abbreviation": "GER",
            "IdCountry": "GER",
            "Score": away_score,
        },
    }


def espn_event(completed=True, home_score="2", away_score="1"):
    return {
        "id": "espn-test",
        "date": "2026-07-15T12:00:00Z",
        "competitions": [
            {
                "status": {
                    "type": {
                        "state": "post" if completed else "pre",
                        "completed": completed,
                        "name": "STATUS_FINAL" if completed else "STATUS_SCHEDULED",
                        "detail": "Final" if completed else "Scheduled",
                    }
                },
                "competitors": [
                    {
                        "homeAway": "home",
                        "score": home_score,
                        "team": {"displayName": "France", "abbreviation": "FRA"},
                    },
                    {
                        "homeAway": "away",
                        "score": away_score,
                        "team": {"displayName": "Germany", "abbreviation": "GER"},
                    },
                ],
            }
        ],
    }


def completed_result(home=2, away=1, source="FIFA official calendar API"):
    return {
        "status": "completed",
        "completed": True,
        "home_score": home,
        "away_score": away,
        "display": f"{home}-{away}",
        "source": source,
    }


def analysis_match(completed=False):
    result = (
        completed_result(2, 1)
        if completed
        else {
            "status": "scheduled",
            "completed": False,
            "home_score": None,
            "away_score": None,
            "display": None,
            "source": "FIFA official calendar API",
            "verification": "unavailable",
        }
    )
    return {
        "match_id": "M-test",
        "match_number": 73,
        "kickoff_utc": "2026-07-15T12:00:00Z",
        "kickoff_beijing": "2026-07-15T20:00:00+08:00",
        "kickoff_display": "北京时间 07-15 20:00",
        "teams": {
            "home": {"name": "法国", "name_en": "France", "country_code": "FRA", "flag_emoji": "🇫🇷"},
            "away": {"name": "德国", "name_en": "Germany", "country_code": "GER", "flag_emoji": "🇩🇪"},
        },
        "result": result,
        "predicted_score": {"home": 1, "away": 0},
        "score_options": [
            {"score": "1-0", "rank": 1, "reason": "主推荐理由"},
            {"score": "1-1", "rank": 2, "reason": "次选理由"},
            {"score": "2-1", "rank": 3, "reason": "第三选择理由"},
        ],
        "win_draw_loss": {"home_win": 48, "draw": 27, "away_win": 25},
        "xg_prediction": {"home": 1.4, "away": 0.9},
        "upset_probability": 22,
        "confidence": "medium",
        "tactical_matchup": "战术分析",
        "risk_analysis": "风险分析",
        "injury_adjustment": "unknown",
        "injuries": {},
        "odds": {"available": False},
        "method_factors": {},
        "matchup_graph": {},
    }


class MatchResultSourceTests(unittest.TestCase):
    def test_fifa_numeric_completed_status_carries_official_result(self):
        item = fifa_item(0, 2, 1)
        item["OfficialityStatus"] = 1
        item["ResultType"] = 1

        match = pipeline.transform_fifa_match(item)

        self.assertTrue(match["result"]["completed"])
        self.assertEqual(match["result"]["display"], "2-1")
        self.assertEqual(match["result"]["source"], "FIFA official calendar API")

    def test_fifa_completed_match_carries_real_result(self):
        match = pipeline.transform_fifa_match(fifa_item("Finished", 2, 1))

        self.assertTrue(match["result"]["completed"])
        self.assertEqual(match["result"]["status"], "completed")
        self.assertEqual(
            (match["result"]["home_score"], match["result"]["away_score"]),
            (2, 1),
        )
        self.assertEqual(match["result"]["source"], "FIFA official calendar API")

    def test_fifa_scheduled_zero_zero_is_not_a_real_result(self):
        match = pipeline.transform_fifa_match(fifa_item("Scheduled", 0, 0))

        self.assertFalse(match["result"]["completed"])
        self.assertIsNone(match["result"]["home_score"])
        self.assertIsNone(match["result"]["away_score"])

    def test_espn_completed_match_carries_secondary_result(self):
        match = pipeline.transform_espn_event(espn_event(True, "2", "1"))

        self.assertIsNotNone(match)
        self.assertTrue(match["result"]["completed"])
        self.assertEqual(match["result"]["display"], "2-1")
        self.assertEqual(match["result"]["source"], "ESPN public FIFA World Cup scoreboard")

    def test_espn_scheduled_zero_zero_is_not_a_real_result(self):
        match = pipeline.transform_espn_event(espn_event(False, "0", "0"))

        self.assertIsNotNone(match)
        self.assertFalse(match["result"]["completed"])
        self.assertIsNone(match["result"]["display"])


class MatchResultMergeTests(unittest.TestCase):
    def test_fifa_result_wins_and_espn_confirms(self):
        fifa = completed_result(2, 1)
        espn = completed_result(2, 1, "ESPN public FIFA World Cup scoreboard")

        result = pipeline.merge_match_result(fifa, espn)

        self.assertEqual(result["source"], "FIFA official calendar API")
        self.assertEqual(result["verification"], "confirmed")
        self.assertEqual(result["display"], "2-1")

    def test_fifa_result_wins_when_espn_conflicts(self):
        fifa = completed_result(2, 1)
        espn = completed_result(1, 2, "ESPN public FIFA World Cup scoreboard")

        result = pipeline.merge_match_result(fifa, espn)

        self.assertEqual(result["display"], "2-1")
        self.assertEqual(result["verification"], "conflict")
        self.assertEqual(result["secondary_display"], "1-2")

    def test_analysis_merge_preserves_research_result(self):
        research_match = pipeline.transform_fifa_match(fifa_item("Finished", 2, 1))
        analysis = {
            "matches": [
                {
                    "match_id": "M-test",
                    "teams": research_match["teams"],
                    "predicted_score": {"home": 1, "away": 0},
                }
            ]
        }

        merged = pipeline.merge_analysis_matches(analysis, {"matches": [research_match]})

        self.assertTrue(merged[0]["result"]["completed"])
        self.assertEqual(merged[0]["result"]["display"], "2-1")

    def test_structure_node_preserves_completed_result(self):
        match = pipeline.transform_fifa_match(fifa_item("Finished", 2, 1))

        node = pipeline.structure_match_node(match, {}, set())

        self.assertTrue(node["result"]["completed"])
        self.assertEqual(node["result"]["display"], "2-1")

    def test_placeholder_node_has_no_completed_result(self):
        node = pipeline.bracket_placeholder_node(89, "round_of_16")

        self.assertFalse(node["result"]["completed"])
        self.assertIsNone(node["result"]["display"])


class MatchResultRenderTests(unittest.TestCase):
    def test_completed_card_displays_actual_and_labels_prediction(self):
        page = pipeline.match_card(analysis_match(completed=True))

        self.assertIn("完赛 · 真实比分", page)
        self.assertIn("赛前预测", page)
        self.assertIn("prediction-review-label", page)
        self.assertIn("scoreboard actual-result", page)
        self.assertIn(">2<", page)
        self.assertIn(">1<", page)

    def test_scheduled_card_uses_predicted_score(self):
        page = pipeline.match_card(analysis_match(completed=False))

        self.assertIn("未开赛 · 预测比分", page)
        self.assertIn("scoreboard predicted-result", page)
        self.assertIn(">1<", page)
        self.assertIn(">0<", page)

    def test_completed_bracket_node_shows_result_not_pending(self):
        node = {
            **analysis_match(completed=True),
            "current_window": False,
            "placeholder": False,
            "score_options": [],
        }

        page = pipeline.bracket_structure_node_html(node, "round_of_32")

        self.assertIn("完赛", page)
        self.assertIn("2 : 1", page)
        self.assertNotIn("待定", page)

    def test_scheduled_real_bracket_node_is_not_pending(self):
        node = {
            **analysis_match(completed=False),
            "current_window": False,
            "placeholder": False,
            "score_options": [],
        }

        page = pipeline.bracket_structure_node_html(node, "round_of_32")

        self.assertIn("未开赛", page)
        self.assertNotIn("待定", page)

    def test_placeholder_bracket_node_remains_pending(self):
        node = pipeline.bracket_placeholder_node(89, "round_of_16")

        page = pipeline.bracket_structure_node_html(node, "round_of_16")

        self.assertIn("待定", page)
        self.assertNotIn("完赛 · 真实比分", page)


class MatchResultValidationTests(unittest.TestCase):
    def test_completed_result_requires_valid_scores(self):
        errors = []

        validator.validate_result(
            {"completed": True, "home_score": None, "away_score": 1},
            "match.result",
            errors,
        )

        self.assertTrue(errors)

    def test_scheduled_result_cannot_carry_real_scores(self):
        errors = []

        validator.validate_result(
            {"status": "scheduled", "completed": False, "home_score": 0, "away_score": 0},
            "match.result",
            errors,
        )

        self.assertTrue(errors)

    def test_valid_completed_result_passes(self):
        errors = []

        validator.validate_result(completed_result(2, 1), "match.result", errors)

        self.assertEqual(errors, [])


class MatchResultResearchWindowTests(unittest.TestCase):
    def test_structure_window_covers_completed_tournament_matches(self):
        display = pipeline.china_match_day_window(2, dt.date(2026, 7, 15))

        structure = pipeline.tournament_structure_window(display)

        self.assertEqual(structure["match_days"][0]["date"], "2026-06-11")
        self.assertGreaterEqual(
            dt.datetime.fromisoformat(structure["end_iso"]),
            dt.datetime.fromisoformat(display["end_iso"]),
        )
        self.assertGreaterEqual(len(structure["match_days"]), 40)

    @patch("app.pipeline.request_json")
    def test_espn_structure_fetch_uses_one_date_range_request(self, request_json):
        request_json.return_value = {"events": []}

        events, urls, warnings = pipeline.fetch_espn_events(dt.date(2026, 6, 10), 48)

        self.assertEqual(events, [])
        self.assertEqual(warnings, [])
        self.assertEqual(request_json.call_count, 1)
        self.assertEqual(request_json.call_args.kwargs["params"]["dates"], "20260610-20260727")
        self.assertEqual(len(urls), 1)


if __name__ == "__main__":
    unittest.main()
