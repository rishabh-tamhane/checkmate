# v0.1 MVP Technical Design

This file is the index for version-specific technical-design workstreams.
Requirements define what v0.1 must do; the documents below define how each
workstream is implemented.

## Workstreams

- [Project setup](technical-design/01-project-setup.md)
  - Status: Established
- [MVP implementation](technical-design/02-mvp-implementation.md)
  - Status: Complete draft awaiting approval; implementation tasks remain
    blocked
  - Detailed guides:
    - [System architecture](technical-design/02-mvp-implementation/01-system-architecture.md)
      - Status: Approved on 2026-08-18
    - [Domain and calculations](technical-design/02-mvp-implementation/02-domain-and-calculations.md)
      - Status: Approved on 2026-08-18
    - [Web workflow](technical-design/02-mvp-implementation/03-web-workflow.md)
      - Status: Approved on 2026-08-18
    - [Receipt extraction](technical-design/02-mvp-implementation/04-receipt-extraction.md)
      - Status: Draft, awaiting review
    - [PDF export](technical-design/02-mvp-implementation/05-pdf-export.md)
      - Status: Draft, awaiting review
    - [Security and privacy](technical-design/02-mvp-implementation/06-security-and-privacy.md)
      - Status: Draft, awaiting review
    - [Runtime and testing](technical-design/02-mvp-implementation/07-runtime-and-testing.md)
      - Status: Draft, awaiting review

## Design governance

- Read the applicable workstream design before modifying code or configuration.
- Do not begin MVP application implementation until its design status is
  `Approved`.
- Record decisions and their rationale in the applicable design document before
  deriving implementation tasks.
- If requirements and a technical design disagree, stop and resolve the
  conflict before implementation.
- Keep future-version ideas out of the active design and record them in the
  backlog.

## Detailed-guide governance

- The MVP implementation document remains the authoritative design proposal.
- Its detailed guides explain the selected approach, provide worked examples,
  and identify implications for future implementation tasks.
- Each guide records whether that design area has been reviewed and approved.
- Partial guide approval records review progress but does not unblock
  implementation tasks or application code. The overall workstream remains
  blocked until every required guide is approved and the parent design status
  changes to `Approved`.
- A material change to an approved guide returns that guide to `Draft` until the
  change is reviewed.
- If a guide would introduce or change a decision, update and review the parent
  design first. If a guide and the parent disagree, the parent controls.
