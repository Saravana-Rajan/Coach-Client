# Coach-Client Reassignment Detection & Handling

A full-stack system that detects coaching assignment changes from a simulated Salesforce source, syncs data locally, maintains an immutable audit trail, enforces role-based access control, and generates AI-powered transition briefs for newly assigned coaches.

**The core challenge:** Salesforce provides no change notifications or change events. On every sync, the application pulls the entire dataset and diffs it field-by-field against its local mirror to determine what changed -- additions, removals, modifications, and reassignments across coaches, accounts, clients, and assignments.

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Django 5, Django REST Framework |
| Frontend | React 18, TypeScript, Vite, CSS Modules |
| Charts | Recharts |
| Databases | SQLite x2 (app DB + simulated Salesforce DB) |
| AI | Google Gemini (transition briefs) |

## Setup Instructions

### Prerequisites

- Python 3.10+
- Node.js 18+
- A Google Gemini API key (optional, for AI transition briefs)

### Backend

```bash
cd backend
python -m venv venv
source venv/Scripts/activate  # Windows
pip install -r requirements.txt
python manage.py migrate --database=default
python manage.py migrate --database=salesforce
python manage.py seed_salesforce
python manage.py create_test_users
python manage.py runserver 8001
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Access the application at **http://localhost:5174**

### Environment Variables

Create a `.env` file in the `backend/` directory (or copy from `.env.example` if available):

```
GEMINI_API_KEY=your-key
DJANGO_SECRET_KEY=your-secret
```

| Variable | Description |
|---|---|
| `GEMINI_API_KEY` | Google Gemini API key for AI-powered transition briefs |
| `DJANGO_SECRET_KEY` | Django secret key (auto-generated default exists; change in production) |

## Test Credentials

| Username | Password | Role |
|---|---|---|
| admin | admin123 | Admin |
| arjun | arjun123 | Coach |
| deepa | deepa123 | Coach |
| karthik | karthik123 | Coach |
| sneha | sneha123 | Coach |
| vikram | vikram123 | Coach |

## Test Data Distribution

The `seed_salesforce` management command populates the simulated Salesforce database with:

- **5 coaches** with uneven distribution:

| Coach | Accounts | Clients |
|---|---|---|
| Arjun Mehta | 4 | 8 |
| Deepa Nair | 3 | 6 |
| Karthik Rajan | 2 | 4 |
| Sneha Iyer | 1 | 2 |
| Vikram Desai | 0 | 0 |

- **10 accounts** across industries: Technology, Healthcare, Finance, Manufacturing, Energy, Retail, Construction, Automotive
- **20 contacts** with Indian names, 2-3 per account

This uneven distribution is intentional -- it enables testing reassignment scenarios like bulk transfers, coaches going from zero to many clients, and vice versa.

## Architecture Overview

**Two separate databases** -- the simulated Salesforce source and the application database never share tables, schemas, or connections. The app reads from the source but never writes to it.

- `db_salesforce.sqlite3` -- Simulated Salesforce (source of truth). Modified via the Source Editor page to test scenarios.
- `db.sqlite3` -- Application database (local mirror, audit trail, transition briefs, users).

**Core data flow:**
1. Admin triggers a sync
2. Sync engine pulls entire dataset from Salesforce DB
3. Detector diffs current vs. previous state field-by-field
4. Changes are recorded as immutable audit records grouped by sync run
5. Reassignments trigger AI transition brief generation (non-blocking; failures are logged but do not break the sync)

For the full architecture breakdown, see `Docs/architecture.md`.

## Key Features

- **Full-dataset sync with diff-based change detection** -- Detects 14 change types including coach reassignments, field modifications, record additions/removals, status changes, and schema changes
- **Immutable audit trail** -- Every detected change is logged with timestamps, old/new values, and the sync run that produced it. No edit or delete. Syncs with zero changes produce zero audit records.
- **API-level access control** -- Enforced at the API layer, not just the UI. Coaches can only access their own data; direct API calls for another coach's data are denied. Admins have full visibility.
- **AI transition briefs** -- Google Gemini generates human-readable handoff briefs when a client is reassigned, using real client and account data. AI failures are logged but never block the sync.
- **Real-time schema change detection** -- Detects when Salesforce schema changes (new fields, removed fields, type changes) during sync
- **Admin management panel** -- Full CRUD operations and bulk actions for coaches, accounts, clients, and assignments in the Salesforce source
- **Source Editor** -- Direct manipulation of simulated Salesforce data for testing edge cases and reassignment scenarios
- **Sync notifications** -- Notify coaches that "something changed" without revealing what changed
- **Dark/light theme** -- User-selectable theme across the entire application
- **Dashboard analytics** -- Visual charts and statistics via Recharts

## How to Test Edge Cases

The system is designed to handle approximately 15 real-world edge case scenarios. To test them:

1. **Source Editor page** (Admin only) -- Directly modify the simulated Salesforce data: reassign clients between coaches, add/remove records, change field values, and modify schema
2. **Admin Management page** -- Perform CRUD and bulk operations on coaches, accounts, clients, and assignments

### Example test flow:

1. Log in as `admin`
2. Trigger an initial sync from the Admin Dashboard
3. Go to Source Editor -- make changes (e.g., reassign a client from Arjun to Vikram, deactivate a coach, add a new account)
4. Trigger sync again
5. Check the Audit Trail for detected changes
6. Check Transition Briefs for any AI-generated handoff documents
7. Log in as the affected coaches to verify they see only their own data

For the full edge case test report with documented pass/fail results and evidence, see `Docs/edge-case-test-report.md`.

## Project Structure

```
Coach-Client/
├── backend/
│   ├── config/              # Django settings, URLs, WSGI
│   ├── coaching/            # Core models (Coach, Account, Contact, Assignment)
│   ├── sync/                # Sync engine, change detector, audit models
│   ├── briefs/              # AI transition brief generation (Gemini)
│   ├── users/               # Authentication and user management
│   ├── admin_management/    # Admin CRUD/bulk operations API
│   ├── salesforce_sim/      # Simulated Salesforce source models
│   ├── salesforce_connector/# Salesforce DB router and connection logic
│   ├── db.sqlite3           # Application database
│   └── db_salesforce.sqlite3# Simulated Salesforce database
├── frontend/
│   └── src/
│       ├── pages/           # All page components (Dashboard, Audit Trail, etc.)
│       ├── components/      # Shared UI components
│       ├── context/         # React context (auth, theme)
│       ├── api/             # API client functions
│       └── types.ts         # TypeScript type definitions
├── Docs/
│   ├── coach-client-reassignment-PRD.md   # Full product requirements
│   └── edge-case-test-report.md           # Edge case test results
└── sf-deploy/               # Salesforce deployment configuration
```
