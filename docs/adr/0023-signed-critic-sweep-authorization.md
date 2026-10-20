# ADR-0023 — Signed authorization for durable critic sweeps

- Status: Accepted for the Sprint 2 infrastructure prototype
- Date: 2026-10-20
- Depends on: ADR-0016 (reviewer signatures), ADR-0019 (verified read snapshots), ADR-0022 (durable critic transitions)
- Traceability: AWF-R025, AWF-R031, AWF-R032

## Context

A durable CLEAN_SWEEP currently proves that a locally declared critic observation and
isolated-context reference were bound to one revision transition and recovered without
silently changing their causal positions. It does not prove the declared critic was
authorized to make that observation. Local convergence can consequently be reached
without a signed critic authorization check. The existing Ed25519 reviewer-authentication
contract covers other review roles but not CLEAN_SWEEP observations.

Neither a user-provided critic string nor an event's internal digest proves civil
identity, intellectual independence, scientific correctness, or historical adjudication.

## Decision

1. Extend the signed reviewer role vocabulary additively with CRITIC, bound exclusively
   to an evidence event of kind CRITIC_OBSERVATION. Continue using the canonical,
   versioned ReviewerClaim and Ed25519 grant verification from ADR-0016.
2. Introduce an application-level gate, verify_authorized_critic_sweeps. It recovers
   a durable revision under an explicitly supplied expected ledger head, rejects a
   mismatched run, and requires a locally CONVERGED decision on the supplied immutable
   DocumentIR and RevisionPolicy.
3. Require an exact attestation inventory: every current CleanSweep intent event
   reference maps to precisely one REVIEW_ATTESTATION reference, with no omissions,
   duplicates, or extraneous entries. The signed attestation MUST target the actual
   CRITIC_OBSERVATION reference carried in the durable CLEAN_SWEEP intent, never an
   arbitrary caller-selected observation.
4. Resolve all sweep intents and attestations in one transaction-scoped verified
   evidence read. Verify event kind, revision subject, run, original observation,
   canonical claim, Ed25519 signature, actor/key/role/run/subject/timestamp grant,
   revocation/expiry, event ordering and agreement with CleanSweep.critic_id.
   Re-check the ledger against the recovered exact head to reject concurrent growth
   between journal recovery and attestation reading. Do not introduce a trusted-head
   cache or bypass the existing complete integrity audit.
5. The trust policy's expected SHA-256 and ledger expected head MUST originate outside
   the untrusted SQLite/policy-file pair. Private keys never enter AWF or its repository.
   Public keys and actor IDs express permitted credentials, not human identity.
6. Preserve legacy journal writes and replay contracts for compatibility: the journal
   may represent unsigned historical or diagnostic CLEAN_SWEEP entries, but callers
   MUST invoke this separate gate before presenting sweeps as authorized. This gate
   does not modify records, claim REVIEW_ATTESTED, or grant model training permission.

The result uses AuthorizationGateResult. An invalid or incomplete attestation inventory
reports authorization_verified=false; corrupt or unauthenticated storage/policy roots
remain integrity errors. The independent_adjudication_proven flag remains false
regardless of the cryptographic outcome.

## Alternatives considered

- Automatically authorize sweeps at write time: rejected for this increment because
  reviewer attestations can arrive after immutable observations and journal commits.
  Doing so would also impose a new dependency on previously valid local recovery.
- Sign CleanSweep.critic_id without an observation: rejected; the identity claim would
  not bind the actual evidence or the version of the reviewed manuscript.
- Verify every attestation through an independent full-ledger scan: rejected because
  the same expensive audit can be safely reused within one verified snapshot.
- Treat two distinct actor IDs/keys as proof of independent reviewers: rejected;
  an operator can control more than one identity or key.

## Failure modes and boundaries

- A revoked, expired, wrong-role, wrong-subject, wrong-run or mismatched-actor claim,
  an attestation swap, missing inventory entry, obsolete document, or nonconverged
  revision must fail closed.
- A forged/truncated ledger, mutable trust anchor or concurrent append cannot be
  excused by matching internally consistent hashes; the operator must anchor policy
  digest and ledger head independently and manage real external custody.
- This prototype does not prove isolation of prompts/context, evaluator competency,
  academic correctness, trusted clock, custody of private signing keys, or legitimate
  adjudication of any of the 168 historical MUST items. Revocation can invalidate
  previously authorized sweeps on subsequent verification.

## Verification

- Integration tests construct and sign real CRITIC_OBSERVATION events, persist two
  sweeps through SQLiteRevisionJournal, restart and recover, then reject missing,
  swapped, forged, revoked, stale, wrong-role/run/subject/actor and corrupt causal
  evidence.
- Assert one verified ledger audit per multi-sweep gate, including concurrent-append
  detection and correct negative authorization on reopened findings/changed documents.
- CI quality gate and the independently recreated Windows test run are required
  before merging this increment into develop. No acceptance claim follows merely
  from the existence of this ADR or from a passing synthetic test.
