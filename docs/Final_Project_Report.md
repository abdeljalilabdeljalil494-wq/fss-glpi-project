# Implementation of GLPI for Centralized Asset & Inventory Management
## Faculty of Sciences of Sfax (FSS)

**Final project report and implementation handover package**  
Prepared from the supplied project specifications. Deployment status: **implementation package completed; production deployment pending authorized FSS infrastructure and data access.**

## Executive summary
This project defines a centralized GLPI service for managing IT, network, laboratory assets, consumable stock, and technical support across Informatics, Physics, Chemistry, Biology, and central administration. It addresses fragmented manual registers, weak software visibility, unrecorded stock movements, and disconnected maintenance history. The design combines scoped access, agent-based inventory, controlled network discovery, traceable stock movements, and structured ticket workflows.

The supplied specifications establish a ten-week roadmap, internal fixed-IP hosting, department-level isolation, faculty-wide administrative reporting, daily database/configuration backups, and four outcome KPIs. This deliverable translates those requirements into an implementable architecture, configuration model, rollout plan, acceptance criteria, and operating guidance. The live GLPI service has not been deployed because no server, administrator access, active database, or FSS inventory data was provided; the report does not represent unverified deployment or inventory results as facts.

## 1. Background and problem
FSS currently requires a unified information system for classroom and lab PCs, network infrastructure, scientific instruments, warehouse stock, and repair requests. Manual audits can become outdated; software versions and license evidence are difficult to reconcile; equipment moves are not consistently captured; and maintenance history is fragmented. These weaknesses increase audit effort and risk of shortages or delayed repairs.

## 2. Objectives and scope
1. Create a dependable asset register with locations, ownership, status, and maintenance links.
2. Automate approved workstation hardware/software discovery.
3. Discover approved network equipment using controlled SNMP scanning.
4. Track lab instruments and consumable stock, including movement history and threshold alerts.
5. Standardize ticket intake, categorization, assignment, resolution, and reporting.
6. Isolate department access while preserving authorized consolidated administration.
7. Establish secure operations, tested backups, training, and measurable KPIs.

In scope: Informatics/general IT, Physics, Chemistry, Biology, central warehouse, faculty IT operations. Out of scope without additional approval: public Internet access, unapproved monitoring, credential collection, chemical safety compliance itself, and unverified live database reporting.

## 3. Requirements traceability
| Specification requirement | Design response | Verification |
|---|---|---|
| Automatic inventory on PCs | GLPI Agent pilot then staged managed deployment | Compare pilot records with sampled endpoints |
| SNMP network discovery | Approved subnet, read-only credentials, rate limits | Confirm target scope and discovered devices with IT |
| Storehouse entry/exit and alerts | Auditable receipt/issue/adjustment records and minimum thresholds | Test transactions and boundary alert |
| Helpdesk lifecycle | Categories, assignment groups, status workflow, work logs | End-to-end ticket test |
| Specialized lab assets | Type-specific fields for microscopes, spectrometers, balances, incubators | Department owner review and sample verification |
| Department isolation | Entity/profile/group design with least privilege | Negative cross-department access tests |
| Consolidated view | Faculty admin read/report access as approved | Test admin report and edit restrictions |
| Daily backups | Automated protected DB/config backup and restore drills | Job monitoring and isolated restore evidence |
| Reservation assistance | Enable supported reservation workflow; document fallback where unsupported | Concurrent booking/conflict test |

## 4. Proposed architecture
The service is hosted on an internal FSS virtual machine with a static private IP and DNS name. Users access GLPI over HTTPS through an internal reverse proxy or approved web service. The SQL database is private and accepts connections only from the application host. Managed computers report inventory through GLPI Agent at an approved interval. Network discovery is limited to authorized management subnets and uses read-only SNMPv3 credentials where supported. Daily backups are encrypted and stored separately from the production VM.

Production must use a release and database combination explicitly supported by GLPI at installation time. Exact versions, sizing, hostname, firewall paths, retention, and recovery objectives are subject to FSS IT approval. The service is not to be exposed publicly.

## 5. Data and access design
### Asset register
Common attributes: unique inventory identifier, asset type, make/model, serial number, department/entity, building/room/lab, custodian, status, acquisition/warranty information, supplier, and last verified date. Lab-specific fields may include measurement range, resolution, calibration due date, condition, and accessories. Fields are kept to operational need.

### Software and license evidence
Agent inventory supplies installed software/version visibility on managed PCs. Procurement/license evidence is reconciled separately; automated discovery alone is not a legal compliance determination.

### Inventory and consumables
A stock item records code, name, unit, location, batch/lot, expiry when relevant, supplier, quantity, and approved minimum. Each receipt, issue, or adjustment records date, quantity, actor, reason, and source/destination. Available-quantity semantics and reservation deductions must be agreed before threshold alerts are enabled. Chemistry workflows must also meet applicable FSS safety and SDS procedures.

### Roles
Requesters submit tickets and (where enabled) reservations. Department asset managers maintain only their department's records. Technicians work assigned queues. Storekeepers manage authorized stock. Named faculty administrators receive consolidated views. Technical administrators manage the platform and should be few and explicitly authorized.

## 6. Ticket and reservation workflows
Ticket categories: Hardware, Software, Network, Lab Equipment, Account/Access, Other. Intake captures department, location, impact, urgency, description, affected asset, and contact method. Statuses: New, Assigned, In progress, Pending with reason, Resolved, Closed. Technicians record diagnosis, actions, parts, and resolution; tickets must never request passwords.

Reservations are enabled only for suitable assets and only after confirming that the installed GLPI functionality or approved plugin supports the required conflict behavior. Asset owners define duration, lead time, cancellation, approval, and maintenance blackout rules. Unsupported equipment uses a clearly designated approved scheduling fallback until tested conflict prevention is available.

## 7. Implementation roadmap
| Phase | Timeline | Principal deliverables |
|---|---|---|
| Pilot | Weeks 1–2 | Hardened internal GLPI instance, 5–10 pilot PCs, roles/entities, tested ticket and backup workflows |
| Extension | Weeks 3–6 | Staged rollout across computer rooms and departmental labs; reconciled asset data; trained coordinators |
| Network & stores | Weeks 7–9 | Controlled network discovery, warehouse and Chemistry stock, selected laboratory equipment |
| Handover | Week 10 | User training, operating documentation, restore evidence, KPI baseline, final sign-off and chemical-tracking study |

A preparation gate precedes Phase 1: approve VM/network/TLS, product compatibility, account roster, access policy, backup target, data fields, stock thresholds, and responsible owners.

## 8. Security, privacy, and continuity
Access is restricted to the internal faculty network or approved VPN. HTTPS is mandatory. Database privileges are least-privilege; firewall rules limit database access to the application host. Named accounts, role reviews, secure credential storage, plugin governance, patch/change control, time synchronization, and audit review are required. Backups include the database and required configuration/files, are encrypted and off-host, and are monitored. Restore tests—not just backup-job completion—demonstrate recoverability. Credentials must not be placed in tickets, source files, or this report.

## 9. Testing and acceptance
Before production rollout, demonstrate: accurate pilot PC inventory without duplicates; denied cross-department access; authorized consolidated reports; complete ticket lifecycle; traceable stock movements and threshold alert; safe scoped SNMP discovery; reservation conflict behavior; HTTPS and network isolation; monitored backup failure and successful isolated restore; and documented training/ownership/sign-offs. The accompanying acceptance checklist provides a recordable test template.

## 10. KPIs and evaluation
- **Automated PC inventory coverage:** active managed PCs successfully inventoried within the agreed reporting period divided by the reconciled active PC count.
- **Inventory audit-time reduction:** (baseline audit hours − measured post-rollout audit hours) divided by baseline hours.
- **Unplanned warehouse stockouts:** count of unexpected shortages; target is zero, reviewed monthly.
- **Mean time to resolve (MTTR):** mean elapsed time from ticket creation to resolution, segmented by priority/category with requester-wait treatment defined consistently.

Targets and measured results are not fabricated. Establish baselines during the pilot, then review monthly with department representatives.

## 11. Risks and mitigations
| Risk | Mitigation |
|---|---|
| Incomplete or inaccurate starting registers | Validate owner/location, label assets, reconcile samples, track unknowns |
| Excessive privileges or data leakage | Entity isolation, least privilege, test accounts, periodic access review |
| Agent or SNMP disruption | Pilot, approved scope, change window, conservative scan rates, rollback |
| Plugin/version incompatibility | Prefer supported core functions; test approved plugins and upgrades in staging |
| False stock alerts or missed shortage | Agree availability formula and thresholds; audit sample movements |
| Backup exists but cannot restore | Regular isolated restore drills and documented recovery steps |
| Low adoption | Department champions, role-specific training, clear service desk route |
| Unverified reservation conflict handling | Concurrent booking tests; fallback process until proven |

## 12. Handover and outstanding prerequisites
The accompanying runbook, CSV templates, backup script template, and acceptance checklist form the handover package. FSS must still supply: authorized internal host/network details; approved GLPI/OS/database versions; administrator execution of installation; TLS/SMTP configuration; department user/group roster; approved asset/stock registers; network discovery scope and SNMP policy; thresholds; retention and recovery objectives; service contacts; and department sign-offs. These are controlled operational inputs and must be exchanged through approved channels, not this report or an unprotected chat.

## Conclusion
The project design covers the requirements in the FSS specification and provides a practical staged path from a representative pilot to faculty-wide handover. Success depends on validated source data, least-privilege configuration, department participation, safe rollout, tested restore capability, and sustained ownership. Production completion must be confirmed by FSS IT after deployment and acceptance testing; this package intentionally makes no claim that those external actions have already occurred.