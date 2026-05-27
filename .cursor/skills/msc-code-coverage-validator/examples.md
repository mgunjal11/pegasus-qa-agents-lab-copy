# Example: MSC-205866 coverage validation

Illustrative output (abbreviated). Numbers are fictional for format reference.

## Coverage validation: MSC-205866 — Add retry on RASP submission timeout

**Jira**: [MSC-205866](https://wbdstreaming.atlassian.net/browse/MSC-205866)  
**Status**: In Review | **Type**: Story

### Linked PR(s)

| PR | Repo | State | Title | Dev tests | CI status |
|----|------|-------|-------|-----------|------------|
| [#412](https://github.com/wbd-msc/media-lib-rasp/pull/412) | `wbd-msc/media-lib-rasp` | open | Add retry on RASP timeout | `test_rasp_client.py` | Passed |

### Coverage summary

| Metric | Value | Notes |
|--------|-------|-------|
| Dev code coverage | **83.3%** (5/6 scored) | Jira AC → production code |
| Dev unit/integration test coverage | **80.0%** (4/5 dev-owned) | Unit & integration tests — 3 unit, 1 integration |
| QA scope remaining | **2 items** | 1 E2E, 1 Spot-check |
| CI line coverage | **87.2%** | Source: codecov |
| CI branch coverage | **79.1%** | Codecov PR comment |

**Verdict**: Pass with gaps — R6 (max retry cap) partially implemented; no dedicated test for cap.

### Dev vs QA test ownership

#### Covered by dev tests (unit / integration)
- **R1** Retry on HTTP 504 — integration: `tests/test_rasp_client.py::test_retries_on_504`
- **R2** Exponential backoff — unit: `tests/test_rasp_client.py` (mocked client)
- **R4** Surface final error — unit: `tests/test_rasp_client.py::test_raises_after_max_retries`
- **R5** Default max retries = 3 — unit: `tests/test_rasp_client.py::test_default_max_retries`

#### QA handoff
- **R3** Log each retry at WARNING — **Spot-check**: dev tests don't assert log level; verify in staging logs
- **R6** Configurable max retries via env — **E2E**: env override needs deployment config validation in staging
- **R7** (if present) Dashboard shows retry count — **Manual**: UI verification in ops dashboard

### Requirements traceability

| ID | Requirement (from Jira) | Code | Dev tests | Owner | QA scope | Evidence |
|----|-------------------------|------|-----------|-------|----------|----------|
| R1 | Retry on HTTP 504 from RASP API | Implemented | Covered (Integration) | Dev | None | `tests/test_rasp_client.py::test_retries_on_504` |
| R2 | Exponential backoff between retries | Implemented | Covered (Unit) | Dev | None | `src/rasp/client.py:_backoff` |
| R3 | Log each retry at WARNING | Implemented | Partial (Unit) | Shared | Spot-check | logging calls; no assert on level |
| R4 | Surface final error to caller after exhaustion | Implemented | Covered (Unit) | Dev | None | `test_raises_after_max_retries` |
| R5 | Default max retries = 3 | Implemented | Covered (Unit) | Dev | None | `test_default_max_retries` |
| R6 | Configurable max retries via env `RASP_MAX_RETRIES` | Partial | Missing | Shared | E2E | Env read added; no test |

### Implementation review

#### Correctly implemented
- R1–R2: Retry and backoff match AC; uses tenacity consistent with repo patterns.

#### Gaps and concerns
- 🟡 **High**: R6 env override lacks dev test; QA must validate in staging with env set.
- 🟢 **Medium**: R3 logging not asserted in unit tests; QA spot-check recommended.

### Recommended actions
1. **Dev**: Add `test_max_retries_from_env` (unit) for R6.
2. **Dev**: Assert WARNING log on retry in existing retry test (R3).
3. **QA**: E2E in staging — set `RASP_MAX_RETRIES=5`, trigger 504, confirm retry cap and logs.
