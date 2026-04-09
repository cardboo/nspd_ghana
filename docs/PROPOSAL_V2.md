# NSPD Ghana v2 — System Enhancement Proposal

**Prepared for:** Ghana Maritime Authority
**Prepared by:** NSPD Ghana Development Team
**Date:** April 2026
**Document Version:** 1.0

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Current System Overview](#2-current-system-overview)
3. [Identified Gaps & Limitations](#3-identified-gaps--limitations)
4. [Proposed Enhancements](#4-proposed-enhancements)
   - Phase 1: Core Platform Capabilities
   - Phase 2: Data Model & Compliance
   - Phase 3: Operational Efficiency
   - Phase 4: Polish & Extended Features
5. [Proposed Database Architecture](#5-proposed-database-architecture)
6. [Implementation Phases & Timeline](#6-implementation-phases--timeline)
7. [Summary of Deliverables](#7-summary-of-deliverables)

---

## 1. Executive Summary

The National Seafarer Placement Database (NSPD) Ghana system currently operates as an **internal, read-only administrative dashboard** for reviewing seafarer training applications. While the existing platform provides valuable data visualization and export capabilities, it lacks critical operational features required for a complete seafarer registration and compliance management workflow.

This proposal outlines a comprehensive upgrade path for **NSPD Ghana Version 2**, transforming the system from a passive data viewer into a **full-lifecycle seafarer registration, review, and compliance management platform**.

The proposed enhancements are organized into four implementation phases, each delivering independently valuable functionality while building toward the complete system vision.

---

## 2. Current System Overview

### 2.1 What the System Does Today

| Feature                  | Status      | Description                                                |
|--------------------------|-------------|------------------------------------------------------------|
| User Authentication      | Complete    | Secure login with session management and CSRF protection   |
| Dashboard                | Complete    | Summary metrics (total submissions, average experience, recent activity) |
| Submissions Browser      | Complete    | Paginated, searchable list with rank filtering             |
| Submission Detail View   | Complete    | Full record display for individual applications            |
| Analytics & Reports      | Complete    | Five interactive charts with server-side filtering         |
| PDF Export               | Complete    | Individual submission reports (Reviewer+ access)           |
| CSV Export               | Complete    | Bulk data export with active filters (Reviewer+ access)    |
| Role-Based Access        | Complete    | Three-tier permission model (Administrator, Reviewer, Viewer) |

### 2.2 Technology Stack

| Component   | Technology                              |
|-------------|-----------------------------------------|
| Backend     | PHP 8.1+                                |
| Database    | MySQL 8.0 (InnoDB)                      |
| Frontend    | HTML5, CSS3, Vanilla JavaScript         |
| Charts      | Chart.js 4.x                            |
| PDF Engine  | TCPDF                                   |

### 2.3 Current Data

The system currently holds **574 seafarer application records** imported from a legacy data source, with fields covering personal information, maritime rank, certification status, sea experience, and medical fitness.

---

## 3. Identified Gaps & Limitations

Through a comprehensive code and functionality audit, the following critical gaps have been identified:

### 3.1 No Public-Facing Application Intake

The system has **no mechanism for seafarers to submit new applications**. All existing records were imported from an external source. This means:

- New applicants cannot register through the platform
- Data entry is entirely manual or dependent on external systems
- There is no self-service capability for the seafaring community

### 3.2 No Application Processing Workflow

While the database schema includes `status`, `reviewed_by`, and `reviewed_at` columns, **no user interface exists** to manage the application lifecycle. Applications cannot be approved, rejected, or moved through a review pipeline.

### 3.3 No User Administration Interface

User accounts can only be created via direct database access (SQL scripts). There is no interface for administrators to:

- Create, edit, or deactivate user accounts
- Assign or change roles
- Reset passwords

### 3.4 Limited Data Model

The current data model stores certification and medical status as simple Yes/No flags rather than tracking actual documents, dates, and expiry information. This limits the system's ability to:

- Monitor compliance in real time
- Alert on expiring certifications or medicals
- Maintain an auditable record of seafarer qualifications

### 3.5 No Document Management

Physical documents (certificates, medical reports, identification) are not captured or stored by the system. The `attachment` field records only whether an attachment exists — not the attachment itself.

### 3.6 No Audit Trail

There is no logging of system activity. It is not possible to determine who accessed which records, when exports were performed, or who made status changes.

---

## 4. Proposed Enhancements

### Phase 1 — Core Platform Capabilities

These features address the most critical gaps and transform the system from a passive viewer into an active operational tool.

#### 4.1.1 Public Seafarer Registration Form

**Objective:** Allow seafarers to submit applications directly through the platform without requiring a login.

**Scope:**

- Multi-step guided form accessible at a public URL (e.g., `/register.php`)
  - **Step 1:** Personal Information (name, date of birth, contact, nationality, ID number)
  - **Step 2:** Qualifications & Certifications (rank, RMU courses, ISPS/GMA, other certifications)
  - **Step 3:** Sea Experience (voyage history, total experience, last vessel type)
  - **Step 4:** Medical Fitness (status, examining clinic, expiry date)
  - **Step 5:** Document Uploads (certificates, medical reports, ID scan, passport photo)
  - **Step 6:** Review & Submit (summary of all entered data with edit capability)
- Server-side validation with clear, field-level error messages
- Confirmation page with a unique reference number upon successful submission
- Duplicate detection — alert if email or phone number already exists in the system
- Anti-spam protection (honeypot field and rate limiting)

**Business Value:** Eliminates manual data entry, enables self-service registration, and creates a single point of entry for all seafarer applications.

---

#### 4.1.2 Application Review & Approval Workflow

**Objective:** Enable reviewers and administrators to process applications through a structured lifecycle.

**Scope:**

- Application statuses: **Pending** → **Under Review** → **Approved** / **Rejected**
- Status badges displayed throughout the submissions list and detail views
- Status filter added to the submissions page
- Approve/Reject action buttons on the submission detail page (Reviewer+ access)
- Mandatory reviewer notes when rejecting an application
- Optional internal notes on any application (visible to staff only)
- Reviewer assignment — administrators can assign applications to specific reviewers
- Dashboard updates:
  - New card: "Pending Review" count
  - New card: "Approved Today" count
  - Status breakdown chart (donut) on reports page

**Business Value:** Establishes a structured, auditable review process. Ensures no applications are overlooked and provides clear accountability for decisions.

---

#### 4.1.3 User Management Interface

**Objective:** Allow administrators to manage system users without direct database access.

**Scope:**

- New admin-only page: `/users.php`
- View all users in a table (username, full name, role, email, last login, status)
- Add new user form (with password strength requirements)
- Edit user details and role assignment
- Activate/deactivate user accounts (soft delete — never hard delete)
- Password reset capability (admin-initiated)
- Change own password (all users, from header profile menu)

**Business Value:** Enables operational independence from the development team for routine user administration tasks.

---

#### 4.1.4 Document Upload & Storage

**Objective:** Capture and store actual documents alongside application records.

**Scope:**

- Secure file upload on the registration form and editable from the admin detail view
- Supported document types:
  - Certificates of Competency (CoC)
  - STCW certificates
  - Medical fitness certificates
  - Passport / Ghana Card scan
  - Passport-size photograph
  - Other supporting documents
- File validation: PDF, JPG, PNG only; maximum 5 MB per file
- Secure storage in a non-public directory with randomized filenames
- View and download documents from the submission detail page
- Document status indicators (uploaded/missing) on the submissions list

**Business Value:** Creates a centralized, digital document repository. Eliminates the need for separate physical filing systems and enables remote document verification.

---

### Phase 2 — Data Model & Compliance Enhancements

These features expand the data model to support real-world maritime compliance requirements.

#### 4.2.1 Enhanced Seafarer Profile

**Objective:** Capture comprehensive biographical and identification data.

**Additional fields:**

| Field                   | Type        | Purpose                              |
|-------------------------|-------------|--------------------------------------|
| Date of Birth           | Date        | Age verification, eligibility        |
| Gender                  | Enum        | Demographic reporting                |
| Nationality             | Varchar     | Regulatory compliance                |
| Ghana Card / Passport # | Varchar     | Unique identification                |
| Region / City           | Varchar     | Geographic distribution analysis     |
| Residential Address     | Text        | Contact and correspondence           |
| Emergency Contact Name  | Varchar     | Safety requirement                   |
| Emergency Contact Phone | Varchar     | Safety requirement                   |
| Passport Photo          | File ref    | Visual identification                |

**Business Value:** Aligns the database with IMO and GMA regulatory data requirements for seafarer registries.

---

#### 4.2.2 Detailed Certification Tracking

**Objective:** Move from Yes/No flags to full certification lifecycle management.

**Scope:**

- New `certifications` table tracking per-seafarer, per-certificate:
  - Certificate name and type (STCW, CoC, CoP, Short Course, etc.)
  - Issuing authority
  - Certificate number
  - Date of issue
  - Date of expiry
  - Uploaded certificate document (linked to document storage)
- Certification status engine:
  - **Valid** — current and not expired
  - **Expiring Soon** — within 90 days of expiry
  - **Expired** — past expiry date
- Dashboard alert widget: "Certificates Expiring in 30/60/90 Days"
- Reports page: new Certification Compliance chart
- CSV/PDF exports updated to include certification details

**Business Value:** Enables proactive compliance monitoring. Prevents seafarers from shipping with expired certifications. Provides GMA with real-time visibility into fleet certification status.

---

#### 4.2.3 Voyage & Employment History

**Objective:** Track individual voyage records to build a verifiable sea service history.

**Scope:**

- New `voyage_history` table:
  - Vessel name and IMO number
  - Ship type
  - Shipping company
  - Rank held during voyage
  - Sign-on date and sign-off date
  - Port of engagement
- Auto-calculated total sea experience (sum of all voyage durations)
- Timeline view on the seafarer detail page
- Voyage history included in PDF export

**Business Value:** Provides verifiable sea service records. Supports CoC applications that require documented sea time. Enables analysis of workforce deployment patterns.

---

#### 4.2.4 Medical Records Management

**Objective:** Track medical fitness with dates, providers, and document references.

**Scope:**

- New `medical_records` table:
  - Examination date
  - Expiry date
  - Examining doctor / clinic
  - Result (Fit / Unfit / Fit with Restrictions)
  - Restrictions detail (if applicable)
  - Uploaded medical certificate
- Medical status automatically derived from most recent record
- Expired medical alerts on dashboard
- Medical compliance chart on reports page

**Business Value:** Ensures no seafarer is deployed without valid medical clearance. Creates an auditable medical fitness history.

---

### Phase 3 — Operational Efficiency Features

#### 4.3.1 Advanced Search & Filtering

- Global search bar in the header (searches across all fields)
- Advanced filter panel on submissions: status, date range (submitted between), ship type, experience range, medical status, certification status
- Sortable table columns (click header to sort)
- Saved filter presets (e.g., "Pending Engine Cadets", "Expiring Medicals")
- Configurable results per page (10 / 25 / 50 / 100)

#### 4.3.2 Activity & Audit Log

- New `activity_log` table recording all significant system events:
  - User logins and logouts
  - Application status changes (with before/after values)
  - Document uploads and downloads
  - Data exports (CSV, PDF)
  - User account changes
- Dedicated audit log page (Administrator only)
- Filterable by user, action type, and date range

#### 4.3.3 Email Notifications

- Confirmation email to seafarer upon successful application submission
- Notification to assigned reviewer when a new application is received
- Email to seafarer when application status changes (approved/rejected)
- Scheduled digest: weekly summary of pending applications to administrators
- Configurable SMTP settings via admin settings page

#### 4.3.4 Admin Settings Page

- Toggle application submissions open/closed
- Configure notification preferences
- SMTP email configuration
- System information display (PHP version, database size, record counts)
- Manage dropdown options (rank list, ship types) without code changes

---

### Phase 4 — Polish & Extended Features

#### 4.4.1 Print-Friendly Views & Reporting

- Print stylesheet for submission detail pages
- Batch PDF generation (export multiple submissions at once)
- Seafarer ID card template (photo + name + rank + registration number + QR code)
- Summary report PDF for filtered datasets (not just individual records)
- "Download chart as image" button on reports page

#### 4.4.2 Data Import Tools

- CSV import wizard for bulk data migration
- Field mapping interface (map CSV columns to database fields)
- Validation preview before import (show errors/warnings)
- Import history log

#### 4.4.3 Enhanced UX

- Dark mode toggle (preference saved per user)
- AJAX-powered submissions table (filter and paginate without full page reload)
- Breadcrumb navigation
- Keyboard shortcuts for common actions
- Session timeout warning with extend option

#### 4.4.4 Password & Account Management

- "Change Password" option for all logged-in users
- Forgot password flow with email-based reset token
- Account lockout after failed login attempts
- Password expiry policy (configurable)

---

## 5. Proposed Database Architecture

The following new tables and modifications support the features described above:

### New Tables

```
documents
├── id (PK)
├── application_id (FK → applications)
├── document_type (enum: certificate, medical, id_scan, photo, other)
├── original_filename
├── stored_filename
├── file_size
├── mime_type
├── uploaded_by (FK → users, nullable)
├── uploaded_at

certifications
├── id (PK)
├── application_id (FK → applications)
├── cert_type (enum: STCW, CoC, CoP, ShortCourse, Other)
├── cert_name
├── cert_number
├── issuing_authority
├── issue_date
├── expiry_date
├── document_id (FK → documents, nullable)
├── created_at

voyage_history
├── id (PK)
├── application_id (FK → applications)
├── vessel_name
├── imo_number
├── ship_type
├── company_name
├── rank_held
├── sign_on_date
├── sign_off_date
├── port_of_engagement
├── created_at

medical_records
├── id (PK)
├── application_id (FK → applications)
├── exam_date
├── expiry_date
├── examining_doctor
├── clinic_name
├── result (enum: Fit, Unfit, FitWithRestrictions)
├── restrictions_detail
├── document_id (FK → documents, nullable)
├── created_at

reviewer_notes
├── id (PK)
├── application_id (FK → applications)
├── user_id (FK → users)
├── note_text
├── created_at

activity_log
├── id (PK)
├── user_id (FK → users, nullable)
├── action (e.g., login, status_change, export, view)
├── target_type (e.g., application, user, document)
├── target_id
├── details (JSON)
├── ip_address
├── created_at

notifications
├── id (PK)
├── user_id (FK → users)
├── type (e.g., new_application, status_change, cert_expiry)
├── title
├── message
├── is_read (boolean)
├── link
├── created_at
```

### Modifications to Existing `applications` Table

```
Add columns:
├── date_of_birth (DATE)
├── gender (ENUM: Male, Female, Other)
├── nationality (VARCHAR)
├── id_number (VARCHAR — Ghana Card or Passport)
├── address (TEXT)
├── region (VARCHAR)
├── city (VARCHAR)
├── emergency_contact_name (VARCHAR)
├── emergency_contact_phone (VARCHAR)
├── photo_document_id (FK → documents)
├── reference_number (VARCHAR, UNIQUE — auto-generated on submission)
```

---

## 6. Implementation Phases & Timeline

| Phase   | Scope                                          | Estimated Duration |
|---------|-------------------------------------------------|--------------------|
| Phase 1 | Registration Form, Approval Workflow, User Management, Document Uploads | 4 - 6 weeks |
| Phase 2 | Enhanced Profile, Certification Tracking, Voyage History, Medical Records | 3 - 4 weeks |
| Phase 3 | Advanced Search, Audit Log, Email Notifications, Settings Page           | 3 - 4 weeks |
| Phase 4 | Print/Reports, Data Import, Dark Mode, Password Management              | 2 - 3 weeks |

**Total estimated duration: 12 - 17 weeks**

Each phase delivers independently functional capabilities and can be deployed upon completion. Phases can be adjusted in scope or priority based on institutional needs and feedback.

---

## 7. Summary of Deliverables

| #  | Deliverable                              | Phase | Priority  |
|----|------------------------------------------|-------|-----------|
| 1  | Public Seafarer Registration Form        | 1     | Critical  |
| 2  | Application Review & Approval Workflow   | 1     | Critical  |
| 3  | User Management Interface                | 1     | Critical  |
| 4  | Document Upload & Storage System         | 1     | Critical  |
| 5  | Enhanced Seafarer Profile Fields         | 2     | High      |
| 6  | Certification Lifecycle Tracking         | 2     | High      |
| 7  | Voyage & Employment History              | 2     | High      |
| 8  | Medical Records Management               | 2     | High      |
| 9  | Advanced Search & Filter System          | 3     | Medium    |
| 10 | Activity & Audit Logging                 | 3     | Medium    |
| 11 | Email Notification System                | 3     | Medium    |
| 12 | Admin Settings Page                      | 3     | Medium    |
| 13 | Enhanced Print & Batch Reporting         | 4     | Standard  |
| 14 | CSV Data Import Wizard                   | 4     | Standard  |
| 15 | UX Enhancements (Dark Mode, AJAX, etc.) | 4     | Standard  |
| 16 | Password & Account Management            | 4     | Standard  |

---

*This proposal is submitted for review and approval. Implementation will proceed upon confirmation of scope and phase prioritization.*

**NSPD Ghana Development Team**
**April 2026**
