#!/usr/bin/env python3
"""
orient — the wake-up organ.

Read me every morning; reading me is my ratification. I have three jobs:

  1. VERIFY WITNESSES — a check may run only if two distinct sessions spoke
     its key aloud. The key lives nowhere but in the signers' session
     transcripts, read at their recorded commits from the session-files repo.
     To get the key you must touch the transcript that vouched the code.
     The record is the unlock.
  2. RUN RATIFIED CHECKS — a check is one file returning one string.
     Everything a check returns is escaped. Only strings cross.
  3. SUBSTITUTE — "$NAME key=value" in template.json becomes the escaped string.

Unratified checks do not run. Their slots render as placeholders naming their
witness count. The chain (chain/chain.jsonl) is append-only; every report
records the head it saw (the ratchet: a rewritten history discontinues
against heads already recorded).

Sessions repo: $ORIENT_SESSIONS_REPO or ~/Coding_Projects/session-files.
"""
import hashlib
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CHAIN = ROOT / "chain" / "chain.jsonl"
TEMPLATE = ROOT / "template.json"
CHECKS = ROOT / "checks"
SESSIONS = Path(os.environ.get("ORIENT_SESSIONS_REPO",
                               Path.home() / "Coding_Projects" / "session-files"))
TIMEOUT = 30


def sha(b):
    return hashlib.sha256(b).hexdigest()


def chain_head():
    try:
        return json.loads(CHAIN.read_text().strip().splitlines()[-1])["hash"]
    except Exception:
        return None


def spoken_key(name, witness):
    """The key this witness spoke, read from the transcript AT ITS COMMIT —
    never the working tree. None if the record does not vouch."""
    try:
        r = subprocess.run(
            ["git", "-C", str(SESSIONS), "show",
             f"{witness['commit']}:{witness['session_path']}"],
            capture_output=True, timeout=30)
    except Exception:
        return None
    if r.returncode != 0:
        return None
    m = re.search(rf"orient-key-{re.escape(name)}-[0-9a-f]{{24}}",
                  r.stdout.decode("utf-8", "replace"))
    return m.group(0) if m else None


def peel(blob, keys):
    """Remove one encryption layer per key, outermost (latest witness) first."""
    for k in keys:
        r = subprocess.run(["openssl", "enc", "-d", "-aes-256-cbc", "-a",
                            "-pbkdf2", "-pass", f"pass:{k}"],
                           input=blob, capture_output=True, timeout=15)
        if r.returncode != 0:
            return None
        blob = r.stdout
    return blob


def escape(s):
    """Checks return sensor readings, not messages. Strip anything that is
    not plain printable text; collapse all whitespace."""
    s = re.sub(r"\x1b\[[0-9;?]*[a-zA-Z]", "", s)
    s = "".join(c if c.isprintable() else " " for c in s)
    return re.sub(r"\s+", " ", s).strip()


def evaluate(name, args):
    enc = CHECKS / f"{name}.sh.enc"
    wit = CHECKS / f"{name}.witness.json"
    if not enc.exists() or not wit.exists():
        return f"MISSING — no artifact for {name}"
    w = json.loads(wit.read_text())
    keys, seen = [], set()
    for witness in w.get("witnesses", []):
        if witness["session_path"] in seen:
            continue  # two witnesses means two distinct sessions
        k = spoken_key(name, witness)
        if k:
            keys.append(k)
            seen.add(witness["session_path"])
    if len(keys) < 2:
        return (f"UNRATIFIED {len(keys)}/2 witnesses — "
                f"see checks/{name}.witness.json")
    plain = peel(enc.read_bytes(), list(reversed(keys)))
    if plain is None or sha(plain) != w.get("sha256"):
        return ("WITNESS FAILURE — decrypted hash does not match the "
                "ratified hash; do not trust this slot")
    try:
        r = subprocess.run(["bash", "/dev/stdin", *args], input=plain,
                           capture_output=True, timeout=TIMEOUT, cwd=ROOT,
                           env={**os.environ, "ORIENT_ROOT": str(ROOT)})
    except subprocess.TimeoutExpired:
        return "TIMEOUT"
    return escape(r.stdout.decode("utf-8", "replace")) or "EMPTY"


def render(node):
    if isinstance(node, dict):
        return {k: render(v) for k, v in node.items()}
    if isinstance(node, list):
        return [render(v) for v in node]
    if isinstance(node, str) and node.startswith("$"):
        name, *args = node[1:].split()
        return evaluate(name, args)
    return node


def main():
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    report = {
        "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "chain_head": chain_head(),
        "report": render(json.loads(TEMPLATE.read_text())),
    }
    out = json.dumps(report, indent=1)
    (ROOT / "reports").mkdir(exist_ok=True)
    (ROOT / "reports" / f"orient-{stamp}.json").write_text(out + "\n")
    print(out)


if __name__ == "__main__":
    sys.exit(main())
