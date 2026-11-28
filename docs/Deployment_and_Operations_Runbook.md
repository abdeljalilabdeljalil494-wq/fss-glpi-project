# Deployment & Operations Runbook — GLPI at FSS

## 1. Scope and assumptions
Centralized asset, software, network-device, laboratory-equipment, stock, and helpdesk management for Informatics/Computer Science, Physics, Chemistry, Biology, and faculty administration. This runbook does not assert that a server or database exists. Production values and choices require FSS IT approval.

**Recommended baseline:** supported GLPI release at time of installation; supported Linux LTS VM; MariaDB/MySQL version supported by that GLPI release; internal DNS and static private IP; HTTPS using FSS-managed certificate; access restricted to the faculty network/VPN. Pin exact versions after compatibility review; do not use floating `latest` in production.

## 2. Architecture
- Internal users → HTTPS reverse proxy → GLPI web application → private SQL database.
- GLPI Agent on managed PCs performs scheduled inventory; deploy only after endpoint/security approval.
- Network discovery/SNMP is restricted to approved management subnets and read-only SNMPv3 credentials where supported. Never store credentials in tickets or this package.
- Daily encrypted database and GLPI configuration backups to a separate protected location; monitor success and periodically test restores.
- No public exposure; firewall permits HTTPS from authorized faculty segments and database traffic only from the GLPI host.

## 3. Tenant and authorization design
Use GLPI entities (or equivalent supported isolation mechanism) as a faculty root with child scopes: Informatics, Physics, Chemistry, Biology, and central administration. Map each department's users to its scope and provide least-privilege profiles. Configure technician groups and assignment rules per department. Cross-department overview is limited to explicitly authorized faculty administrators. Validate visibility with test accounts before importing real data.

Suggested roles:
- Requester: create/read own tickets; reserve equipment if enabled.
- Department asset manager: manage assets and stock in own entity; no global admin.
- Technician: view/assign/resolve tickets in assigned scope; record work and parts.
- Storekeeper: receive, issue, adjust stock in authorized stores; audit trail retained.
- Faculty administrator: approved consolidated reporting and cross-entity oversight.
- GLPI technical administrator: platform configuration; restricted to named IT operators.

## 4. Data model and configuration
### Asset types
Computers, monitors, printers, switches, routers, UPS, microscopes, spectrometers, balances, incubators, and other approved equipment. Use built-in GLPI item types where suitable; use supported fields/plugins only after compatibility, maintenance, security, and upgrade review.

Required common fields: inventory number (unique), type/model, manufacturer, serial number, entity/department, building/room/lab, custodian, status, acquisition date, warranty end, supplier, and last verified date. Lab fields: measurement range/resolution, calibration due date, condition, accessories, and safety notes as appropriate. Do not record personal/sensitive data beyond operational need.

### Software
Enable agent-based software inventory on managed PCs. Track product/version, installation footprint, and license evidence where available. Reconcile discovery against procurement/license records; inventory is not itself proof of license compliance.

### Stock
Track item code, name, unit, store/shelf, lot/batch, expiry date where relevant, supplier, quantity, minimum threshold, and movements. Receive/issue/adjust transactions must record date, quantity, source/destination, reason, and authorized actor. For chemicals, follow FSS chemical safety/SDS and regulatory procedures; GLPI is not a substitute for hazardous-material compliance systems.

Threshold rule: alert when available quantity is below the approved minimum; define whether reservations/committed quantities reduce available stock. Assign alerts to the storekeeper and backup. Avoid duplicate alerts by setting a cooldown or daily digest.

### Tickets
Categories: Hardware, Software, Network, Lab Equipment, Account/Access, and Other. Require requester, department/entity, location, affected asset where known, impact, urgency, description, and contact method. Lifecycle: New → Assigned → In progress → Pending (with reason) → Resolved → Closed. Record diagnosis, actions, parts used, and resolution. Do not request passwords or secrets in tickets.

## 5. Reservation workflow
If the installed GLPI version/configuration supports reservation of the relevant asset type, enable it only for reservable assets. Define owner, booking duration, lead time, cancellation rules, maintenance blackout periods, and approval requirements. Users check availability before submitting; asset managers resolve conflicts. Test simultaneous booking behavior and permissions. If native reservation does not cover a lab device, use an approved scheduling plugin or documented departmental calendar; do not claim conflict prevention until tested.

## 6. Deployment sequence
### Preparation (before Week 1)
- Confirm business owner, service owner, IT operators, department coordinators, storekeeper, data owner, and escalation contacts.
- Approve VM sizing based on endpoint count, inventory frequency, attachment volume, and retention. Reserve static private IP and internal DNS.
- Confirm supported OS/DB/GLPI/plugin matrix, patching owner, TLS certificate, firewall paths, SMTP, time synchronization, and backup target.
- Approve data retention, privacy, access matrix, stock thresholds, inventory fields, and agent policy.

### Phase 1 — Pilot (Weeks 1–2)
- Install and harden GLPI on the internal VM. Configure HTTPS, database least privilege, mail notifications, and backups.
- Create entities, profiles, groups, categories, locations, and test accounts.
- Deploy agents to 5–10 test PCs across representative rooms; validate CPU/RAM/disk/OS/software data and duplicate handling.
- Run ticket, stock movement, authorization-isolation, backup/restore, and update tests. Do not proceed with unresolved critical failures.

### Phase 2 — Extension (Weeks 3–6)
- Roll out by building/lab in batches; communicate maintenance window and support route.
- Reconcile discovered assets with physical labels and custodians; resolve duplicates and unknowns.
- Train departmental asset managers and technicians; capture exceptions and lessons.

### Phase 3 — Network and stores (Weeks 7–9)
- Pilot SNMP discovery on an approved subnet with read-only access and rate limits; verify detected devices with IT.
- Onboard central warehouse and Chemistry stock using validated opening balances and lot/expiry information.
- Add lab instruments after owner review of fields, calibration needs, safety requirements, and booking policy.

### Phase 4 — Handover (Week 10)
- Train requesters, technicians, asset managers, storekeepers, and administrators.
- Deliver role-specific quick guides, architecture/configuration register, backup/restore evidence, support/escalation contacts, and change log.
- Obtain department sign-off and baseline KPI report; record deferred items and owner/date.

## 7. Backup and recovery
The supplied `scripts/daily_backup.sh` is a template. Configure DB access via a protected MySQL option file or secret manager, GLPI config path, backup destination, encryption, retention, monitoring, and off-host storage. Run under a dedicated least-privilege account. Back up database and required configuration/files consistently. Test restore into an isolated environment before production and at an agreed cadence. A successful backup job is not proof of recoverability.

## 8. Security and maintenance
- Restrict access to internal faculty network/VPN; enforce HTTPS; disable default accounts and remove unused plugins.
- Require named accounts and least privilege; use MFA/SSO if supported and approved.
- Patch OS, GLPI, DB, agents, and plugins under change control; test upgrades in staging and maintain rollback/backup.
- Keep SNMP and DB credentials out of the database where possible, tickets, scripts, and version control; rotate according to FSS policy.
- Review users/profiles quarterly and on role departure; log administrative actions; define incident response and retention.

## 9. Acceptance tests (minimum)
1. Agent reports approved hardware/software fields for pilot PCs and updates without creating duplicates.
2. Department manager cannot view/edit another department's restricted assets or tickets.
3. Faculty admin can produce consolidated summary without granting unnecessary edit rights.
4. Ticket creation, assignment, notifications, pending/resolution/closure, and asset linkage work end to end.
5. Stock receipts/issues/adjustments have traceable actor/time/quantity; threshold alert fires at configured boundary.
6. SNMP scan discovers only approved targets and does not disrupt network devices.
7. Reservation prevents or clearly flags overlapping bookings for supported assets.
8. HTTPS and firewall checks pass; DB is not reachable from user segments.
9. Backup completes, alert is generated on failure, and a restore is demonstrated in isolation.
10. User guides, ownership, escalation, and department sign-offs are recorded.

## 10. KPI definitions
- Automated PC inventory coverage = active managed PCs with a successful inventory in the agreed period ÷ active managed PCs in reconciled register × 100.
- Audit time reduction = (baseline audit hours − post-deployment audit hours) ÷ baseline audit hours × 100.
- Unplanned stockouts = count of incidents where required stock is unavailable unexpectedly; target zero, reviewed monthly.
- MTTR = average elapsed time from ticket creation to resolution; report by priority/category and exclude/categorize requester-wait time consistently.

Set targets only after establishing a trustworthy baseline. Review monthly with departments; KPI outputs depend on accurate, current records.

## 11. Site-specific items still required
Internal hostname/static IP; VM sizing/OS; approved GLPI release and DB compatibility; authorized deployment credentials (never send them in chat); TLS/SMTP details; department user/group roster; network ranges and SNMP policy; asset/stock opening registers; thresholds; retention policy; backup destination and RPO/RTO; service contacts; reservation rules; sign-off owners.