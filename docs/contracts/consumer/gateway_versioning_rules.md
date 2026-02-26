# Gateway Contract Versioning Rules (HTTP + WS)

## HTTP
- External HTTP APIs MUST be versioned using path prefix: `/api/vN/...`.
- Existing non-versioned compatibility routes (`/api/chat/*`, `/v1/content/*`) are legacy-compatible façades managed by Gateway ACL/flags.
- Breaking changes require a new major version path (`/api/v2/...`) and dual-run migration window.

## WebSocket
- WS contract version is negotiated with subprotocol `jwt` + token semantics.
- Query fallback `?token=` remains supported for backward compatibility.
- Breaking WS envelope changes require explicit version marker (e.g. `v=2` query or versioned subprotocol) and compatibility overlap.

## Provider Verification Gate
- Every PR must pass Gateway provider verification tests that validate route ownership, toggles, and WS contract envelope invariants.
- Any drift between contract files and gateway runtime fails CI merge checks.
