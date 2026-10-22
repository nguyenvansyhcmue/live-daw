# Renderer grain causality audit

- Target commits audited: 36
- Commit → new dominant grain median: 208 samples (4.33 ms)
- Commit → new dominant grain P90: 288 samples (6.00 ms)
- Max |control lookup timestamp delta|: 0 samples

A small commit-to-grain interval and zero lookup delta rule out a stale control queue or old dominant grain as the cause of a later audible mismatch.
