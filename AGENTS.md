# RK Screener — Multi-Agent Orchestration

This file defines how the Developer, Reviewer, and Tester agents collaborate to implement the RK Stock Screener project.

## Reference Document

All implementation work follows: **`RK_Screener_Implementation_Plan_v2.md`**

## Agents

| Agent | Role | Can Write Code? |
|-------|------|-----------------|
| **Developer** (`.claude/agents/developer.md`) | Implements code from the plan, fixes reviewer/tester feedback | Yes |
| **Reviewer** (`.claude/agents/reviewer.md`) | Reviews code for correctness, security, plan compliance | No (read-only + run tests) |
| **Tester** (`.claude/agents/tester.md`) | Writes tests, runs pytest, validates behavior with real/mock data | Yes (test files only) |

## Workflow: Implement → Review → Fix → Test Loop

For each sprint/day in the implementation plan, follow this cycle:

```
┌──────────┐     ┌──────────┐     ┌──────────┐     ┌──────────┐
│ Developer│────>│ Reviewer │────>│ Developer│────>│  Tester  │
│  (build) │     │ (audit)  │     │  (fix)   │     │ (verify) │
└──────────┘     └──────────┘     └──────────┘     └──────────┘
                                       │                 │
                                       │    ┌────────────┘
                                       │    │ failures?
                                       │    v
                                       │  ┌──────────┐
                                       └──│ Developer│──> re-test
                                          │  (fix)   │
                                          └──────────┘
```

### Step 1: Implement
Ask the **Developer** agent to implement the current sprint/day:

```
Ask the Developer agent to implement Sprint 1, Day 1 from
RK_Screener_Implementation_Plan_v2.md (Config, Logger, Utils).
```

### Step 2: Review
Ask the **Reviewer** agent to audit what was just built:

```
Ask the Reviewer agent to review the Sprint 1, Day 1 implementation
(config.py, logger.py, cache.py) against the plan.
```

### Step 3: Fix
If the Reviewer found issues, send them back to the **Developer**:

```
Ask the Developer agent to fix the issues found by the Reviewer:
[paste or reference the reviewer's ISSUES list]
```

### Step 4: Test
Ask the **Tester** agent to write and run tests for what was built:

```
Ask the Tester agent to write and run tests for Sprint 1, Day 1
(config.py, logger.py, cache.py).
```

### Step 5: Fix Test Failures
If the Tester found failures, send them back to the **Developer**:

```
Ask the Developer agent to fix these test failures:
[paste the Tester's failure report]
```

Then re-run the Tester to confirm fixes.

### Step 6: Next Sprint
Once all tests pass and the Reviewer is satisfied, move to the next day/sprint.

## Implementation Order (from the plan)

### Phase 1 — Local Machine MVP

| Sprint | Days | What to Build |
|--------|------|---------------|
| Sprint 1 | Days 1-3 | Config, logger, cache, DB schema, database.py, main.py skeleton, ALL module stubs |
| Sprint 2 | Days 4-11 | Layer 1 (universe), Layer 2 (price filter), Layer 3 (fundamentals/XBRL) |
| Sprint 3 | Days 12-17 | Layer 4 (insider buying), Layer 5 (bonds), Layer 6 (Gemini LLM) |
| Sprint 4 | Days 18-21 | Scoring engine, results.json output, full pipeline run |
| Sprint 5 | Days 22-30 | Frontend pages 1-3, Page 4 stub |

### Phase 2 — GitHub Actions + Deferred Features
| Sprint | Days | What to Build |
|--------|------|---------------|
| Phase 2 | Days 31-38 | GitHub Actions, swing trader, Playwright bonds, charts |

### Phase 3 — Cloudflare Web App
| Sprint | Days | What to Build |
|--------|------|---------------|
| Phase 3 | Days 39-55 | Cloudflare Workers, D1 database, full web app |

## Example Full Session

```
# 1. Implement Sprint 1, Day 1
"Ask the Developer agent to implement Sprint 1 Day 1 from the plan:
config.py, logger.py, and cache.py"

# 2. Review it
"Ask the Reviewer agent to review Sprint 1 Day 1 implementation"

# 3. Fix review issues (if any)
"Ask the Developer agent to fix these reviewer issues: [issues]"

# 4. Write and run tests
"Ask the Tester agent to write and run tests for Sprint 1 Day 1"

# 5. Fix test failures (if any)
"Ask the Developer agent to fix these test failures: [failures]"

# 6. Re-run tests to confirm
"Ask the Tester agent to re-run the Sprint 1 Day 1 tests"

# 7. Move to Day 2
"Ask the Developer agent to implement Sprint 1 Day 2: database schema
and database.py"

# ... continue through all sprints
```

## Tips

- **One day/section at a time.** Don't ask the Developer to implement an entire sprint at once — break it into the day-sized chunks from the plan.
- **Always review before testing.** The Reviewer catches plan deviations and security issues that tests won't find.
- **Always test before moving on.** The Tester catches runtime bugs and edge cases that code review misses.
- **The plan is the source of truth.** If there's a conflict between what seems "better" and what the plan says, follow the plan.
- **Test tickers:** GME, RRC, RFP, AAPL, META — use these throughout.
- **Mock external APIs in tests.** Never hit real EDGAR, yfinance, or OpenInsider APIs in tests — use `responses` or `unittest.mock`.
