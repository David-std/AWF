# AWF S2 — source rights/provenance gate (private local API)

This slice adds a **rights-evidence boundary**, not a legal or scientific adjudication system. The source ledger, original documents, citation PDFs, grant instruments, and any real decision files remain locally private and must not be committed.

## Source of truth

The authoritative object cannot be a mutable dossier field like `source_rights_status`. AWF instead expects a canonical rights inventory tied to an exact source file SHA-256, parent archive SHA-256 and segment offsets. An independently stored expected inventory hash is mandatory. Claims include owner, claimed authority, jurisdiction, licence expression, evidence HTTPS URI and evidence-byte SHA-256. A URI is a locator, **not the legal evidence**.

The current implementation exposes:
- `parse_source_rights(data, expected_sha256, expected_asset)` in `awf.application.commands.source_rights`.
- `check_source_right(inventory, source_bytes, start_byte, end_byte, expected_fragment_sha256, use, evidence_by_sha256, authority, expected_authority_policy_sha256, now)`.
- Domain types `SourceAsset`, `RightsUse`, `RightsClaim`, `RightsInventory` and `RightsDecision` in `awf.domain.source_rights`.

A local application **must** independently supply the file bytes, the source and fragment digests, the expected inventory digest, trusted time and actual evidence bytes. For any positive result it must additionally supply an independent, appropriately authorized `RightsAuthorityPort` and independently pinned policy digest. **No production rights authority adapter is shipped in this PR**: default evaluation therefore remains `UNKNOWN` even for plausible SPDX/CC strings.

`TRAIN_ALLOWED` is a purpose-specific rights conclusion only. It never sets `training_authorized=true` or authorizes training in S5; those require dataset-level rights assessment, owner approval where relevant, safety/splits and later independent acceptance. A dataset card or published article does not prove this right.

## Limits and next increment

The byte-span design intentionally does not silently transfer a file-level permission to unknown fragments or other files. This PR does not validate genuine beneficial ownership, contract jurisdiction, copyright exceptions, model-training legality, permission of a final rights issuer, revoked third-party notices or linked source contents. The external authority port must later be implemented only after an authority owner and chain-of-custody procedure exist. The scientific disagreement adjudication process is independent and comes later.

Read ADR-0028 and the negative synthetic tests before using this boundary. No new CLI flag writes a rights grant and no existing `inspect-review` behavior changes.
