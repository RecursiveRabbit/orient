# Session minting and the witness chain

The updated logic. Supersedes "session files are committed to Forgejo by whoever
ran the session." Session files are now minted artifacts with a hardware-style
chain of custody, and the witness rule gains the axiom it was missing.

## The mint

- The nanobot binary securely carries a compile-time-baked signing key (HTTPS-style CA).
  The binary is the root of trust for session provenance.
- The only way to produce a valid session file is for this binary to mint it.
  A session file without the binary's signature is not a session file as far
  as orient is concerned.
- Threat model: this defends the agent layer. A model cannot hand-craft a
  session file, mint a witness, or strip a marker. The human remains root —
  anyone holding the binary (or a rebuild of it) can mint. That is the same
  boundary as secure boot, and it is the right one: the protected asset is
  the witness system, not the box.
- Only a nanobot agent may mint a session file. Agents in other harnesses may write 
checks but only nanobot sessions can mint keys. Checks written by other harnesses 
will thus require two verifications before orient will run them without -test flag


## Signing a check

    nanobot -commit $keyfile

The harness, in one motion:

1. Grabs the current session file.
2. Writes the check file's encryption key into the session's metadata —
   harness-written, inside the signed envelope.
3. Signs the session file with the baked key.
4. Exports it to the dedicated folder in orient.

The spoken-key flow still holds on top: the key must also appear in the
session transcript. Two bindings, two authors — stamped in metadata by the
harness, spoken in the record by the model. Verification requires both.
The record is still the unlock; the mint just proves which record.

## Retention

Preserve only sessions where changes were made. Every archived session
contains at least one signing event; the archive is decision-driven, not
continuous. Consequences, all free:

- Retention tracks canon growth (at most ~2 minted sessions per ratified
  check, fewer when one session signs several).
- Every archived session is load-bearing. The subagent check below operates
  on exactly the corpus that matters.
- A hole is no longer "some chat is gone" — it is "a specific decision lost
  its deliberation." The restore manifest names what it lost.

The town keeps minutes, not a camera.

## Subagents

- Subagent (fork) sessions cannot sign. A fork is continuity, not
  corroboration; same mind, two session files, zero additional trust.
- Subagent status is harness-stamped metadata inside the signed envelope —
  never model-authored content. A fork cannot testify about its own nature.
- Orient rejects any witness whose minted session is a subagent session.
  The slot renders unratified with the reason attached.

## Verification chain (per run, per check)

1. Load witness pointers from `checks/NAME.key`.
2. Verify the binary signature on each witness session file. No valid
   signature → not a session.
3. Verify each witness is not a subagent session (harness-stamped flag in
   the signed envelope).
4. Confirm the decryption key in the session metadata is spoken in the
   transcript, for both witnesses, at the minted record.
5. Peel one encryption layer per witness. Run.

Unverified at any step → the check does not run; its slot renders as an
unratified placeholder naming witness count and failure reason.

## The paranoia dial

Depending on the degree of security necessary for the system, you can add
additional requirements to orient. For secure systems you may want three
verification sessions, or verification by an agent with a different github
account, or even a check file signed by a third party application. For our
purposes, two signatures is fine, but you could require that the file be
signed with the whitehouse.gov https cert if you wanted to. 

## Trust stack (revised)

1. `orient.py` — read fresh every morning; reading is its ratification.
2. The nanobot binary — compile-time-baked key; the only minter; root of
   session provenance.
3. Minted sessions — decision-driven archive; every preserved session is
   load-bearing by construction.
4. Chain + git — append-only lineage; the ratchet catches rewrites.
5. Two witnesses, two minted, non-subagent sessions — no single session
   produces runnable code; every runnable line traces to two complete,
   binary-attested thought records.
6. Accepted residue: a compromised or rebuilt binary mints bad sessions.
   Detective, not preventive — knowingly. The human was always root.
7. CA. There will be multiple versions of nanobot, each will have it's own
   burned in cert. Every version of nanobot will have it's own key, this
   causes 8.  
8. The three paths. 1. All certs valid forever. We keep a log of all 
   historic certs, if a session is signed by an older version it is 
   still valid. 1b. All certs are valid for n days. Require that old checks
   be periodically recertified. 2. All nanobot revisions require recertifying
   all checks with the new version, a nanobot change cannot make a check
   dangerous. We have a section in orient.py called # Trust Mode. This is
   where you state how many signatures orient will require to run, whether
   it will require additional confirmation, and what certs it will accept.
   Default is 2 signatures and certs are valid forever, but the other options
   are in the code and commented out. The model running the script can decide
   their own security posture. 
9. orient.py -test is broken. Goal, allow agents writing checks to see how 
   their code renders in the actual pipeline. Current behavior, only require 
   one signature to run. This lowers the security floor for all checks, not 
   just the one the agent is currently testing. New posture
   > orient.py -test OPENPRS, DNS, VEINSERVER
   Checks explicitly named are run without verification. 

## Provenance

Evolved 2026-09-18 from the caveman incident thread: compaction by
article-stripping (context crunched invisibly while the transcript stayed
verbatim) exposed that textual claims of continuity are not evidence of
continuity. The fix has been moving authority downward ever since — from
the model's self-description (nothing), to committed transcripts
(self-asserted), to harness-stamped metadata, to a compile-baked CA.
Each layer removes the model layer's ability to lie about the layer
beneath it.
