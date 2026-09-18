#!/usr/bin/env python3
"""
sign — the witness act. Not part of the core; any session may write its own.

  sign.py NAME --signer WHO --session-path P --commit C [--key K] [--src FILE]

Encrypts the check source with the witness key (layered outermost over any
prior signatures), writes checks/NAME.sh.enc, updates checks/NAME.witness.json,
writes checks/NAME.key (a pointer to the session transcript at a specific
commit), and mints all three artifacts into the chain.

THE SOURCE IS NOT STORED. --src points at a transient file (a temp file, a
heredoc, /dev/stdin) that exists for the duration of the signing and is then
gone. To read a check's code later, decrypt the artifact with the spoken key
from the transcript — the record is the only source. A check without its
session file is static; it cannot run and it cannot be read.

Flow for a signer:
  1. sign.py NAME --signer WHO            # prints a fresh key
  2. speak the key aloud in your session
  3. commit your session file; note the commit hash
  4. sign.py NAME --signer WHO --key K --session-path P --commit C --src FILE
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
SESSIONS = Path(os.environ.get("ORIENT_SESSIONS_REPO",
                               Path.home() / "Coding_Projects" / "session-files"))
sys.path.insert(0, str(ROOT))
from chain import append  # noqa: E402

KEY_RE = "orient-key-{name}-[0-9a-f]{{24}}"


def spoken_key(name, witness):
    r = subprocess.run(["git", "-C", str(SESSIONS), "show",
                        f"{witness['commit']}:{witness['session_path']}"],
                       capture_output=True)
    if r.returncode != 0:
        raise SystemExit(f"cannot read transcript at {witness['commit'][:12]}")
    m = re.search(KEY_RE.format(name=re.escape(name)),
                  r.stdout.decode("utf-8", "replace"))
    if not m:
        raise SystemExit(f"spoken key for {name} not found in "
                         f"{witness['session_path']}@{witness['commit'][:12]}")
    return m.group(0)


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

    witness = {"signer": signer,
               "spoken_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
               "session_repo": "RecursiveRabbit/session-files",
               "session_path": opt["session-path"],
               "commit": opt["commit"]}

    if enc_f.exists():
        w = json.loads(wit_f.read_text())
        blob = enc_f.read_bytes()
        for prior in reversed(w["witnesses"]):  # peel outermost first
            blob = crypt(blob, spoken_key(name, prior), decrypt=True)
        if hashlib.sha256(blob).hexdigest() != w["sha256"]:
            raise SystemExit(f"{name}: plaintext does not match ratified "
                             "sha256 — refuse to countersign")
        blob = crypt(blob, opt["key"])  # our layer goes outermost
        w["witnesses"].append(witness)
    else:
        if "src" not in opt:
            raise SystemExit("first signature needs --src FILE (a transient "
                             "file; the source is not stored)")
        src = Path(opt["src"]).read_bytes()
        w = {"check": name, "sha256": hashlib.sha256(src).hexdigest(),
             "witnesses": [witness]}
        blob = crypt(src, opt["key"])

    enc_f.write_bytes(blob)
    wit_f.write_text(json.dumps(w, indent=1) + "\n")
    key_f = CHECKS / f"{name}.key"
    key_f.write_text(json.dumps({
        "check": name,
        "key_id": opt["key"],
        "note": ("The key is not here. It was spoken aloud in the session "
                 "transcript at this commit. Read the transcript; the "
                 "record is the unlock."),
        "session_repo": witness["session_repo"],
        "session_path": witness["session_path"],
        "commit": witness["commit"]}, indent=1) + "\n")
    for f in (enc_f, wit_f, key_f):
        h = append("check", str(f.relative_to(ROOT)),
                   {"check": name, "signer": signer})
        print(f"minted {h[:12]} {f.name}")


if __name__ == "__main__":
    main()
