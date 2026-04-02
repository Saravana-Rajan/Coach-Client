# Coach Reassignment Detection & Handling — Product Requirements

Build a system that detects when coaching assignments change and keeps everything in sync: access control, audit history, and onboarding context for new coaches.

---

## Table of Contents

-   [Coach Reassignment Detection & Handling — Product Requirements](#coach-reassignment-detection--handling--product-requirements)
    -   [Table of Contents](#table-of-contents)
    -   [1. Introduction & Project Overview](#1-introduction--project-overview)
        -   [Problem](#problem)
        -   [What You Are Building](#what-you-are-building)
        -   [Learning Goals](#learning-goals)
    -   [2. Source System — What Data Exists](#2-source-system--what-data-exists)
        -   [Coaches](#coaches)
        -     
            
        -   [  
            ](#accounts)
        -   [Contacts (Clients)](#contacts-clients)
        -   [Coach-Client Assignments](#coach-client-assignments)
        -   [The Core Constraint](#the-core-constraint)
        -   [Simulated Source](#simulated-source)
    -   [3. User Roles & What They Need](#3-user-roles--what-they-need)
        -   [Coach](#coach)
        -   [Admin](#admin)
    -   [4. Phase 1: Data Sync](#4-phase-1-data-sync)
        -   [Requirements](#requirements)
        -   [Acceptance Criteria](#acceptance-criteria)
    -   [5. Phase 2: Change Detection & Audit Trail](#5-phase-2-change-detection--audit-trail)
        -   [Requirements](#requirements-1)
        -   [Acceptance Criteria](#acceptance-criteria-1)
    -   [6. Phase 3: Access Control & Dashboard](#6-phase-3-access-control--dashboard)
        -   [Requirements](#requirements-2)
        -   [Acceptance Criteria](#acceptance-criteria-2)
    -   [7. Phase 4: AI Transition Briefs](#7-phase-4-ai-transition-briefs)
        -   [Requirements](#requirements-3)
        -   [Acceptance Criteria](#acceptance-criteria-3)
    -   [8. Phase 5: Edge Case Testing](#8-phase-5-edge-case-testing)
        -   [What to Document](#what-to-document)
    -   [9. Non-Functional Requirements](#9-non-functional-requirements)
        -   [Stack](#stack)
        -   [Two Separate Data Stores](#two-separate-data-stores)
        -   [API Consistency](#api-consistency)
        -   [Error Handling](#error-handling)
        -   [Security](#security)
    -   [10. Deliverables](#10-deliverables)
    -   [11. Evaluation Rubric](#11-evaluation-rubric)
        -   [What We Evaluate](#what-we-evaluate)
        -   [What We Value Most](#what-we-value-most)
    -   [12. FAQ](#12-faq)

---

## 1. Introduction & Project Overview

### Problem

In coaching organizations, a coach is assigned to one or more accounts (companies), each of which has one or more clients (people at those companies). The source of truth for who is assigned to whom lives in Salesforce.

When assignments change in Salesforce — a client gets a new coach, an account is transferred, a coach leaves the organization — the downstream application needs to detect those changes, enforce the new access rules, keep a permanent record of what happened, and help the new coach get up to speed.

The challenge: there is no notification from Salesforce when something changes. You get the full dataset every time, and you need to figure out what's different.

### What You Are Building

A standalone application that:

1.  Pulls data from a simulated Salesforce source and keeps a local copy in sync.
2.  Detects every kind of assignment change that occurred since the last sync.
3.  Records those changes permanently in an audit trail.
4.  Enforces access control so coaches only see their own clients and accounts.
5.  Generates AI-powered briefing documents to onboard new coaches onto their newly assigned clients.
6.  Provides a dashboard for coaches and administrators.

### Learning Goals

-   Working with external data sources where you control the sync, not the source.
-   Detecting changes without change events.
-   Building access control that adapts dynamically as relationships change.
-   Integrating AI to generate actionable context from real data.
-   Handling edge cases that break simple assumptions.

---

## 2. Source System — What Data Exists

The client uses Salesforce as their CRM. Below is a description of what data lives there and how it relates. Think of this as the briefing a product owner would give you about the source system.

### Coaches

Salesforce tracks every coach in the organization. For each coach, it stores their name, email address, how many active clients they currently have, and whether they are still active.

### Accounts

An account is a company being coached. Each account has a name, the industry it operates in, a website, the date the coaching relationship started, and which coach is currently assigned to that account.

### Contacts (Clients)

A contact is an individual person at an account who receives coaching. Each contact has a name, job title, phone, email, which account (company) they belong to, and which coach is assigned to them.

### Coach-Client Assignments

Salesforce also maintains a record of which coach is working with which client at which account, along with a status for that relationship.

### The Core Constraint

**The only way to get data from Salesforce is to pull the entire dataset.** There are no change notifications, no event streams, no webhooks. Every time you sync, you get everything. Every coach, every account, every client, every assignment — the full picture. You must compare what you had before with what you have now to determine what changed.

### Simulated Source

You will not connect to a real Salesforce instance. Instead, you will build a separate data store that acts as the simulated Salesforce. This source must be:

-   **Populated with test data** (see [Phase 5](#8-phase-5-edge-case-testing) for the test dataset).
-   **Editable** — you need to change the source data to simulate real-world Salesforce mutations.
-   **Completely separate** from your application's own data store. Your application reads from it but never writes to it.

---

## 3. User Roles & What They Need

### Coach

A coach logs in and sees only the accounts and clients assigned to them. They should never see another coach's data.

What a coach needs:

-   A list of their assigned accounts, with the clients under each account.
-   Basic metrics: how many accounts they have, how many clients.
-   When they are newly assigned a client or account, a transition brief that gives them context about what they are inheriting.

### Admin

An admin has full visibility and control.

What an admin needs:

-   Everything a coach sees, but across all coaches — not scoped to one person.
-   A complete audit history of every assignment change the system has detected.
-   The ability to trigger a sync from the source system.
-   The ability to view sync history (when syncs ran, what was found).
-   A way to modify the simulated Salesforce data to test different scenarios (this can be a separate tool or built into the admin interface).

---

## 4. Phase 1: Data Sync

**Goal:** Pull the full dataset from the simulated Salesforce source and mirror it in your application's database.

### Requirements

-   The application fetches the complete dataset from the simulated source: all coaches, all accounts, all clients, and all assignments.
-   The application's local data reflects the source accurately after every sync.
-   Records that exist in the source are created or updated locally. Records that no longer exist in the source are removed locally.
-   The sync can be triggered manually by an admin.
-   When the source data is modified, the system must be notified that it should sync. However, the notification must only say "something changed" — it must not say what changed. Your application must figure out the specifics on its own.

### Acceptance Criteria

-    An admin can trigger a sync and the application's data matches the source afterward.
-    New records in the source appear in the application after sync.
-    Records removed from the source are removed from the application after sync.
-    Updated records in the source are updated in the application after sync.
-    The sync mechanism does not receive any information about what specifically changed — only that a sync is needed.
-    The simulated source and the application store data separately; the application never writes to the source.

---

## 5. Phase 2: Change Detection & Audit Trail

**Goal:** After every sync, determine exactly what changed and record it permanently.

### Requirements

**Change Detection**

The system must detect any change to coaching assignments that occurs in Salesforce. This includes changes to who is assigned to whom, people or accounts entering or leaving the system, and structural reorganizations.

For example: if a client gets a new coach, the system must detect that. If a coach leaves the organization, the system must detect that too. These are just examples — think through what other kinds of changes are possible given the data model described in [Section 2](#2-source-system--what-data-exists), and make sure your system catches them all.

**Audit Trail**

-   Every detected change must be recorded permanently. Audit records are never modified or deleted.
-   Each audit record must capture enough information to understand what happened: what changed, what the state was before, what the state is after, and when the change was detected.
-   Audit records from the same sync should be grouped together so you can see everything that happened in a single sync run.
-   The audit trail must be queryable — an admin should be able to filter by type of change, by coach, by account, by date range, etc.
-   Running a sync when nothing has changed in the source must not produce any audit records.

### Acceptance Criteria

-    After a sync where assignments changed, the audit trail accurately reflects what happened — including the before and after state.
-    All audit records from a single sync are grouped together.
-    An admin can filter the audit trail by type of change, coach, and date range.
-    Running a sync twice with no source changes produces zero new audit records the second time.
-    Audit records are immutable — the system does not allow editing or deleting them.

---

## 6. Phase 3: Access Control & Dashboard

**Goal:** Coaches can only see their own data, and both coaches and admins have appropriate dashboards.

### Requirements

**Access Control**

-   A coach can only see accounts and clients that are currently assigned to them.
-   When a client is reassigned from Coach A to Coach B, Coach A must immediately lose access to that client's data, and Coach B must gain access.
-   This must be enforced at the data level, not just the user interface. If a coach directly queries the API, they still cannot access data that is not assigned to them.
-   An admin can see all data across all coaches.

**Coach Dashboard**

-   Shows the coach's assigned accounts.
-   Under each account, shows the assigned clients with their details.
-   Shows basic metrics: total accounts, total clients.
-   Shows any transition briefs for recently received assignments.

**Admin Dashboard**

-   Shows data across all coaches (not scoped).
-   Includes the audit trail viewer with filtering.
-   Includes sync controls: trigger sync, view sync history.

### Acceptance Criteria

-    Coach A has an account with a client. After the client is reassigned to Coach B and a sync runs, Coach A can no longer see that client or account through the dashboard or API.
-    After the same reassignment, Coach B can see the client and account.
-    A coach who directly calls the API (bypassing the UI) still cannot access data they are not assigned to.
-    An admin can see all coaches' data, trigger a sync, and view the audit trail.
-    The coach dashboard shows accounts, clients, and metrics scoped to the logged-in coach.
-    The admin dashboard shows sync history with the number of changes detected per sync.

---

## 7. Phase 4: AI Transition Briefs

**Goal:** When a client is reassigned to a new coach, automatically generate a briefing document that gives the new coach context about what they are inheriting.

### Requirements

**Content**

A transition brief should help the incoming coach get up to speed quickly. It should include:

-   Who the client is and what account they belong to.
-   Who the previous coach was.
-   Relevant details about the account (industry, how long the relationship has been active, etc.).
-   A summary of the client's background (title, contact info).
-   AI-generated insights: a synthesis of available data into actionable context for the new coach, and recommended next steps.

**Generation**

-   A transition brief is generated automatically when a reassignment is detected during sync.
-   The AI must use real data from your database — not made-up information.
-   Use any LLM API (OpenAI, Anthropic, Google, Ollama, etc.).
-   If the AI call fails, log the error but do not fail the entire sync. The brief can be missing; the sync and audit trail must still complete.

**Storage & Access**

-   Transition briefs are stored permanently and linked to the change that triggered them.
-   Coaches can view their transition briefs from the dashboard.
-   Admins can view all transition briefs.

### Acceptance Criteria

-    When a client is reassigned to a new coach and a sync runs, a transition brief is automatically generated for the new coach.
-    The transition brief contains real data from the database (account name, client name, previous coach, etc.).
-    The transition brief includes AI-generated insights and recommended next steps.
-    The new coach can view the transition brief from their dashboard.
-    If the AI call fails, the sync still completes successfully and the failure is logged.
-    An admin can view all transition briefs across all coaches.

---

## 8. Phase 5: Edge Case Testing

**Goal:** Validate that the system handles real-world scenarios correctly.

During evaluation, we will test your system against approximately 15 real-world scenarios by modifying the simulated Salesforce data and running a sync. Your system needs to handle each one correctly.

Here are a few examples of the kind of scenarios we will test:

-   An account currently assigned to one coach is reassigned to a different coach.
-   A coach leaves the organization and their clients are redistributed across other coaches.
-   Multiple coaches swap accounts simultaneously in a single Salesforce update.

These are just examples. You should think through what other scenarios are possible — considering the entities and relationships described in [Section 2](#2-source-system--what-data-exists) — and ensure your system handles them correctly. The more scenarios you anticipate and handle, the better.

### What to Document

For each scenario we test during evaluation, your test report must include:

1.  **What you changed** in the simulated Salesforce source.
2.  **What you expected** the system to do (in your own words).
3.  **What actually happened** — the system's behavior.
4.  **Pass or fail** — did the system behave correctly?
5.  **Evidence** — screenshots, log output, or audit trail entries that prove the result.

NOTE:**We also encourage you to document any additional scenarios you tested yourself.**

If a scenario breaks your system, document it honestly. Explain what went wrong and propose how you would fix it. This is worth more than hiding the failure.

---

## 9. Non-Functional Requirements

### Stack

You choose your own tech stack. Backend framework, frontend framework, database, LLM provider — all your decision. Use whatever you are most productive with.

### Two Separate Data Stores

The simulated Salesforce source and your application's database must be separate. They should not share tables, schemas, or connections.

### API Consistency

All API responses should follow a consistent structure. Define a standard response format and use it everywhere.

### Error Handling

-   Sync failures should be logged and visible to admins.
-   AI failures should not break the sync process.
-   The admin should be able to see the status of any sync (in progress, completed, failed).

### Security

-   Access control is enforced at the API level, not just the UI.
-   Coaches cannot access other coaches' data under any circumstances.

---

## 10. Deliverables

#

Deliverable

Format

Description

1

**Source Code**

Git repository

Complete, runnable full-stack application.

2

**README**

Markdown

Setup instructions, architecture overview, tech stack choices and rationale.

3

**Seed Data Script**

Script or migration

Populates the simulated Salesforce source with the test dataset.

4

**Mutation Tools**

Script(s) or UI

Tool(s) to modify the simulated Salesforce source for each test scenario.

5

**Edge Case Test Report**

Markdown

For each scenario tested: what changed, expected behavior, actual behavior, pass/fail, evidence. Include both the scenarios we provide during evaluation and any additional scenarios you tested yourself.

6

**Architecture Document**

Markdown or diagram

Data model, sync flow, component overview.

---

## 11. Evaluation Rubric

### What We Evaluate

Criteria

What We Are Looking For

**Change detection accuracy**

Does the system correctly detect all types of assignment changes? Are there false positives or missed changes?

**Audit trail completeness**

Is every change recorded? Can we trace back exactly what happened during any sync?

**Access control correctness**

Can a coach only see their own data? After a reassignment, does the old coach immediately lose access?

**AI brief quality**

Are the transition briefs useful? Do they contain real data and actionable insights?

**Edge case handling**

How well does the system handle the range of real-world scenarios we test? Are failures documented honestly with proposed fixes?

**Architecture & design**

Are the technical decisions well-reasoned? Is the system organized in a way that is easy to understand and extend?

**Code quality**

Is the code clean, well-structured, and maintainable?

**Documentation**

Does the README explain how to set up and run the project? Does the architecture doc explain the design decisions?

### What We Value Most

1.  **Anticipating and handling real-world scenarios.** We value candidates who think through what can go wrong — not just handle the cases we give them. If an edge case breaks your system, document it. Explain why. Propose a fix. This is worth more than hiding the failure.
2.  **Understanding the core problem.** Your README should demonstrate that you understand the challenge of working with a full-dataset sync and why change detection is hard.
3.  **Correct access control.** If the old coach can still see reassigned data, that is a critical failure regardless of everything else.

---

## 12. FAQ

**Q: What if one of the evaluation scenarios breaks my system?**A: Document it honestly. Write down what happened, why you think it broke, and how you would fix it given more time. An honest failure with a thoughtful analysis is valued more than a hidden bug.

**Q: Can I use any tech stack?**A: Yes. Backend, frontend, database, LLM provider — all your choice. Use what you are most productive with.

**Q: Do I need to connect to a real Salesforce instance?**A: No. You build a simulated source that acts as Salesforce. The key requirement is that it is a separate data store from your application.

**Q: How should the simulated Salesforce notify the app that data changed?**A: The notification must only convey "something changed, you should sync." It must never convey what specifically changed. How you implement that notification mechanism is up to you.

**Q: How realistic do the AI-generated briefs need to be?**A: They need to use real data from your database and produce something a coach would actually find useful. The quality of the AI output matters, but the integration (passing real data, handling failures gracefully, storing the result) matters more.

**Q: What does the test dataset look like?**A: The client has provided this distribution for testing:

-   **5 coaches:** Alice, Bob, Carol, Dave, and Eve.
-   **10 accounts:** Distributed unevenly across coaches (some coaches have more than others). Realistic company names across industries like Technology, Healthcare, Finance, and Manufacturing.
-   **20 clients:** 2-3 clients per account, with realistic names, titles (CEO, VP Engineering, Director of HR, etc.), and contact details.
-   **Initial assignments:** Alice has 4 accounts and 8 clients. Bob has 3 accounts and 6 clients. Carol has 2 accounts and 4 clients. Dave has 1 account and 2 clients. Eve has no accounts — she is a newly added coach who will be used for reassignment testing.

You must create a seed script that populates the simulated Salesforce source with this data.