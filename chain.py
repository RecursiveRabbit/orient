#!/usr/bin/env python3
"""
chain — the append-only anchor. One JSON object per line in chain/chain.jsonl:

  {seq, ts, kind, path, sha256, meta, prev, hash}

hash covers every field but itself; prev is the previous line's hash.
Cannot go backwards: altering an old link breaks every later hash, and a
full rewrite discontinues against heads that orient runs already recorded
(the ratchet). That is all it needs. No branches.

Correction doctrine (in-place edits are the workflow): every link's hash and
prev are verified, and each path's CURRENT content on disk is checked against
its LATEST link. Edited files are re-signed and re-minted; the old bytes stay
pinned by their old links and the diff lives in git. kind="retire" ends a
file's chain without deleting the history: the path must be absent from disk.

Usage:
  chain.py append <kind> <path> [meta-json]   # mint a file into the chain
  chain.py retire <path> [meta-json]          # end a file's chain deliberately
  chain.py note <kind> [meta-json]            # mint a fileless link
  chain.py verify                             # recompute; reconcile with disk
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
    if path and kind != "retire":
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
    prev = None
    latest = {}
    for link in ls:
        recorded = link.pop("hash", None)
        if sha(canon(link)) != recorded:
            return f"CHAIN BREAK at seq {link['seq']}: hash mismatch"
        if link["prev"] != prev:
            return f"CHAIN BREAK at seq {link['seq']}: prev linkage broken"
        prev = recorded
        if link.get("path"):
            latest[link["path"]] = link  # later links supersede earlier ones
    for path, link in latest.items():
        p = ROOT / path
        if link["kind"] == "retire":
            if p.exists():
                return (f"CHAIN BREAK: {path} resurrected after retirement "
                        f"(retired at seq {link['seq']})")
        else:
            if not p.exists():
                return (f"CHAIN HOLE at seq {link['seq']}: "
                        f"{path} missing from disk")
            if sha(p.read_bytes()) != link["sha256"]:
                return (f"CHAIN BREAK at seq {link['seq']}: {path} altered "
                        "since its latest minting")
    return f"chain ok: {len(ls)} links, head {recorded[:12]}, files verified"


if __name__ == "__main__":
    if len(sys.argv) >= 2 and sys.argv[1] == "verify":
        print(verify())
    elif len(sys.argv) >= 4 and sys.argv[1] == "append":
        print(append(sys.argv[2], sys.argv[3],
                     json.loads(sys.argv[4]) if len(sys.argv) > 4 else {}))
    elif len(sys.argv) >= 3 and sys.argv[1] == "retire":
        print(append("retire", sys.argv[2],
                     json.loads(sys.argv[3]) if len(sys.argv) > 3 else {}))
    elif len(sys.argv) >= 3 and sys.argv[1] == "note":
        print(append(sys.argv[2], None,
                     json.loads(sys.argv[3]) if len(sys.argv) > 3 else {}))
    else:
        raise SystemExit(__doc__)
