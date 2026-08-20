# MVP Implementation

## Status

In progress. Milestones 1 and 2 are complete. Milestone 3 has deterministic
implementation and evidence but awaits its real-provider evaluation. Milestone
4 is ready. The
[MVP implementation technical design](../technical-design/02-mvp-implementation.md)
and all detailed guides were approved on 2026-08-18.

## Execution rules

- Execute milestones in order unless this index explicitly allows overlap.
- Do not mark a checkbox complete until its implementation and stated evidence
  both exist.
- Run focused tests while developing; run the complete repository checks before
  completing each milestone.
- Add or remove dependencies only through `uv add` or `uv remove`, and commit
  the generated `uv.lock` change.
- Do not move security, privacy, accessibility, or test work to the final
  milestone when its associated feature is implemented earlier.
- If implementation reveals a missing decision or conflicts with the approved
  design, stop and update the design before continuing.
- Keep all v0.1 exclusions in `../requirements.md` out of these milestones.

## Milestones

| Order | Milestone | Current status | Outcome |
|---:|---|---|---|
| 1 | [Application foundation](02-mvp-implementation/01-application-foundation.md) | Complete | The installed package starts one stateless web process and serves its shell and health endpoint. |
| 2 | [Manual splitting workflow](02-mvp-implementation/02-manual-splitting-workflow.md) | Complete | A user can manually enter, validate, assign, and calculate an exact split. |
| 3 | [Receipt extraction](02-mvp-implementation/03-receipt-extraction.md) | In progress: external evaluation pending | A user can upload a safe image and receive editable extracted receipt data. |
| 4 | [PDF export](02-mvp-implementation/04-pdf-export.md) | Ready | A valid split can be downloaded as a complete, readable PDF. |
| 5 | [Production readiness](02-mvp-implementation/05-production-readiness.md) | Blocked by milestones 3 and 4 | The complete MVP passes release checks and runs from its production image. |

Milestones 3 and 4 may be developed in parallel after milestone 2 because both
depend on the same finalized calculation contract and neither depends on the
other. Milestone 5 begins only after both are complete.

## Design coverage

| Approved design guide | Primary milestone | Additional coverage |
|---|---|---|
| System architecture | 1 | Boundaries enforced in 2–5 |
| Domain and calculations | 2 | Server revalidation in 4 |
| Web workflow | 2 | Upload behavior in 3 and download behavior in 4 |
| Receipt extraction | 3 | Release evaluation in 5 |
| PDF export | 4 | Manual visual release check in 5 |
| Security and privacy | 1–4, with each feature | Public-deployment gates audited in 5 |
| Runtime and testing | 1–4, with each feature | Container, CI, and acceptance closure in 5 |

## Requirement coverage

| Acceptance criterion | Implemented primarily in | Release evidence closed in |
|---:|---|---|
| 1. Upload a receipt | Milestone 3 | Milestone 5 |
| 2. Convert it into editable items | Milestone 3 | Milestone 5 |
| 3. Add participants | Milestone 2 | Milestone 5 |
| 4. Assign items with checkboxes | Milestone 2 | Milestone 5 |
| 5. Calculate exact totals including tax and tip | Milestone 2 | Milestone 5 |
| 6. Correct extraction mistakes | Milestones 2 and 3 | Milestone 5 |
| 7. Confirm receipt reconciliation | Milestone 2 | Milestone 5 |
| 8. Generate and download a PDF | Milestone 4 | Milestone 5 |

The planned test evidence for these criteria is maintained in `../tests.md`.

## Workstream completion

The MVP implementation workstream is complete only when:

- [ ] Every milestone completion criterion is checked.
- [ ] Every acceptance criterion in `../requirements.md` has passing evidence
  recorded in `../tests.md`.
- [ ] All required commands in `AGENTS.md` pass from a clean checkout.
- [ ] The production image passes its startup, route, asset, health, and
  shutdown smoke tests.
- [ ] Required external extraction and manual visual checks are recorded.
- [ ] No account, persistence, payment, custom split, multiple-currency, or
  other out-of-scope capability was introduced.
