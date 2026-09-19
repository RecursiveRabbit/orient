#!/usr/bin/env python3
"""
sign — the witness act. Not part of the core; any session may write its own.

  sign.py NAME --signer WHO --session-path P --commit C --key K [--src FILE]
  sign.py NAME --signer WHO --minted-session M --key K [--src FILE]

Encrypts the check source (checks/src/NAME.sh, or --src) with the witness
key (layered outermost over any prior signatures), writes checks/NAME.sh.enc,
updates checks/NAME.witness.json, writes checks/NAME.key (a pointer to the
witness session), and mints all three artifacts into the chain.

Two witness forms (session-minting.md):
  --minted-session M — a nanobot-minted session envelope in sessions/ (the
    preferred form; M is the .mint.json filename; the harness stamps the key
    into the signed envelope and the model speaks it in the transcript).
  --session-path P --commit C — legacy: an unsigned transcript anchored by
    git history in the session-files repo. Only counts when orient.py's
    ACCEPT_LEGACY_GIT_WITNESSES is True (or under `-test` recovery).

With no --key, prints a fresh key to speak aloud and exits.
"""
import hashlib
import json
import os
import re
import secrets
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CHECKS = ROOT / "checks"
LEGACY_REPO = Path(os.environ.get(
    "ORIENT_SESSIONS_REPO", Path.home() / "Coding_Projects" / "session-files"))
sys.path.insert(0, str(ROOT))
from chain import append  # noqa: E402


def legacy_spoken_key(name, witness):
    r = subprocess.run(["git", "-C", str(LEGACY_REPO), "show",
                        f"{witness['commit']}:{witness['session_path']}"],
                       capture_output=True)
    if r.returncode != 0:
        raise SystemExit(f"cannot read transcript at {witness['commit'][:12]}")
    m = re.search(rf"orient-key-{re.escape(name)}-[0-9a-f]{{24}}",
                  r.stdout.decode("utf-8", "replace"))
    if not m:
        raise SystemExit(f"spoken key for {name} not found in "
                         f"{witness['session_path']}@{witness['commit'][:12]}")
    return m.group(0)


def minted_key(name, mint_path):
    env = json.loads((ROOT / "sessions" / mint_path).read_text())
    key = (env.get("keys") or {}).get(name)
    if not key:
        raise SystemExit(f"mint {mint_path} stamps no key for {name}")
    return key


def crypt(data, key, decrypt=False):
    cmd = ["openssl", "enc", "-aes-256-cbc", "-a", "-pbkdf2", "-pass",
           f"pass:{key}"]
    if decrypt:
        cmd.insert(2, "-d")
    r = subprocess.run(cmd, input=data, capture_output=True)
    if r.returncode != 0:
        raise SystemExit("openssl layer failed")
    return r.stdout


def main():
    args = sys.argv[1:]
    if not args:
        raise SystemExit(__doc__)
    name = args[0].upper().removesuffix(".SH")
    opt = {args[i][2:]: args[i + 1]
           for i in range(1, len(args) - 1) if args[i].startswith("--")}
    signer = opt.get("signer", "unknown")

    enc_f = CHECKS / f"{name}.sh.enc"
    wit_f = CHECKS / f"{name}.witness.json"

    if "key" not in opt:
        print(f"orient-key-{name}-{secrets.token_hex(12)}")
        return

    if "minted-session" in opt:
        witness = {"signer": signer,
                   "spoken_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                   "minted_session": opt["minted-session"]}
    else:
        witness = {"signer": signer,
                   "spoken_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                   "session_repo": "RecursiveRabbit/session-files",
                   "session_path": opt["session-path"],
                   "commit": opt["commit"]}

    if enc_f.exists():
        w = json.loads(wit_f.read_text())
        blob = enc_f.read_bytes()
        for prior in reversed(w["witnesses"]):  # peel outermost first
            if "minted_session" in prior:
                k = minted_key(name, prior["minted_session"])
            else:
                k = legacy_spoken_key(name, prior)
            blob = crypt(blob, k, decrypt=True)
        if hashlib.sha256(blob).hexdigest() != w["sha256"]:
            raise SystemExit(f"{name}: plaintext does not match ratified "
                             "sha256 — refuse to countersign")
        blob = crypt(blob, opt["key"])  # our layer goes outermost
        w["witnesses"].append(witness)
    else:
        src_f = Path(opt.get("src", CHECKS / "src" / f"{name}.sh"))
        src = src_f.read_bytes()
        w = {"check": name, "sha256": hashlib.sha256(src).hexdigest(),
             "witnesses": [witness]}
        blob = crypt(src, opt["key"])

    enc_f.write_bytes(blob)
    wit_f.write_text(json.dumps(w, indent=1) + "\n")
    key_f = CHECKS / f"{name}.key"
    key_f.write_text(json.dumps({
        "check": name,
        "key_id": opt["key"],
        "note": ("The key is not here. It was spoken aloud in the witness "
                 "session and stamped into its mint envelope. Read the "
                 "record; the record is the unlock."),
        **{k: witness[k] for k in
           ("minted_session", "session_repo", "session_path", "commit")
           if k in witness}}, indent=1) + "\n")
    for f in (enc_f, wit_f, key_f):
        h = append("check", str(f.relative_to(ROOT)),
                   {"check": name, "signer": signer})
        print(f"minted {h[:12]} {f.name}")


if __name__ == "__main__":
    main()
