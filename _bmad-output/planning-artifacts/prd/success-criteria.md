# Success Criteria

## User Success

- A user configures a playbook and runs a full story cycle (create → review → ATDD → dev → code review) without intervening. They return to completed, committed, multi-model-validated artifacts ready for a 5-minute human review.
- The init wizard gets a new user from zero to a working config in under 5 minutes, querying available models from their installed CLIs.
- A user reads the state file or git log and can reconstruct exactly what happened, which model ran which step, and what the outcome was.

## Business Success

- Bobby and team use it daily as the standard way to run BMAD automated cycles.
- Community adoption measured by active users — target number TBD but tracked as primary growth metric.
- The tool becomes the recognized standard for automated BMAD workflow execution.

## Technical Success

- Runs 10+ story cycles without requiring human intervention (excluding genuine content decisions).
- Recovers gracefully from rate limit errors, transient CLI failures, and network interruptions.
- State file is always consistent — a crash at any point allows clean resume from last completed step.
- Logs are comprehensive enough to diagnose any failure without reproducing it.

## Measurable Outcomes

- **Attention reclaimed:** A full story cycle requires ≤5 minutes of human review time instead of 2+ hours of active participation.
- **Reliability:** <5% of runs require human intervention for non-content reasons (errors, crashes, state corruption).
- **Onboarding:** New user from install to first successful automated run in <15 minutes.
