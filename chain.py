#!/usr/bin/env python3
"""
chain — the append-only anchor. One JSON object per line in chain/chain.jsonl:

  {seq, ts, kind, path, sha256, meta, prev, hash}

hash covers every field but itself; prev is the previous line's hash.
Cannot go backwards: altering an old link breaks every later hash, and a
full rewrite discontinues against heads that orient runs already recorded
(the ratchet). That is all it needs. No branches.

Usage:
  chain.py append <kind> <path> [meta-json]   # mint a file into the chain
  chain.py note <kind> [meta-json]            # mint a fileless link
  chain.py verify                             # recompute; check files on disk
"""
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CHAIN = ROOT / "chain" / "chain.jsonl"


def canon(o):
    return json.dumps(o, sort_keys=True, separators=(",", ":")).encode()


def sha(b):
    return hashlib.sha256(b).hexdigest()


def links():
    if not CHAIN.exists():
        return []
    return [json.loads(l) for l in CHAIN.read_text().splitlines() if l.strip()]


def append(kind, path, meta):
    ls = links()
    digest = None
    if path:
        p = ROOT / path
        if not p.is_file():
            raise SystemExit(f"no such file: {path}")
        digest = sha(p.read_bytes())
    link = {"seq": len(ls),
            "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "kind": kind, "path": path, "sha256": digest,
            "meta": meta, "prev": ls[-1]["hash"] if ls else None}
    link["hash"] = sha(canon(link))
    CHAIN.parent.mkdir(exist_ok=True)
    with CHAIN.open("a") as f:
        f.write(json.dumps(link) + "\n")
    return link["hash"]


def verify():
    ls = links()
    if not ls:
        return "chain empty"
    # A path may be re-minted (a check is corrected and re-signed); the chain
    # is append-only history, so the on-disk content check applies to the
    # LATEST link per path. Older links are verified structurally forever.
    latest = {}
    for link in ls:
        if link["path"]:
            latest[link["path"]] = link["seq"]
    prev = None
    for link in ls:
        recorded = link.pop("hash", None)
        if sha(canon(link)) != recorded:
            return f"CHAIN BREAK at seq {link['seq']}: hash mismatch"
        if link["prev"] != prev:
            return f"CHAIN BREAK at seq {link['seq']}: prev linkage broken"
        if link["path"] and latest.get(link["path"]) == link["seq"]:
            p = ROOT / link["path"]
            if not p.exists():
                return f"CHAIN HOLE at seq {link['seq']}: {link['path']} missing from disk"
            if sha(p.read_bytes()) != link["sha256"]:
                return (f"CHAIN BREAK at seq {link['seq']}: "
                        f"{link['path']} altered since minting")
        prev = recorded
    return f"chain ok: {len(ls)} links, head {recorded[:12]}, files verified"


if __name__ == "__main__":
    if len(sys.argv) >= 2 and sys.argv[1] == "verify":
        print(verify())
    elif len(sys.argv) >= 4 and sys.argv[1] == "append":
        print(append(sys.argv[2], sys.argv[3],
                     json.loads(sys.argv[4]) if len(sys.argv) > 4 else {}))
    elif len(sys.argv) >= 3 and sys.argv[1] == "note":
        print(append(sys.argv[2], None,
                     json.loads(sys.argv[3]) if len(sys.argv) > 3 else {}))
    else:
        raise SystemExit(__doc__)
