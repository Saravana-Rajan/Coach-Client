# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Coach-Client Reassignment Detection & Handling system. Detects coaching assignment changes from a simulated Salesforce source (full-dataset pull, no change events), syncs data locally, maintains an immutable audit trail, enforces role-based access control, and generates AI-powered transition briefs for newly assigned coaches.

Full PRD: `Docs/coach-client-reassignment-PRD.md`

## Architecture (from PRD)

**Two separate data stores** — the simulated Salesforce source and the application database must never share tables, schemas, or connections. The app reads from the source but never writes to it.

**Core data model:**
- Coaches (name, email, active client count, active status)
- Accounts (company being coached, assigned to one coach)
- Contacts/Clients (individual at an account, assigned to one coach)
- Coach-Client Assignments (coach ↔ client ↔ account with status)

**Key constraint:** Sync pulls the entire dataset every time. No change notifications — the app must diff current vs. previous state to detect what changed.

**Five implementation phases:**
1. **Data Sync** — Full pull from source, mirror locally, admin-triggered
2. **Change Detection & Audit Trail** — Diff-based detection, immutable audit records grouped by sync run
3. **Access Control & Dashboard** — API-level enforcement (not just UI), coach sees only their data, admin sees all
4. **AI Transition Briefs** — Auto-generated on reassignment using real data, AI failure must not break sync
5. **Edge Case Testing** — ~15 real-world scenarios; document pass/fail with evidence

**User roles:** Coach (scoped to own data) and Admin (full visibility, sync controls, audit trail access)

## Test Data Distribution

- 5 coaches: Alice, Bob, Carol, Dave, Eve (Eve starts with no assignments)
- 10 accounts distributed unevenly across coaches
- 20 clients (2-3 per account)
- Initial: Alice=4 accounts/8 clients, Bob=3/6, Carol=2/4, Dave=1/2, Eve=0/0

## Key Requirements to Remember

- Sync notification must only say "something changed" — never what changed
- Audit records are immutable — no edit or delete
- Syncing with no changes must produce zero audit records
- Access control enforced at API level — direct API calls by a coach must be denied for other coaches' data
- AI brief failures must be logged but must not fail the sync
- All API responses must follow a consistent structure
