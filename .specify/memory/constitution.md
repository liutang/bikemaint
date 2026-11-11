<!--
Sync Impact Report
Version change: 1.1.0 → 1.2.0
Rationale: MINOR bump — new "Git Practices" guidance added under Development Workflow,
  materially expanding governance guidance without redefining or removing any existing principle.
Modified principles: none
Added sections:
  - Git Practices (new, appended to Development Workflow)
Removed sections: none
Deferred TODOs: none
Templates requiring follow-up: none — this command only amends the constitution;
  dependent templates (plan/spec/tasks) read it at runtime and are not modified here.
-->

# BikeMaint Constitution

## Core Principles

### I. Simplicity Over Cleverness
Code MUST favor the plainest solution that correctly solves the problem at hand. Clever,
implicit, or overly abstract constructs are prohibited when a direct, readable alternative
exists. Every abstraction (base class, decorator, metaclass, generic helper) MUST earn its
place by removing real duplication or complexity — not by anticipating hypothetical future
needs. When two approaches are equally correct, the one a new contributor can understand
fastest wins.

### II. Modular, Non-Monolithic Design
The application MUST be organized into small, independently understandable modules with
clear boundaries (e.g., routers, services/business logic, data access, templates) rather
than a single monolithic file or layer. Each module MUST have one clear responsibility and
MUST NOT reach into another module's internals; cross-module communication happens through
explicit interfaces (function signatures, Pydantic models, dependency-injected services).
Modules MUST be independently testable without booting the entire application.

### III. Test-Driven Development (NON-NEGOTIABLE)
All new behavior MUST be developed test-first: write a failing test that encodes the
requirement, get it reviewed/approved, watch it fail, then write the minimal code to make
it pass, then refactor. This applies to routes, business logic, and data-access code alike.
No pull request may merge with untested new behavior, and the Red-Green-Refactor cycle is
not optional under deadline pressure — shipping without tests is treated as a defect, not a
shortcut.

### IV. Security by Default
Security is a default requirement, not an add-on. All user input MUST be validated at the
boundary (Pydantic models/FastAPI validation) before use. All database access MUST use
parameterized queries — string-built SQL is prohibited. Secrets and credentials MUST come
from environment configuration, never hard-coded or committed. Authentication/authorization
checks MUST happen server-side on every protected route; HTMX partial responses are not
exempt from the same authorization rules as full-page routes. Dependencies MUST be kept
current with known vulnerabilities addressed promptly.

### V. Human-Readable Observability
Every log line MUST be understandable by a human operator without cross-referencing source
code: use clear, complete sentences or structured key=value pairs, include the relevant
identifiers (e.g., request id, resource id), and avoid cryptic codes or stack-trace-only
errors for expected failure paths. Logs MUST distinguish severity correctly (debug/info/
warning/error) and MUST NOT log secrets, credentials, or full request bodies containing
sensitive data.

## Technology Stack

The project's stack is fixed to keep the codebase small and consistent: **FastAPI** for the
web/API layer, **HTMX** for interactivity (server-rendered HTML fragments over the wire,
no SPA framework or client-side build pipeline), **Jinja2** for templates, and **SQLite** as
the database. This combination MUST NOT be diversified (e.g., adding a second templating
engine, a frontend framework, or an alternate database) without a constitution amendment
justifying the change and its migration impact. Server-rendered HTML plus HTMX is the
default pattern for all interactive UI; introducing client-side JavaScript frameworks
requires the same amendment process.

## Project Structure

The repository MUST follow a fixed top-level layout so that the module boundaries required by
Principle II are visible from the filesystem, not just from code review:

- `app/` — all application source code, organized by responsibility:
  - `app/routers/` — FastAPI route handlers only; no business logic and no direct database
    queries.
  - `app/services/` — business logic; MUST be callable independently of HTTP and MUST NOT
    import FastAPI or any request/response objects.
  - `app/models/` — Pydantic request/response schemas and SQLite row/table models.
  - `app/db/` — database connection setup, parameterized query functions, and migrations.
  - `app/templates/` — Jinja2 templates, including HTMX partial fragments.
  - `app/static/` — CSS/JS/image assets served as-is; no build pipeline output is committed.
- `tests/` — mirrors the `app/` layout (e.g., `tests/services/test_x.py` tests
  `app/services/x.py`) so every module has one obvious, discoverable test location.
- `.specify/` — Spec Kit governance artifacts (constitution, specs, plans, scripts). It
  MUST NOT contain application source code.

A file's directory MUST match its responsibility regardless of its contents: a router file
containing business logic, or a service file importing FastAPI, is a Principle II violation
even though it is placed correctly by name. Introducing a new top-level directory, or a new
subdirectory under `app/` with a distinct responsibility, requires a constitution amendment
naming the directory and its boundary.

## Development Workflow

Every pull request MUST demonstrate the TDD cycle (failing test → passing test) for the
behavior it introduces or changes. Code review MUST verify: (1) module boundaries and the
required directory layout are respected (Principle II, Project Structure), (2) no unvalidated
input reaches the database or templates (Principle IV), and (3) new log statements are
readable and correctly leveled (Principle V). Reviewers reject PRs that introduce cleverness
without justification (Principle I), that expand the technology stack without an accompanying
constitution amendment, or that place files outside the structure defined above.

### Git Practices

- `main` MUST always be in a deployable state. All non-trivial work happens on short-lived
  feature branches created from `main` and merged back via pull request; direct pushes to
  `main` are reserved for previously-agreed trivial exceptions (e.g., a one-line typo fix)
  and MUST still pass CI before landing.
- Commits MUST be atomic: each commit represents one logical, reviewable change and leaves
  the codebase in a working state. Squash exploratory or fixup commits before merge rather
  than merging a noisy history.
- Commit messages MUST be written in the imperative mood (e.g., "Add retry logic", not
  "Added" or "Adding"), with a concise summary line and, when the reasoning is not obvious
  from the diff, a body explaining *why* the change was made.
- Merging to `main` MUST go through a pull request that satisfies the review requirements
  above; force-pushing to `main` or any other shared branch is prohibited, as is rewriting
  history that has already been pushed and reviewed by someone else.
- Secrets, credentials, and generated/build artifacts MUST NOT be committed. `.gitignore`
  MUST be kept current so this is enforced before history is created, reinforcing Principle
  IV rather than relying on after-the-fact cleanup.

## Governance

This constitution supersedes any conflicting practice, style guide, or prior convention in
this repository. Amendments are made by editing this file directly, incrementing the
version per the policy below, and recording the change in a Sync Impact Report comment at
the top of the file. Versioning follows semantic versioning: MAJOR for backward-incompatible
governance or principle removals/redefinitions, MINOR for new principles or materially
expanded guidance, PATCH for clarifications and wording fixes. Every pull request MUST be
reviewed for compliance with this constitution before merge; unjustified complexity,
untested behavior, stack deviations, or directory-structure violations are grounds for
rejection. Use this document as the runtime source of truth for `/speckit-plan`,
`/speckit-tasks`, and `/speckit-implement`.

**Version**: 1.2.0 | **Ratified**: 2026-09-15 | **Last Amended**: 2026-09-15
