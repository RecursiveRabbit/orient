# certs/ — pinned nanobot baked keys (the CA trust store)

One PEM per nanobot revision: `<cert_id>.pem`. The cert_id in a mint envelope
must match a file here, and be acceptable under the CERT_POLICY in
orient.py's Trust Mode:

- `"forever"` (default) — every pinned cert stays valid; historic mints
  remain witnesses.
- `("days", n)` — mints older than n days need recertification.
- `"latest"` — only the cert named in the `LATEST` file; a nanobot revision
  recertifies the whole canon.

Pinning a cert is a deliberate act: it means Evans (or a session acting with
his authority) has inspected that nanobot build and accepts its mints.
