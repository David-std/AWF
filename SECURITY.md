# AWF security and privacy policy (planning baseline)

No public hosted service or API has been deployed yet. The project will operate on academic manuscripts and may handle sensitive unpublished research; **local-only processing is the default** until an explicit external-processing consent/configuration is introduced.

## Mandatory engineering controls

- Never add manuscripts, raw PDFs/DOCX, credentials, .env files, model/provider tokens, closed-source datasets or GPU service credentials to GitHub.
- Use content-addressed immutable originals and derived revisions; redact body text from logs by default. Log only event IDs, hashes, controlled error codes and non-sensitive performance measures.
- Treat PDF/DOCX as untrusted input: file-size/time/page limits, macro avoidance, safe parsers and sandboxing when warranted.
- Separate interactive inference from offline training; keep protected holdout isolated and unavailable to model retrieval.
- Reject critical verification failures; route critical uncertainty to human review. A crashed verifier may never mean accepted.
- When APIs are added, implement authentication/authorization, access scopes, quotas, sanitization and provider timeouts before deployment.
- Review license, permission, retention and transfer terms before sending a document to any third-party model provider.

## Reporting a vulnerability

Do not put exploits containing private manuscripts, tokens or identifying data into a public issue. Contact repository maintainers through a private GitHub channel if enabled; no dedicated security inbox is committed at present.

Current state: this file records the **intended controls**, not results of a security audit.
