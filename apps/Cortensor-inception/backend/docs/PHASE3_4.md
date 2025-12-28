# Phase 3.4 — Evidence, Canonicalization, and Attestation (Finalized)

Phase 3.4 transforms decisions into immutable, canonically hashed, cryptographically attested evidence bundles that can be independently verified without access to inference, models, or runtime state.

## Components

- `canonicalize` — RFC-8785 style canonical JSON serializer (stable key ordering)
- `hashEvidence` — canonical hashing (sha256)
- `keys` — explicit key model (`rsa-2048` currently)
- `signer` — typed attestation using RSA-SHA256
- `verify` — public-key verification of attestation
- `immutability` — storage-side pre-persist guard
- `retention` — minimum retention policy and legal hold
- `bundle` — `EvidenceBundle` construction
- `index` — `runPhase3_4` sealed entry point that returns `{ bundle, hash, attestation }`

## Auditor rules

To verify a bundle an auditor needs only:
- the `bundle` object
- the `attestation` (signed hash)
- the signer's public key

No trust in environment or runtime is required — just math.

## Non-Goals

- This layer does not decide policy (that's Phase 3.3)
- This layer does not store evidence (it provides guards and types to be used by storage)

