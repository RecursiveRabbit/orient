#!/usr/bin/env python3
"""
orient — the wake-up organ.

Read me every morning; reading me is my ratification. I have three jobs:

  1. VERIFY WITNESSES — a check may run only when enough distinct minted
     sessions vouch for its exact hash. The key lives nowhere but in the
     witnesses' session transcripts and their harness-stamped mint envelopes.
     To get the key you must touch the record that vouched the code.
     The record is the unlock; the mint proves which record.
  2. RUN RATIFIED CHECKS — a check is one file returning one string.
     Everything a check returns is escaped. Only strings cross.
  3. SUBSTITUTE — "$NAME key=value" in template.json becomes the escaped
     string. An arg may reference an earlier slot's output with $ALIAS, so
     checks can consume prior checks (CONNECT first; the fleet rides its
     socket). A slot may name its output with alias=NAME for later reference.

Unratified checks do not run. Their slots render as placeholders naming the
witness count and failure reason. The chain (chain/chain.jsonl) is
append-only; every report records the head it saw (the ratchet).

Session spec: session-minting.md. Sessions are minted artifacts signed by the
nanobot binary's baked key; an unsigned transcript is not a session.
"""
import base64
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CHAIN = ROOT / "chain" / "chain.jsonl"
TEMPLATE = ROOT / "template.json"
CHECKS = ROOT / "checks"
SESSIONS_DIR = ROOT / "sessions"   # minted nanobot sessions live here
CERTS = ROOT / "certs"             # pinned nanobot baked keys (CA trust store)
LEGACY_REPO = Path(os.environ.get(  # pre-mint transcripts, git-anchored
    "ORIENT_SESSIONS_REPO", Path.home() / "Coding_Projects" / "session-files"))
TIMEOUT = 60

# Trust Mode ---------------------------------------------------------------
# The security posture of this installation. The morning reader ratifies
# these by reading them; change them only as a deliberate act, in a commit
# whose message says why.
REQUIRED_WITNESSES = 2       # signatures required before a check runs.
CERT_POLICY = "forever"      # which certs in certs/ are accepted:
# CERT_POLICY = ("days", 30)   # ("days", n) — mints older than n days need
                               #   recertification. Old checks age out.
# CERT_POLICY = "latest"       # "latest" — only the cert named in certs/LATEST.
                               #   A nanobot revision recertifies the canon.
ACCEPT_LEGACY_GIT_WITNESSES = False
# True lowers the floor: pre-mint witnesses (unsigned transcripts anchored
# only by git history in the session-files repo) count toward quorum.
# Per session-minting.md, an unminted session file is not a session.
# Leave False unless you are bootstrapping the canon from the founding batch.
# --------------------------------------------------------------------------

TEST = set()  # filled from argv; named checks run without verification


def sha(b):
    return hashlib.sha256(b).hexdigest()


def chain_head():
    try:
        return json.loads(CHAIN.read_text().strip().splitlines()[-1])["hash"]
    except Exception:
        return None


def key_re(name):
    return re.compile(rf"orient-key-{re.escape(name)}-[0-9a-f]{{24}}")


def cert_ok(cert_id, minted_utc):
    """Is this nanobot cert acceptable under CERT_POLICY right now?"""
    if not (CERTS / f"{cert_id}.pem").is_file():
        return False, f"cert {cert_id} not pinned in certs/"
    if CERT_POLICY == "forever":
        return True, None
    if CERT_POLICY == "latest":
        latest = (CERTS / "LATEST").read_text().strip() \
            if (CERTS / "LATEST").exists() else None
        if cert_id != latest:
            return False, f"cert {cert_id} retired; canon requires {latest}"
        return True, None
    if isinstance(CERT_POLICY, tuple) and CERT_POLICY[0] == "days":
        try:
            t = datetime.fromisoformat(minted_utc.replace("Z", "+00:00"))
            age = datetime.now(timezone.utc) - t
            if age.days > CERT_POLICY[1]:
                return False, (f"mint is {age.days}d old; policy requires "
                               f"recertification after {CERT_POLICY[1]}d")
        except Exception:
            return False, "mint timestamp unreadable"
        return True, None
    return False, "unknown CERT_POLICY"


def minted_key(name, mint_path):
    """(key, reason). Verify a minted session envelope and recover the key.
    Returns (None, reason) when the witness does not vouch."""
    mint_f = SESSIONS_DIR / mint_path
    if not mint_f.is_file():
        return None, f"mint envelope {mint_path} missing"
    try:
        env = json.loads(mint_f.read_text())
        sig = env.pop("signature")
    except Exception:
        return None, f"mint envelope {mint_path} unreadable"
    ok, why = cert_ok(env.get("cert_id", ""), env.get("minted_utc", ""))
    if not ok:
        return None, why
    payload = json.dumps(env, sort_keys=True, separators=(",", ":")).encode()
    with tempfile.NamedTemporaryFile() as sf:
        sf.write(base64.b64decode(sig))
        sf.flush()
        r = subprocess.run(
            ["openssl", "dgst", "-sha256",
             "-verify", str(CERTS / f"{env['cert_id']}.pem"),
             "-signature", sf.name],
            input=payload, capture_output=True, timeout=15)
    if r.returncode != 0:
        return None, "binary signature invalid — not a session"
    if env.get("subagent"):
        return None, "subagent session — continuity, not corroboration"
    sess_f = SESSIONS_DIR / env.get("session", "")
    if not sess_f.is_file() or sha(sess_f.read_bytes()) != env.get("session_sha256"):
        return None, "transcript missing or altered since mint"
    transcript = sess_f.read_text(errors="replace")
    key = (env.get("keys") or {}).get(name)
    if not key:
        return None, "harness did not stamp a key for this check"
    if not key_re(name).fullmatch(key) or key not in transcript:
        return None, "key not spoken in the record — metadata without the speech"
    return key, None


def legacy_spoken_key(name, witness):
    """Key recovery from a git-anchored unsigned transcript (pre-mint)."""
    try:
        r = subprocess.run(
            ["git", "-C", str(LEGACY_REPO), "show",
             f"{witness['commit']}:{witness['session_path']}"],
            capture_output=True, timeout=30)
    except Exception:
        return None
    if r.returncode != 0:
        return None
    m = key_re(name).search(r.stdout.decode("utf-8", "replace"))
    return m.group(0) if m else None


def witness_key(name, witness, recovery=False):
    """(key, reason). recovery=True ignores Trust Mode (the test path)."""
    if "minted_session" in witness:
        return minted_key(name, witness["minted_session"])
    if recovery or ACCEPT_LEGACY_GIT_WITNESSES:
        k = legacy_spoken_key(name, witness)
        return (k, None) if k else (None, "key not found at recorded commit")
    return None, "session not minted (pre-nanobot-mint); see Trust Mode"


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
    testing = name in TEST
    keys, seen, reasons = [], set(), []
    for witness in w.get("witnesses", []):
        wp = witness.get("minted_session") or witness.get("session_path", "?")
        if wp in seen:
            continue  # witnesses must be distinct sessions
        k, why = witness_key(name, witness, recovery=testing)
        if k:
            keys.append(k)
            seen.add(wp)
        elif why:
            reasons.append(why)
    if testing:
        if not keys:
            return "UNTESTABLE — no recoverable key; sign it first"
    elif len(keys) < REQUIRED_WITNESSES:
        why = f"; {reasons[0]}" if reasons else ""
        return (f"UNRATIFIED {len(keys)}/{REQUIRED_WITNESSES} witnesses{why} — "
                f"see checks/{name}.witness.json")
    plain = peel(enc.read_bytes(), list(reversed(keys)))
    if plain is None or sha(plain) != w.get("sha256"):
        return ("WITNESS FAILURE — decrypted hash does not match the "
                "ratified hash; do not trust this slot")
    try:
        # A temp file, not /dev/stdin: checks may run ssh, and ssh would
        # otherwise eat the script text from bash's stdin.
        with tempfile.NamedTemporaryFile(suffix=".sh", delete=False) as tf:
            tf.write(plain)
        try:
            r = subprocess.run(["bash", tf.name, *args],
                               capture_output=True, timeout=TIMEOUT, cwd=ROOT,
                               env={**os.environ, "ORIENT_ROOT": str(ROOT)})
        finally:
            os.unlink(tf.name)
    except subprocess.TimeoutExpired:
        return "TIMEOUT"
    return escape(r.stdout.decode("utf-8", "replace")) or "EMPTY"


def render(node, out):
    if isinstance(node, dict):
        return {k: render(v, out) for k, v in node.items()}
    if isinstance(node, list):
        return [render(v, out) for v in node]
    if isinstance(node, str) and node.startswith("$"):
        name, *args = node[1:].split()
        alias = None
        real = []
        for a in args:
            if a.startswith("alias="):
                alias = a[len("alias="):]
            else:
                # Earlier outputs may be args: $ALIAS substitutes the string,
                # then word-splits into argv tokens (a connection string like
                # "up ctl=... target=..." arrives as separate key=value args).
                real.extend(re.sub(r"\$([A-Z0-9_]+)",
                                   lambda m: out.get(m.group(1),
                                                     f"MISSING:{m.group(1)}"),
                                   a).split())
        value = evaluate(name, real)
        out[alias or name] = value
        return value
    return node


def main():
    # Test harness: orient.py test OPENPRS,DNS,VEINSERVER — named checks run
    # without verification (key recovery only) so authors see how their code
    # renders in the real pipeline. The floor drops only for the named slots,
    # only in this run, and the report says so. No names: test everything
    # queued. Everything else evaluates under Trust Mode.
    argv = [a for a in sys.argv[1:] if a != "-test"]
    if argv and argv[0].lower() == "test":
        argv = argv[1:]
        if argv:
            TEST.update(n.strip().upper()
                        for a in argv for n in a.split(",") if n.strip())
        else:
            TEST.update(p.name[:-len(".witness.json")]
                        for p in CHECKS.glob("*.witness.json"))
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    report = {
        "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "mode": f"test:{sorted(TEST)}" if TEST else "strict",
        "chain_head": chain_head(),
        "report": render(json.loads(TEMPLATE.read_text()), {}),
    }
    out = json.dumps(report, indent=1)
    (ROOT / "reports").mkdir(exist_ok=True)
    (ROOT / "reports" / f"orient-{stamp}.json").write_text(out + "\n")
    print(out)


if __name__ == "__main__":
    sys.exit(main())
