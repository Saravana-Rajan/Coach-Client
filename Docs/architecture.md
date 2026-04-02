# Architecture Document -- Coach-Client Reassignment Detection & Handling

**Version:** 1.0
**Date:** 2026-03-25
**Status:** Living document
**PRD Reference:** `Docs/coach-client-reassignment-PRD.md`

---

## Table of Contents

1. [System Overview](#1-system-overview)
2. [Tech Stack](#2-tech-stack)
3. [Data Model](#3-data-model)
4. [Sync Flow](#4-sync-flow)
5. [Change Detection Algorithm](#5-change-detection-algorithm)
6. [Access Control](#6-access-control)
7. [Schema Change Detection](#7-schema-change-detection)
8. [API Endpoints](#8-api-endpoints)
9. [Frontend Architecture](#9-frontend-architecture)
10. [Design Decisions & Trade-offs](#10-design-decisions--trade-offs)

---

## 1. System Overview

The Coach-Client Reassignment Detection & Handling system is a full-stack application that synchronizes coaching assignment data from a simulated Salesforce CRM, detects changes through full-dataset diffing, maintains an immutable audit trail of every modification, enforces role-based access control at the API level, and generates AI-powered transition briefs when coaches are reassigned.

### Core Problem

Coaching organizations manage coach-to-client assignments in Salesforce, but Salesforce provides no change notifications. The system receives the complete dataset on every pull and must determine what changed since the previous sync.

### High-Level Architecture

```
+---------------------+        +-----------------------+        +------------------+
|                     |  Pull  |                       |  REST  |                  |
|  Salesforce Source  |------->|   Django Backend       |<------>|  React Frontend  |
|  (db_salesforce)    |        |   (db.sqlite3)        |        |  (Vite + TS)     |
|                     |        |                       |        |                  |
+---------------------+        +-----------------------+        +------------------+
                                        |
                                        | API Call
                                        v
                               +------------------+
                               |  Google Gemini   |
                               |  2.0 Flash       |
                               |  (AI Briefs)     |
                               +------------------+
```

### Key Capabilities

- **Data Sync** -- Full pull from simulated Salesforce source, diff against local state, update application database.
- **Change Detection** -- 14 distinct change types across coaches, accounts, contacts, and assignments.
- **Immutable Audit Trail** -- Every detected change is recorded permanently. No edits, no deletes.
- **Role-Based Access Control** -- Coaches see only their own data; admins see everything. Enforced at the API layer.
- **AI Transition Briefs** -- On reassignment, an AI-generated briefing document is created for the new coach. AI failures never block the sync.
- **Schema Change Detection** -- Automatic detection and migration of Salesforce schema changes.

---

## 2. Tech Stack

### Backend

| Component              | Technology                  | Version |
|------------------------|-----------------------------|---------|
| Web Framework          | Django                      | 5.0     |
| REST API               | Django REST Framework (DRF) | 3.15    |
| Python Runtime         | Python                      | 3.13    |
| AI Provider            | Google Gemini 2.0 Flash     | --      |
| Salesforce Integration | simple_salesforce            | --      |

### Frontend

| Component       | Technology       | Version |
|-----------------|------------------|---------|
| UI Library      | React            | 18.3    |
| Language         | TypeScript       | --      |
| Build Tool      | Vite             | 5.4     |
| Styling         | CSS Modules      | --      |
| Charts          | Recharts         | --      |
| Design System   | PentEdge CRM    | Custom  |

### Data Stores

| Database                 | Engine  | File                    | Purpose                              |
|--------------------------|---------|-------------------------|--------------------------------------|
| Application Database     | SQLite  | `db.sqlite3`            | App models, audit trail, users       |
| Salesforce Source (Sim)  | SQLite  | `db_salesforce.sqlite3` | Simulated Salesforce CRM data        |

The two databases are physically separate files. Django's database router (`config/db_router.py`) ensures all `salesforce_sim` models read from and write to the `salesforce` database alias, while all other models use the `default` database. Cross-database foreign keys are prohibited.

---

## 3. Data Model

### Entity Relationship Diagram

```
SALESFORCE SOURCE DB (db_salesforce.sqlite3)         APPLICATION DB (db.sqlite3)
================================================     ================================================

+----------------+                                   +----------------+
|   SFCoach      |                                   |   Coach        |
|----------------|                                   |----------------|
| id       (PK)  |                                   | id       (PK)  |
| sf_id    (UUID) |                                   | sf_id    (UUID) |
| name           |                                   | name           |
| email          |                                   | email          |
| active_clients |                                   | active_clients |
| is_active      |                                   | is_active      |
+-------+--------+                                   +-------+--------+
        |                                                     |
        | 1:N                                                 | 1:N
        v                                                     v
+----------------+                                   +----------------+
|   SFAccount    |                                   |   Account      |
|----------------|                                   |----------------|
| id       (PK)  |                                   | id       (PK)  |
| sf_id    (UUID) |                                   | sf_id    (UUID) |
| name           |                                   | name           |
| industry       |                                   | industry       |
| website        |                                   | website        |
| coaching_start |                                   | coaching_start |
| coach_id  (FK) |---> SFCoach                       | coach_id  (FK) |---> Coach
+-------+--------+                                   +-------+--------+
        |                                                     |
        | 1:N                                                 | 1:N
        v                                                     v
+----------------+                                   +----------------+
|   SFContact    |                                   |   Contact      |
|----------------|                                   |----------------|
| id       (PK)  |                                   | id       (PK)  |
| sf_id    (UUID) |                                   | sf_id    (UUID) |
| name           |                                   | name           |
| title          |                                   | title          |
| phone          |                                   | phone          |
| email          |                                   | email          |
| account_id(FK) |---> SFAccount                     | account_id(FK) |---> Account
| coach_id  (FK) |---> SFCoach                       | coach_id  (FK) |---> Coach
+----------------+                                   +----------------+

+------------------+                                 +------------------+
|  SFAssignment    |                                 |  Assignment      |
|------------------|                                 |------------------|
| id         (PK)  |                                 | id         (PK)  |
| sf_id      (UUID)|                                 | sf_id      (UUID)|
| coach_id   (FK)  |---> SFCoach                     | coach_id   (FK)  |---> Coach
| contact_id (FK)  |---> SFContact                   | contact_id (FK)  |---> Contact
| account_id (FK)  |---> SFAccount                   | account_id (FK)  |---> Account
| status           |                                 | status           |
+------------------+                                 +------------------+
  unique: (coach, contact)                             unique: (coach, contact)
```

### Application-Only Models

These models exist only in the application database and have no Salesforce counterpart.

```
+--------------------+        +---------------------+        +-----------------------+
|     SyncLog        |        |    AuditRecord      |        |   TransitionBrief     |
|--------------------|        |---------------------|        |-----------------------|
| id           (PK)  |<--+   | id            (PK)  |        | id              (PK)  |
| started_at         |   |   | sync_id  (FK,PROT.) |------->| sync_id    (FK,PROT.) |
| completed_at       |   +---|                      |   +--->| audit_record_id (FK)  |
| status             |       | change_type          |   |    | coach_id   (FK,NULL)  |
| changes_detected   |       | entity_type          |---+    | contact_name          |
| error_message      |       | entity_sf_id  (UUID) |        | account_name          |
+--------------------+       | entity_name          |        | previous_coach_name   |
                              | before_state  (JSON) |        | content         (text)|
                              | after_state   (JSON) |        | generated_at          |
                              | coach_name           |        +-----------------------+
                              | account_name         |
                              | detected_at          |
                              +----------------------+

+--------------------+        +---------------------+        +-----------------------+
|    CustomUser      |        | SyncNotification    |        | SchemaMigrationLog    |
|--------------------|        |---------------------|        |-----------------------|
| id           (PK)  |        | id            (PK)  |        | id              (PK)  |
| username           |        | out_of_sync  (bool) |        | detected_at           |
| password (hashed)  |        | last_notified       |        | applied_at            |
| role (coach/admin) |        | last_synced         |        | entity_type           |
| coach_sf_id (UUID) |        | message             |        | field_name            |
| (inherited fields) |        +---------------------+        | old_type              |
+--------------------+         Singleton (pk=1 only)         | new_type              |
                                                              | old_constraints (JSON)|
+---------------------+                                      | new_constraints (JSON)|
| BulkOperationLog    |                                      | status                |
|---------------------|                                      | migration_sql         |
| id            (PK)  |                                      | rollback_sql          |
| operation_type      |                                      | error_message         |
| performed_by        |                                      +-----------------------+
| performed_at        |
| details       (JSON)|
| affected_entities(J)|
| status              |
| error_message       |
+---------------------+
```

### AuditRecord Change Types (14 total)

| Change Type            | Entity     | Trigger Condition                          |
|------------------------|------------|--------------------------------------------|
| `coach_added`          | Coach      | Present in source, absent in local         |
| `coach_removed`        | Coach      | Absent in source, present in local         |
| `coach_updated`        | Coach      | Field value differs (name, email, etc.)    |
| `account_added`        | Account    | Present in source, absent in local         |
| `account_removed`      | Account    | Absent in source, present in local         |
| `account_reassigned`   | Account    | `coach` FK changed                         |
| `account_updated`      | Account    | Non-coach field value differs              |
| `contact_added`        | Contact    | Present in source, absent in local         |
| `contact_removed`      | Contact    | Absent in source, present in local         |
| `contact_reassigned`   | Contact    | `coach` FK changed                         |
| `contact_updated`      | Contact    | Non-coach field value differs              |
| `assignment_added`     | Assignment | Present in source, absent in local         |
| `assignment_removed`   | Assignment | Absent in source, present in local         |
| `assignment_updated`   | Assignment | Field value differs (status, etc.)         |

### Test Data Distribution

| Coach | Accounts | Clients | Notes                      |
|-------|----------|---------|----------------------------|
| Alice | 4        | 8       | Heaviest load              |
| Bob   | 3        | 6       |                            |
| Carol | 2        | 4       |                            |
| Dave  | 1        | 2       | Lightest active load       |
| Eve   | 0        | 0       | Starts with no assignments |

---

## 4. Sync Flow

The sync engine (`sync/engine.py`) executes a synchronous, all-or-nothing synchronization. Below is the step-by-step flow.

```
Admin clicks "Sync"  -or-  Webhook notification received
            |
            v
+---------------------------+
| 0. Schema Detection       |
|    Compare SF describe()  |
|    against saved baseline |
|    Auto-migrate if needed |
+------------+--------------+
             |
             v
+---------------------------+
| 1. Create SyncLog         |
|    status = "in_progress" |
+------------+--------------+
             |
             v
+---------------------------+
| 2. Pull ALL Source Data   |
|    SFCoach, SFAccount,    |
|    SFContact, SFAssignment|
|    (via .using("salesforce"))
+------------+--------------+
             |
             v
+---------------------------+
| 3. Pull ALL Local Data    |
|    Coach, Account,        |
|    Contact, Assignment    |
+------------+--------------+
             |
             v
+---------------------------+
| 4. Build Lookup Maps      |
|    SF PK -> coach name    |
|    local PK -> coach name |
+------------+--------------+
             |
             v
+---------------------------+
| 5. Change Detection       |
|    detector.py runs       |
|    diff on all 4 entities |
|    Returns change dicts   |
+------------+--------------+
             |
             v
+---------------------------+
| 6. Create AuditRecords    |
|    One per detected change|
|    Linked to SyncLog      |
+------------+--------------+
             |
             v
+---------------------------+
| 7. Collect Reassignment   |
|    Info for AI Briefs     |
+------------+--------------+
             |
             v
+---------------------------+
| 8. Update Local DB        |
|    update_or_create for   |
|    added/updated entities |
|    Delete removed entities|
+------------+--------------+
             |
             v
+---------------------------+
| 9. Handle Inactive Coaches|
|    Update active status   |
+------------+--------------+
             |
             v
+---------------------------+
| 10. Clear Notification    |
|     out_of_sync = False   |
+------------+--------------+
             |
             v
+---------------------------+
| 11. Generate AI Briefs    |
|     Non-blocking:         |
|     failure is logged but |
|     does NOT fail the sync|
+------------+--------------+
             |
             v
+---------------------------+
| 12. Finalize SyncLog      |
|     status = "completed"  |
|     changes_detected = N  |
|     completed_at = now()  |
+---------------------------+
```

### Key Invariants

- **No changes = no audit records.** If the diff produces zero changes, no `AuditRecord` rows are created and the `SyncLog` records `changes_detected = 0`.
- **Audit before update.** Change detection runs against the current local state before the local database is modified, ensuring the `before_state` JSON accurately reflects the pre-sync values.
- **AI failures are non-fatal.** If Gemini is unreachable or returns an error, the failure is logged and the sync completes normally.
- **Notification says "something changed" only.** The `SyncNotification.message` never reveals what specifically changed.

---

## 5. Change Detection Algorithm

The detection logic lives in `sync/detector.py`. It is a pure comparison module: it reads data but writes nothing.

### Algorithm (per entity type)

```
function detect_changes(source_entities, local_entities):
    source_map = { entity.sf_id -> entity  for entity in source_entities }
    local_map  = { entity.sf_id -> entity  for entity in local_entities  }

    changes = []

    // ADDED: in source but not in local
    for sf_id in source_map:
        if sf_id NOT in local_map:
            changes.append(added_change)

    // REMOVED: in local but not in source
    for sf_id in local_map:
        if sf_id NOT in source_map:
            changes.append(removed_change)

    // UPDATED or REASSIGNED: in both, compare fields
    for sf_id in intersection(source_map, local_map):
        if coach FK changed:
            changes.append(reassigned_change)   // accounts & contacts only
        if any other field changed:
            changes.append(updated_change)

    return changes
```

### Detection Functions

| Function                       | Entities Compared          | Change Types Produced                                    |
|--------------------------------|----------------------------|----------------------------------------------------------|
| `detect_coach_changes()`       | SFCoach vs Coach           | coach_added, coach_removed, coach_updated                |
| `detect_account_changes()`     | SFAccount vs Account       | account_added, account_removed, account_reassigned, account_updated |
| `detect_contact_changes()`     | SFContact vs Contact       | contact_added, contact_removed, contact_reassigned, contact_updated |
| `detect_assignment_changes()`  | SFAssignment vs Assignment | assignment_added, assignment_removed, assignment_updated |

### Change Dict Structure

Every change is represented as a dictionary with the following keys:

```python
{
    "change_type":    "contact_reassigned",     # One of 14 types
    "entity_type":    "contact",                # coach | account | contact | assignment
    "entity_sf_id":   UUID("..."),              # Stable SF identifier
    "entity_name":    "Jane Doe",               # Human-readable name
    "before_state":   { "coach": "Alice", ... },# JSON snapshot before change (null if added)
    "after_state":    { "coach": "Bob", ... },  # JSON snapshot after change (null if removed)
    "coach_name":     "Bob",                    # Current/new coach name
    "account_name":   "Acme Corp",              # Associated account (where applicable)
}
```

---

## 6. Access Control

### Design Principle

Access control is enforced at the API level, not just the UI. A direct API call from a coach requesting another coach's data returns HTTP 403 Forbidden.

### Implementation

```
Request arrives
      |
      v
+-----------------------------+
| Django Session Auth         |
| (SessionAuthentication)     |
+-------------+---------------+
              |
              v
+-----------------------------+
| get_coach_for_user(request) |
|                             |
| if user.role == "coach":   |
|   return Coach matching     |
|   user.coach_sf_id          |
| if user.role == "admin":   |
|   return None               |
+-------------+---------------+
              |
              v
+-----------------------------+
| View Permission Check       |
|                             |
| coach = get_coach_for_user()|
| if coach is not None:       |
|   filter queryset by coach  |
|   if entity.coach != coach: |
|     return 403 Forbidden    |
| else: (admin)               |
|   return full queryset      |
+-----------------------------+
```

### Access Rules by Entity

| Entity          | Coach Access                                   | Admin Access       |
|-----------------|------------------------------------------------|--------------------|
| Accounts        | Only accounts where `account.coach == coach`   | All accounts       |
| Contacts        | Only contacts where `contact.coach == coach`   | All contacts       |
| Assignments     | Only assignments where `assignment.coach == coach` | All assignments |
| Audit Records   | Denied (admin only)                            | Full access        |
| Sync Controls   | Denied (admin only)                            | Trigger, history   |
| Transition Briefs | Only briefs where `brief.coach == coach`     | All briefs         |

### Reassignment Impact on Access

When a client is reassigned from Coach A to Coach B during a sync:

- **Coach A** immediately loses API access to that client's data after the local database is updated.
- **Coach B** immediately gains API access to that client's data.
- The transition is atomic within the sync transaction.

---

## 7. Schema Change Detection

The system includes a three-layer approach to detecting and handling Salesforce schema changes, managed through the `salesforce_connector` and `admin_management` apps.

### Detection Layers

```
+-------------------------------------------+
| Layer 1: describe() Baseline Comparison   |
|   - Cached in .sf_schema_cache.json       |
|   - Compares field types, constraints     |
|   - Runs automatically at sync start      |
+-------------------------------------------+
              |
              v
+-------------------------------------------+
| Layer 2: SetupAuditTrail Query            |
|   - Queries SF audit logs for metadata    |
|     changes                               |
+-------------------------------------------+
              |
              v
+-------------------------------------------+
| Layer 3: Webhook from SF Apex Trigger     |
|   - Real-time push notification           |
|   - POST to /api/sf-connector/schema-webhook/ |
+-------------------------------------------+
```

### Type-Safe Data Ingestion

To handle fields that may arrive in unexpected types after a schema change, the sync engine uses safe coercion functions:

| Function       | Purpose                                    |
|----------------|--------------------------------------------|
| `_safe_str()`  | Coerce to string, default to empty string  |
| `_safe_int()`  | Coerce to integer, default to 0            |
| `_safe_bool()` | Coerce to boolean, default to False        |
| `_safe_date()` | Parse date string, default to None         |

### Auto-Migration Flow

1. Schema differences detected during sync pre-check.
2. Migration SQL generated for each difference.
3. SQL executed against the application database.
4. `SchemaMigrationLog` records the change with status (detected / migrated / failed / rolled_back).
5. Rollback SQL is stored for each migration, enabling reversal if needed.

---

## 8. API Endpoints

All endpoints are prefixed with `/api/` and return consistent JSON response structures.

### Authentication (`/api/auth/`)

| Method | Endpoint          | Description                        | Access  |
|--------|-------------------|------------------------------------|---------|
| POST   | `/api/auth/login/`  | Session login (username + password)| Public  |
| POST   | `/api/auth/logout/` | Session logout                     | Auth    |
| GET    | `/api/auth/csrf/`   | Retrieve CSRF token                | Public  |
| GET    | `/api/auth/me/`     | Current user profile and role      | Auth    |

### Coaching Data (`/api/coaching/`)

| Method | Endpoint                | Description                        | Access       |
|--------|-------------------------|------------------------------------|--------------|
| GET    | `/api/coaching/dashboard/` | Coach dashboard with stats      | Coach/Admin  |
| GET    | `/api/coaching/accounts/`  | List accounts (scoped)          | Coach/Admin  |
| GET    | `/api/coaching/contacts/`  | List contacts (scoped)          | Coach/Admin  |

### Sync Operations (`/api/sync/`)

| Method | Endpoint              | Description                        | Access     |
|--------|-----------------------|------------------------------------|------------|
| POST   | `/api/sync/trigger/`  | Trigger a full sync                | Admin only |
| GET    | `/api/sync/history/`  | List past sync runs                | Admin only |
| GET    | `/api/sync/audit/`    | Audit trail (all records)          | Admin only |

### Transition Briefs (`/api/briefs/`)

| Method | Endpoint              | Description                        | Access       |
|--------|-----------------------|------------------------------------|--------------|
| GET    | `/api/briefs/`        | List transition briefs (scoped)    | Coach/Admin  |
| GET    | `/api/briefs/<id>/`   | Brief detail                       | Coach/Admin  |

### Salesforce Source Management (`/api/salesforce/`)

| Method | Endpoint                    | Description                            | Access     |
|--------|-----------------------------|----------------------------------------|------------|
| GET    | `/api/salesforce/coaches/`  | List SF coaches                        | Admin only |
| POST   | `/api/salesforce/coaches/`  | Create SF coach                        | Admin only |
| PUT    | `/api/salesforce/coaches/<id>/` | Update SF coach                    | Admin only |
| DELETE | `/api/salesforce/coaches/<id>/` | Delete SF coach                    | Admin only |
| GET    | `/api/salesforce/accounts/` | List SF accounts                       | Admin only |
| POST   | `/api/salesforce/accounts/` | Create SF account                      | Admin only |
| PUT    | `/api/salesforce/accounts/<id>/` | Update SF account                 | Admin only |
| DELETE | `/api/salesforce/accounts/<id>/` | Delete SF account                 | Admin only |
| GET    | `/api/salesforce/contacts/` | List SF contacts                       | Admin only |
| POST   | `/api/salesforce/contacts/` | Create SF contact                      | Admin only |
| PUT    | `/api/salesforce/contacts/<id>/` | Update SF contact                 | Admin only |
| DELETE | `/api/salesforce/contacts/<id>/` | Delete SF contact                 | Admin only |

### Salesforce Connector (`/api/sf-connector/`)

| Method | Endpoint                             | Description                       | Access     |
|--------|--------------------------------------|-----------------------------------|------------|
| GET    | `/api/sf-connector/status/`          | Connection and sync status        | Admin only |
| POST   | `/api/sf-connector/pull-and-sync/`   | Pull from SF and sync             | Admin only |
| GET    | `/api/sf-connector/schema-check/`    | Check for schema changes          | Admin only |
| POST   | `/api/sf-connector/schema-webhook/`  | Receive SF schema change webhook  | Public*    |

*Webhook endpoint accepts unauthenticated POST requests from Salesforce.

### Admin Management (`/api/admin-mgmt/`)

| Method | Endpoint                          | Description                        | Access     |
|--------|-----------------------------------|------------------------------------|------------|
| GET    | `/api/admin-mgmt/coaches/`        | List coaches (admin view)          | Admin only |
| POST   | `/api/admin-mgmt/coaches/`        | Create coach in SF source          | Admin only |
| PUT    | `/api/admin-mgmt/coaches/<id>/`   | Update coach in SF source          | Admin only |
| DELETE | `/api/admin-mgmt/coaches/<id>/`   | Delete coach from SF source        | Admin only |
| GET    | `/api/admin-mgmt/accounts/`       | List accounts (admin view)         | Admin only |
| POST   | `/api/admin-mgmt/accounts/`       | Create account in SF source        | Admin only |
| PUT    | `/api/admin-mgmt/accounts/<id>/`  | Update account in SF source        | Admin only |
| DELETE | `/api/admin-mgmt/accounts/<id>/`  | Delete account from SF source      | Admin only |
| GET    | `/api/admin-mgmt/contacts/`       | List contacts (admin view)         | Admin only |
| POST   | `/api/admin-mgmt/contacts/`       | Create contact in SF source        | Admin only |
| PUT    | `/api/admin-mgmt/contacts/<id>/`  | Update contact in SF source        | Admin only |
| DELETE | `/api/admin-mgmt/contacts/<id>/`  | Delete contact from SF source      | Admin only |
| POST   | `/api/admin-mgmt/bulk-ops/`       | Execute bulk operations            | Admin only |
| GET    | `/api/admin-mgmt/schema/`         | View schema migration history      | Admin only |

---

## 9. Frontend Architecture

### Build and Tooling

The frontend is a single-page application built with React 18.3, TypeScript, and Vite 5.4. CSS Modules provide scoped styling using the PentEdge CRM design system (`--pm-*` CSS custom properties).

### Routing and Code Splitting

React Router handles navigation. Pages are lazily loaded to minimize initial bundle size.

```
App.tsx
  |
  +-- <AuthProvider>
  |     +-- <SyncProvider>
  |     |     +-- <ThemeProvider>
  |     |           +-- <Router>
  |     |                 |
  |     |                 +-- /login           -> LoginPage
  |     |                 +-- /dashboard       -> CoachDashboard     [ProtectedRoute]
  |     |                 +-- /admin           -> AdminDashboard     [AdminRoute]
  |     |                 +-- /audit           -> AuditTrailPage     [AdminRoute]
  |     |                 +-- /briefs          -> TransitionBriefsPage [ProtectedRoute]
  |     |                 +-- /source-editor   -> SourceEditorPage   [AdminRoute]
  |     |                 +-- /admin-mgmt      -> AdminManagementPage [AdminRoute]
  |     |                 +-- /schema-changes  -> SchemaChangesPage  [AdminRoute]
```

### Route Guards

| Guard            | Behavior                                             |
|------------------|------------------------------------------------------|
| `ProtectedRoute` | Redirects to `/login` if not authenticated           |
| `AdminRoute`     | Redirects to `/dashboard` if authenticated but not admin |

### Context Providers

| Context        | Purpose                                                   |
|----------------|-----------------------------------------------------------|
| `AuthContext`  | Manages login/logout state, current user profile and role |
| `SyncContext`  | Tracks sync notification status, polling for out-of-sync  |
| `ThemeContext` | Manages light/dark theme toggle                           |

### Pages

| Page                   | Role        | Description                                              |
|------------------------|-------------|----------------------------------------------------------|
| `LoginPage`            | Public      | Username/password authentication form                    |
| `CoachDashboard`       | Coach       | Assigned accounts, contacts, stats, and briefs           |
| `AdminDashboard`       | Admin       | System-wide overview, sync controls, charts              |
| `AuditTrailPage`       | Admin       | Searchable, filterable audit record history               |
| `TransitionBriefsPage` | Coach/Admin | AI-generated transition briefs (scoped per role)         |
| `SourceEditorPage`     | Admin       | Direct CRUD on simulated Salesforce data                 |
| `AdminManagementPage`  | Admin       | Coach/account/contact management with bulk operations    |
| `SchemaChangesPage`    | Admin       | Schema migration history and rollback controls           |

### Design System

The PentEdge CRM design system uses CSS custom properties prefixed with `--pm-` for consistent theming across all components. CSS Modules ensure style isolation per component. The system supports both light and dark themes via the `ThemeContext`.

---

## 10. Design Decisions & Trade-offs

### SQLite as the Database Engine

**Decision:** Use SQLite for both the application and simulated Salesforce databases.

**Rationale:** This is an evaluation project; SQLite eliminates infrastructure dependencies and allows the entire system to run with zero configuration. The two-database architecture (enforced by Django's database router) proves the separation-of-concerns design regardless of the database engine.

**Production alternative:** PostgreSQL with connection pooling. The Django ORM abstraction means switching engines requires only a settings change, not code changes.

### Session Authentication

**Decision:** Use Django's built-in session authentication rather than JWT.

**Rationale:** Session auth is simpler to implement, debug, and secure for a server-rendered or same-origin SPA. CSRF protection comes for free. There is no need for token refresh logic or token storage on the client.

**Production alternative:** JWT with short-lived access tokens and refresh tokens, appropriate for distributed deployments or mobile clients.

### Polling + Webhook for Sync Notifications

**Decision:** The frontend polls for sync notification status as a safety net, while also accepting webhook pushes from Salesforce for real-time awareness.

**Rationale:** Webhooks provide immediacy but are unreliable (network failures, SF outages). Polling ensures the system eventually detects changes even if the webhook is missed. The `SyncNotification` singleton model tracks the current state.

**Production alternative:** WebSocket connections for real-time push to the frontend, backed by Redis pub/sub.

### Synchronous Sync Execution

**Decision:** The sync runs synchronously within the Django request-response cycle.

**Rationale:** With the test dataset size (5 coaches, 10 accounts, 20 clients), sync completes in under a second. Asynchronous execution would add complexity without benefit at this scale.

**Production alternative:** Celery task queue with Redis broker. The sync endpoint would return a task ID, and the frontend would poll or subscribe to task status updates.

### Database Router for Cross-Database Isolation

**Decision:** Use Django's `DATABASE_ROUTERS` setting with a custom `SalesforceRouter` class to enforce complete separation between the two databases.

**Rationale:** The PRD mandates that the simulated Salesforce source and the application database must never share tables, schemas, or connections. The router makes this constraint impossible to violate accidentally -- any model in the `salesforce_sim` app is automatically directed to the `salesforce` database alias.

### Immutable Audit Records via PROTECT

**Decision:** `AuditRecord.sync` uses `on_delete=models.PROTECT`, preventing deletion of a `SyncLog` that has associated audit records.

**Rationale:** The audit trail must be immutable. Rather than relying solely on application-level restrictions (which can be bypassed via the Django admin or shell), the `PROTECT` cascade rule makes deletion a database-level error.

### AI Brief Failures as Non-Fatal

**Decision:** If the Google Gemini API call fails during transition brief generation, the error is logged and the sync completes successfully.

**Rationale:** The PRD explicitly requires that AI failures must not break the sync. Transition briefs are supplementary -- the core sync, change detection, and audit trail functions must never be compromised by an external AI service outage.

### Full-Dataset Pull (No Incremental Sync)

**Decision:** Every sync pulls the complete dataset from the Salesforce source and diffs it against the complete local dataset.

**Rationale:** This mirrors the real-world constraint described in the PRD -- Salesforce provides no change events. The system must be designed to work correctly even when the only available operation is "give me everything." At the test data scale, this is perfectly efficient.

**Production consideration:** For larger datasets, the diff algorithm's time complexity is O(N) per entity type (single pass through hash maps keyed by `sf_id`), which scales well even to thousands of records.

---

*This document reflects the system as implemented. It should be updated when significant architectural changes are made.*
