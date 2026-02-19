<!--
=== Sync Impact Report ===
Version change: N/A (initial) → 1.0.0
Modified principles: N/A (first adoption)
Added sections:
  - Principle I: Code Quality
  - Principle II: Testing Standards (NON-NEGOTIABLE)
  - Principle III: User Experience Consistency
  - Principle IV: Performance Requirements
  - Section: Development Workflow
  - Section: Quality Gates
  - Section: Governance
Removed sections: N/A
Templates requiring updates:
  - .specify/templates/plan-template.md ✅ no update needed (Constitution Check is dynamic)
  - .specify/templates/spec-template.md ✅ no update needed (generic requirements/criteria)
  - .specify/templates/tasks-template.md ✅ no update needed (supports test phases)
  - .specify/templates/checklist-template.md ✅ no update needed (generic structure)
Follow-up TODOs: None
=== End Report ===
-->

# AuctionAI Constitution

## Core Principles

### I. Code Quality

All code committed to this repository MUST meet the following standards:

- **Type Safety**: TypeScript `strict` mode MUST remain enabled in the
  frontend. Python type hints MUST be used for all function signatures,
  return types, and public module-level variables.
- **Linting & Formatting**: Ruff (backend) and ESLint (frontend) MUST
  pass with zero errors before any code is merged. Line length limit
  is 120 characters for Python, default ESLint rules for TypeScript.
- **Single Responsibility**: Each module, class, and function MUST have
  one clear purpose. Functions exceeding 50 lines SHOULD be decomposed
  unless doing so reduces readability.
- **No Dead Code**: Unused imports, variables, functions, and commented-out
  code blocks MUST be removed before merge.
- **Explicit Over Implicit**: Magic numbers, implicit type coercions, and
  undocumented side effects are prohibited. Constants MUST be named.
  Configuration values MUST come from environment or config files.
- **Error Handling**: All external I/O (API calls, file operations, DB
  queries) MUST have explicit error handling. Backend endpoints MUST
  return structured error responses with appropriate HTTP status codes.

### II. Testing Standards (NON-NEGOTIABLE)

Testing is mandatory for backend logic. Frontend testing coverage MUST
be established and expanded incrementally.

- **Backend Coverage**: Every new backend service function and API endpoint
  MUST have at least one corresponding test. Tests MUST use pytest with
  pytest-asyncio for async code.
- **Test Organization**: Tests MUST be organized by concern:
  `tests/unit/` for isolated logic, `tests/integration/` for multi-component
  flows, `tests/contract/` for API contract verification.
- **Test Naming**: Test files MUST follow the pattern `test_<module>.py`.
  Test functions MUST follow `test_<behavior_under_test>`.
- **Async Testing**: All async functions MUST be tested with async test
  fixtures. `asyncio_mode = "auto"` MUST remain configured in pytest.ini.
- **AI/LLM Tests**: Tests involving Anthropic Claude API calls MUST use
  mocked responses to ensure determinism, speed, and cost control.
  Integration tests against live APIs are permitted only in dedicated
  CI stages with explicit opt-in.
- **Frontend Testing**: New React components MUST include at minimum a
  render test. Hooks with business logic MUST have unit tests.
  This requirement applies to all new code going forward.
- **No Test Pollution**: Each test MUST be independent. Database state
  MUST be reset between tests. No test may depend on execution order.

### III. User Experience Consistency

The frontend MUST deliver a coherent, predictable experience across all
user-facing surfaces.

- **Design System**: All UI components MUST use Tailwind CSS utility
  classes. Custom CSS is prohibited unless Tailwind cannot express the
  required style. Component visual patterns (spacing, colors, typography)
  MUST be consistent across pages.
- **Loading States**: Every async operation visible to the user MUST
  display a loading indicator. WebSocket progress updates MUST render
  incrementally, not batch after completion.
- **Error Feedback**: All user-facing errors MUST display a human-readable
  message in Korean. Raw API error payloads MUST NOT be shown to users.
  Error states MUST provide a recovery action (retry button, navigation
  link, or clear guidance).
- **Responsive Layout**: All pages MUST be usable on viewport widths from
  768px (tablet) through 1920px (desktop). Mobile-first is NOT required
  but tablet support is mandatory.
- **Accessibility Baseline**: Interactive elements MUST have visible focus
  indicators. Form inputs MUST have associated labels. Color MUST NOT
  be the sole means of conveying information.
- **Data Visualization**: Charts (Recharts) MUST include axis labels,
  tooltips, and a legend when multiple series are present. Number
  formatting MUST use Korean locale conventions (KRW currency, Korean
  number grouping).

### IV. Performance Requirements

The system MUST meet the following performance thresholds under normal
operating conditions (single-user to 10 concurrent users).

- **API Response Time**: Non-AI endpoints (health, file list, history)
  MUST respond within 200ms (p95). AI analysis initiation endpoint MUST
  respond within 500ms (p95) — actual analysis runs asynchronously.
- **Frontend Load**: Initial page load (LCP) MUST complete within 2
  seconds on a standard broadband connection. Bundle size MUST NOT
  exceed 500KB gzipped for the initial chunk.
- **WebSocket Latency**: Progress updates from backend to frontend MUST
  be delivered within 100ms of event emission. Connection establishment
  MUST succeed within 1 second.
- **Database Operations**: SQLite read queries MUST complete within 50ms.
  Write operations (analysis result persistence) MUST complete within
  200ms. Database file size SHOULD be monitored and archived if it
  exceeds 500MB.
- **PDF Processing**: Document parsing MUST handle files up to 50MB.
  OCR fallback MUST complete within 30 seconds per page. Total
  document parsing MUST complete within 2 minutes for standard
  auction documents (< 20 pages).
- **Memory**: Backend process MUST NOT exceed 1GB RSS under normal
  operation. Frontend browser tab MUST NOT exceed 200MB heap.
- **Graceful Degradation**: If any AI analysis node fails after retries,
  the system MUST return partial results with clear indication of
  which analyses succeeded and which failed.

## Development Workflow

All contributors MUST follow this workflow for code changes:

- **Branch Strategy**: Feature work MUST happen on dedicated branches.
  Branch names MUST follow the pattern `<type>/<description>`
  (e.g., `feat/investment-calculator`, `fix/score-calculation`).
- **Commit Messages**: Commits MUST use conventional commit format:
  `<type>: <description>`. Types: feat, fix, refactor, docs, test,
  chore. Korean descriptions are acceptable.
- **Pre-Merge Checklist**:
  1. All backend tests pass (`pytest`)
  2. Ruff linting passes (`ruff check`)
  3. Frontend builds without errors (`npm run build`)
  4. ESLint passes (`npm run lint`)
- **Code Review**: Changes affecting AI pipeline logic, database schema,
  or API contracts MUST be reviewed before merge.
- **Environment Variables**: Secrets and API keys MUST NEVER be committed.
  New environment variables MUST be documented in `.env.example`.

## Quality Gates

Quality gates define mandatory checkpoints that MUST pass before code
progresses through the development pipeline.

- **Gate 1 — Local Validation**: Developer MUST run `pytest` (backend)
  and `npm run build` (frontend) before pushing. Both MUST pass.
- **Gate 2 — Lint Clean**: `ruff check backend/` and `npm run lint`
  MUST report zero errors. Warnings SHOULD be addressed but do not
  block.
- **Gate 3 — Type Safety**: TypeScript compilation (`tsc --noEmit`)
  MUST succeed with zero errors. Python type hints MUST be present
  on all new public functions.
- **Gate 4 — Test Coverage**: New backend code MUST have corresponding
  tests. Untested code MUST be explicitly justified in the PR
  description with a plan to add tests.
- **Gate 5 — Performance Baseline**: Changes to API endpoints or
  database queries MUST NOT regress response times beyond the
  thresholds defined in Principle IV. Manual verification is
  acceptable until automated benchmarks are established.
- **Gate 6 — UX Review**: Changes to user-facing components MUST be
  visually verified against Principle III requirements (loading
  states, error messages, responsive layout).

## Governance

This constitution is the authoritative source for development standards
in the AuctionAI project. All other guidance documents, specs, and task
definitions MUST be consistent with these principles.

- **Supremacy**: Where conflicts exist between this constitution and
  other project documents, the constitution takes precedence.
- **Amendments**: Changes to this constitution MUST be documented with
  a version bump, rationale, and updated Sync Impact Report.
  - MAJOR version: Removing or fundamentally redefining a principle.
  - MINOR version: Adding a new principle or materially expanding
    existing guidance.
  - PATCH version: Clarifications, typo fixes, non-semantic changes.
- **Compliance**: All pull requests and code reviews SHOULD verify
  adherence to these principles. Constitution violations MUST be
  flagged and resolved before merge.
- **Review Cadence**: This constitution SHOULD be reviewed quarterly
  or when a major architectural change is proposed, whichever
  comes first.

**Version**: 1.0.0 | **Ratified**: 2026-02-19 | **Last Amended**: 2026-02-19
