# Engineering Tenets

These tenets explain the engineering values behind Checkmate's concrete agent
instructions and technical decisions. They guide judgment when a situation is
not covered by a specific rule.

## 1. Reproducibility over convenience

A fresh checkout at a given commit should produce the same development
environment, test results, build artifacts, and application behavior.

The Python runtime, direct dependencies, transitive dependencies, build tools,
and production system dependencies must be controlled and recorded. Lockfiles
and generated build artifacts are outputs of declared tooling, not files to edit
by hand.

## 2. Simple over clever

This is an MVP. Choose clear, direct implementations whose behavior is easy to
understand and change. Introduce an abstraction only when it creates an
immediate, demonstrable benefit for the current requirements.

Avoid speculative frameworks, generic repositories, unnecessary service
layers, and infrastructure intended only for possible future versions.

## 3. Business logic is deterministic

Receipt extraction may be probabilistic because it uses OCR or an external AI
service. Once receipt data enters the application, the following behavior must
be deterministic Python code:

- Item subtotal calculation
- Shared-item allocation
- Tax allocation
- Tip allocation
- Cent rounding and remainder distribution
- Receipt-total validation

Identical validated inputs must always produce identical outputs. Monetary
logic must use integer minor units or decimal arithmetic, never binary
floating-point arithmetic.

## 4. External systems live behind interfaces

Application policy must not depend directly on a particular OCR, AI, storage,
or PDF provider. External systems should be represented by narrow interfaces,
with production and test implementations where useful.

For example, a `ReceiptParser` interface may have an external-service
implementation and a deterministic fake used by automated tests. Interfaces
should reflect application needs rather than expose an entire vendor SDK.

## 5. Invalid data fails loudly

The application must not silently turn malformed or inconsistent receipt data
into a plausible-looking split. Invalid monetary values, unassigned non-zero
items, inconsistent totals, and failed external responses must produce explicit
errors or visible validation states.

Error messages should explain what the user can correct. Internal failures
should retain enough non-sensitive context for diagnosis without exposing
secrets or personal data.

## 6. Every core behavior is testable in isolation

Core receipt validation and split calculation must run in tests without a
browser, database, external AI service, network connection, or API credentials.

Tests should emphasize observable behavior and important invariants, including
that participant totals add up exactly to the receipt total. End-to-end tests
complement this isolation; they do not replace focused unit tests.

## 7. Dependencies are intentional

Every dependency increases maintenance work, security exposure, build time, and
the chance of platform-specific failures. Add one only when it materially
improves correctness, safety, or delivery speed compared with a small and clear
implementation using the standard library or an existing dependency.

Dependency changes must be reviewable, locked, tested, and removable without
rewriting unrelated business logic.

## 8. Security and privacy by default

Receipt images, restaurant details, participant names, and API credentials are
sensitive even when the MVP has no user accounts or database. Collect, retain,
transmit, and log only what is required for the active user flow.

Secrets belong in environment-based secret management, never source control.
Use synthetic or deliberately sanitized fixtures in tests and documentation.
External-service boundaries must make data transmission explicit and limited.
