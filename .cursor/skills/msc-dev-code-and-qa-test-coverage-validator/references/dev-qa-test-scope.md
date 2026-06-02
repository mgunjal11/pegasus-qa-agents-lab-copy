# Dev vs QA test scope classification

Use this guide when mapping each Jira requirement to **who verifies it** and **what automated test tier** applies in the PR.

## Ownership model

| Owner | Responsibility |
|-------|----------------|
| **Dev** | Unit and integration tests in the PR prove the requirement; QA may spot-check only |
| **Shared** | Dev covers logic/API boundaries; QA validates end-to-end or cross-system behavior |
| **QA** | No practical automated coverage in the PR; QA owns functional, E2E, UI, or environment-specific verification |

## Dev test tiers

Classify automated test evidence in the PR diff by **path, framework, and assertion style**:

| Tier | Typical signals | Examples |
|------|-----------------|----------|
| **Unit** | Isolated module; mocks/stubs for I/O; fast; no real DB/network | `tests/unit/`, `*_test.go` with mocks, Jest/Vitest unit suites, `@pytest.mark.unit` |
| **Integration** | Real or test-double service boundaries; DB/API/client wiring; multi-module | `tests/integration/`, Testcontainers, `@SpringBootTest`, HTTP client against test server, contract tests |
| **Both** | Requirement has explicit unit **and** integration test evidence | Retry logic unit-tested + API client integration test |

If tier is unclear, infer from test file location, fixtures, and whether external systems are mocked.

## QA scope labels

| QA scope | When to use |
|----------|-------------|
| **None** | Dev unit/integration tests in the PR fully cover the requirement — **do not** list mapped test plan cases under QA handoff for this requirement |
| **Spot-check** | Dev tests cover core logic; QA confirms in staging (config, logging, observability, happy path) |
| **E2E** | Multi-service or UI workflow; production-like data; cannot be asserted in PR tests alone |
| **Manual** | Visual/UX, exploratory, permissions in real env, ops runbooks, or compliance sign-off |
| **Regression** | Existing behavior touched; QA re-runs related suite even if dev added tests |

## Classification rules (apply per requirement)

1. **Parse the requirement** — Is it API/logic, UI, cross-system workflow, NFR (perf/security), or process/docs?

2. **Check PR test evidence** — Unit file? Integration file? Both? Indirect only?

3. **Assign owner**
   - Pure backend logic with unit + integration tests → **Dev**, QA scope **None** or **Spot-check**
   - API contract with integration test only → **Dev** (integration), QA scope **Spot-check** or **E2E** if downstream consumers exist
   - UI label, layout, accessibility → **QA** or **Shared** (if component unit tests exist)
   - End-user journey across apps → **QA**, QA scope **E2E**
   - Logging/metrics → **Shared** — dev asserts in unit/integration; QA **Spot-check** in staging
   - Performance SLAs → **QA** (load/staging) unless PR includes benchmark test
   - Docs-only / process → **N/A** for both tiers

4. **Dev test status** (for Dev/Shared items only)
   - **Covered** — Correct tier test clearly exercises the requirement
   - **Partial** — Wrong tier (unit only when integration needed), weak assertion, or indirect
   - **Missing** — No automated test in PR for dev-owned scope
   - **N/A** — QA-only requirement

5. **Do not double-count** — A requirement covered by integration tests counts as dev-covered even if no separate unit test exists, unless AC explicitly requires both.

## Scoring

**Dev test coverage %** (dev-owned requirements only)

```
dev_score(R) = 1.0 if Dev test status Covered
             = 0.5 if Partial
             = 0.0 if Missing
             = excluded if N/A (QA-only or non-code)

dev_test_coverage_pct = round(100 * sum(dev_score) / count(dev-scored items), 1)
```

**QA scope summary** (informational, not a percentage gate)

- Count requirements by QA scope: None, Spot-check, E2E, Manual, Regression
- **QA remaining** = items where QA scope is E2E, Manual, or Regression, **plus** Shared/Dev items where Dev test status is Partial or Missing
- **QA scope None** = Dev test status **Covered** — `build_qa_ownership_fields()` omits these from §4 QA handoff and limits “execute test plan” bullets to TCs mapped only to requirements that still need QA

Report both the dev coverage % and a plain-language QA handoff list. `map_requirements_to_diff.py` sets `qaScope: none` when `devTestStatus` is **covered** (see `derive_owner_and_qa_scope()`).

## Evidence to cite

For dev tests, cite:
- Test file path and test name
- Tier: `(unit)` or `(integration)`
- What is mocked vs real

For QA scope, cite:
- Why PR tests cannot fully verify (e.g. "UI flow", "requires prod-like entitlement")
- Suggested QA scenario (one line)
