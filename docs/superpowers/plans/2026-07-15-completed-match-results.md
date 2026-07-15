# V3 Completed Match Results Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Display verified completed-match results on match cards and knockout bracket nodes while retaining clearly labeled pre-match predictions.

**Architecture:** Normalize FIFA and ESPN match state into one deterministic `result` object before model analysis. Preserve that object through source verification, analysis merge, tournament structure construction, validation, and deterministic HTML rendering; the DeepSeek models never decide whether a match is complete or supply the final score.

**Tech Stack:** Python 3 standard library, `unittest`, static HTML/CSS, GitHub Actions, GitHub Pages.

## Global Constraints

- Keep the V3 Agent main version unchanged.
- FIFA official schedule is the primary result source; ESPN is secondary verification and may not override a valid FIFA result.
- Analysis model remains exactly `deepseek-v4-pro`; render model remains exactly `deepseek-v4-flash`.
- Do not use production mock data or fabricate results, injuries, odds, weather, rankings, or fixtures.
- Do not skip either DeepSeek API stage in the production workflow.
- A pre-match `0-0` from a provider must never be displayed as a completed result.

---

### Task 1: Normalize Official Match Results

**Files:**
- Create: `tests/test_match_results.py`
- Modify: `app/pipeline.py:465-549`
- Modify: `app/pipeline.py:657-694`

**Interfaces:**
- Produces: `normalize_match_result(status: Any, home_score: Any, away_score: Any, source: str) -> dict[str, Any]`.
- Produces: `matches[*].result` with `status`, `completed`, `home_score`, `away_score`, `display`, and `source`.

- [ ] **Step 1: Write failing source-normalization tests**

```python
def test_fifa_completed_match_carries_real_result(self):
    match = transform_fifa_match(self.fifa_item("Finished", 2, 1))
    self.assertTrue(match["result"]["completed"])
    self.assertEqual((match["result"]["home_score"], match["result"]["away_score"]), (2, 1))

def test_scheduled_zero_zero_is_not_a_real_result(self):
    match = transform_fifa_match(self.fifa_item("Scheduled", 0, 0))
    self.assertFalse(match["result"]["completed"])
    self.assertIsNone(match["result"]["home_score"])
```

- [ ] **Step 2: Run tests and verify RED**

Run: `python -m unittest tests.test_match_results.MatchResultSourceTests -v`

Expected: FAIL because `result` is absent.

- [ ] **Step 3: Implement strict status and score normalization**

```python
def normalize_match_result(status, home_score, away_score, source):
    completed = match_status_completed(status)
    home = non_negative_score(home_score) if completed else None
    away = non_negative_score(away_score) if completed else None
    valid = completed and home is not None and away is not None
    return {
        "status": "completed" if valid else "scheduled",
        "completed": valid,
        "home_score": home if valid else None,
        "away_score": away if valid else None,
        "display": f"{home}-{away}" if valid else None,
        "source": source,
    }
```

Call it from FIFA using `MatchStatus` plus `Home.Score`/`Away.Score`, and from ESPN using `competition.status.type` plus competitor scores.

- [ ] **Step 4: Run source tests and verify GREEN**

Run: `python -m unittest tests.test_match_results.MatchResultSourceTests -v`

Expected: all source tests PASS.

### Task 2: Preserve and Verify Results Through V3 Data Flow

**Files:**
- Modify: `tests/test_match_results.py`
- Modify: `app/pipeline.py:705-780`
- Modify: `app/pipeline.py:1182-1225`
- Modify: `app/pipeline.py:1814-1850`

**Interfaces:**
- Consumes: normalized `result` objects from Task 1.
- Produces: `merge_match_result(primary, secondary) -> dict[str, Any]` and result-bearing analysis/structure nodes.

- [ ] **Step 1: Write failing merge and structure tests**

```python
def test_fifa_result_wins_and_espn_confirms(self):
    result = merge_match_result(self.completed(2, 1, "FIFA"), self.completed(2, 1, "ESPN"))
    self.assertEqual(result["source"], "FIFA official calendar API")
    self.assertEqual(result["verification"], "confirmed")

def test_structure_node_preserves_completed_result(self):
    node = structure_match_node(self.completed_match(), {}, set())
    self.assertTrue(node["result"]["completed"])
```

- [ ] **Step 2: Run merge tests and verify RED**

Run: `python -m unittest tests.test_match_results.MatchResultMergeTests -v`

Expected: FAIL because merge/propagation is absent.

- [ ] **Step 3: Implement deterministic primary-source merge**

Use FIFA completed result whenever valid. Add `verification=confirmed` when ESPN agrees, `verification=conflict` plus both source values when it disagrees, and `verification=unavailable` when ESPN lacks a result. Never replace a valid FIFA score. Preserve `result` in `merge_analysis_matches` and `structure_match_node`; placeholders receive no completed result.

- [ ] **Step 4: Run merge tests and verify GREEN**

Run: `python -m unittest tests.test_match_results.MatchResultMergeTests -v`

Expected: all merge tests PASS.

### Task 3: Render Actual Results and Validate the Contract

**Files:**
- Modify: `tests/test_match_results.py`
- Modify: `app/pipeline.py:2020-2115`
- Modify: `app/pipeline.py:2356-2415`
- Modify: `app/pipeline.py:2640-2825`
- Modify: `app/validate.py:240-410`
- Modify: `app/validate.py:380-505`

**Interfaces:**
- Consumes: `matches[*].result` and `tournament_structure` node results.
- Produces: completed-card HTML, scheduled-card HTML, bracket real-result HTML, and result contract errors.

- [ ] **Step 1: Write failing render and validator tests**

```python
def test_completed_card_displays_actual_and_labels_prediction(self):
    page = match_card(self.analysis_match(completed=True))
    self.assertIn("完赛 · 真实比分", page)
    self.assertIn("赛前预测", page)
    self.assertIn(">2<", page)

def test_scheduled_card_uses_predicted_score(self):
    page = match_card(self.analysis_match(completed=False))
    self.assertIn("未开赛 · 预测比分", page)

def test_completed_result_requires_valid_scores(self):
    errors = []
    validate_result({"completed": True, "home_score": None, "away_score": 1}, "match.result", errors)
    self.assertTrue(errors)
```

- [ ] **Step 2: Run render/validation tests and verify RED**

Run: `python -m unittest tests.test_match_results.MatchResultRenderTests tests.test_match_results.MatchResultValidationTests -v`

Expected: FAIL because status-specific UI and result validation are absent.

- [ ] **Step 3: Implement status-specific HTML and validation**

Add `scoreboard_view(match)` to select official result only when `completed=true` and scores are valid. Add visible `完赛 · 真实比分`, `未开赛 · 预测比分`, and `赛前预测` labels. In bracket nodes, show `完赛 <home>-<away>` for completed real nodes, `未开赛` for known scheduled nodes, and `待定` only for placeholders. Add dedicated green/blue result label styles. Validate result shape and reject completed results on placeholders.

- [ ] **Step 4: Run render/validation tests and full local suite**

Run: `python -m unittest discover -s tests -v`

Expected: all tests PASS.

Run: `python -m py_compile app/pipeline.py app/validate.py`

Expected: exit code 0.

### Task 4: Project Record, Production Pipeline, and Online Verification

**Files:**
- Modify: `项目基本要求.md`
- Generated by workflows: `data/latest.json`, `docs/index.html`

**Interfaces:**
- Consumes: production FIFA, ESPN, and DeepSeek APIs.
- Produces: deployed GitHub Pages and validated V3 JSON.

- [ ] **Step 1: Append the V3 small-version record**

Record date `2026-07-15`, reason, FIFA-primary result policy, ESPN verification, match-card/bracket behavior, and unchanged V3 dual-model architecture.

- [ ] **Step 2: Run fresh local verification**

Run: `python -m unittest discover -s tests -v`

Run: `python -m py_compile app/pipeline.py app/validate.py`

Run: `git diff --check`

Expected: tests PASS and both commands exit 0.

- [ ] **Step 3: Commit and publish the authorized change**

Commit the implementation intentionally, push `main`, then run/monitor `research`, `analysis`, `render`, `finalize`, and `publish` GitHub Actions in order.

- [ ] **Step 4: Verify production artifacts**

Download `https://lidboy.github.io/worldcup_codex/data/latest.json` and the Pages HTML. Run `python app/validate.py <downloaded-latest.json>`. Confirm every completed match has valid official scores, every scheduled card is labeled as prediction, only placeholder nodes display `待定`, China match-day grouping is intact, bracket counts remain 16/8/4/2/1, and Token/Cost remain visible.
