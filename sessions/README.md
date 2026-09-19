# sessions/ — minted witness sessions

`nanobot -commit <checkfile>` exports here, in one motion:

- `<id>.jsonl` — the session transcript (the model-written record; the key
  must be spoken aloud in it)
- `<id>.mint.json` — the signed envelope (harness-written metadata):

```json
{
  "harness": "nanobot",
  "harness_version": "...",
  "cert_id": "<which baked cert, see certs/>",
  "session": "<id>.jsonl",
  "session_sha256": "<hex>",
  "minted_utc": "<iso>",
  "subagent": false,
  "keys": {"CHECKNAME": "orient-key-CHECKNAME-<24hex>"},
  "signature": "<base64, over the canonical JSON of every field above>"
}
```

Verification (per check, per run, in orient.py): cert pinned and acceptable
under Trust Mode → signature valid → not a subagent → transcript unaltered
since mint → stamped key spoken in the record → peel and run.

An unsigned transcript is not a session. The mint proves which record;
the record is the unlock.
