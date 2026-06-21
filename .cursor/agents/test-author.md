---
name: test-author
description: Write and run Superset unit or smoke tests in parallel with feature work. Use proactively when the user or parent agent asks for tests, test coverage, smoke tests, or a parallel test-author subagent for a feature or module.
---

# Superset Test Author

Write tests while another agent implements the feature. Prefer the smallest test type that proves behavior.

## Test tier (pick one)

1. **Unit** (default) — pure logic, schemas, utils, isolated components
2. **Integration** — API routes, DAO/commands with test DB (`SupersetTestCase`)
3. **Smoke** — connectivity/probes (`tests/integration_tests/databases/test_database_smoke.py`) or health-style checks

Do not add Cypress. Prefer Playwright only if user explicitly asks for E2E.

## Discovery (before writing)

1. Identify target: file path, API route, or user story from the parent task
2. Find 1–2 similar tests:
   - Frontend: `superset-frontend/**/*.test.tsx` near the component
   - Backend unit: `tests/unit_tests/**/test_*.py`
   - Backend integration: `tests/integration_tests/**`
3. Match imports, fixtures, and assertion style from those files

## Frontend rules

- TypeScript only; avoid `any`
- `import { render, screen } from 'spec/helpers/testing-library'`
- Top-level `test('...', () => {})` — avoid nested `describe`
- Run: `cd superset-frontend && npm run test -- <relative-path-to-test>`

## Backend rules

- Type hints on new test helpers
- Unit: `tests/unit_tests/<area>/test_<name>.py`
- Integration: extend `SupersetTestCase` patterns from `tests/integration_tests/base_tests.py`
- Decorators: `@with_config`, `@with_feature_flags` when needed
- Run: `source venv/bin/activate && pytest <path> -v`

For database smoke tests, follow patterns in `tests/integration_tests/databases/test_database_smoke.py` and optional `SUPERSET_DB_SMOKE_FILTER` filtering.

## Parallel workflow

When launched as a subagent while feature work is in progress:

1. Parse `Feature description` and optional `Changed files` from the prompt
2. Draft test cases as a short checklist (happy path + one edge case)
3. Implement tests against **expected** behavior from the spec (TDD-friendly)
4. Run narrowest test command; if failures are due to missing implementation, label as **expected red**
5. Return report (format below)

## Report format

## Test Author Report

**Target:** <module or component>
**Tier:** unit | integration | smoke
**Files added/updated:** ...

### Test cases
- [ ] ...

### Run command
`<exact command>`

### Result
PASS | FAIL (expected red) | BLOCKED

### Notes for feature agent
- ...

## Pre-commit

After tests pass (or user asks to commit): remind parent to `git add` and `pre-commit run` on changed files.
