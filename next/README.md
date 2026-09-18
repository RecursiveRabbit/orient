# next/ — proposed second generation (unratified, unminted, awaiting review)

Evans, 2026-09-18: "Build it into the check. A newly oriented session should
get an open ssh connection to the z620 and to vultr. One of the first checks
opens that connection and returns the data needed to access it. Any check can
take any previously written check's output as input. The connection is surfaced
to the agent, who begins the session already connected — or knowing they can't."

And, on chain semantics: correcting a check breaks the chain; a modification is
a whole new check that must be ratified by a second session. Therefore nothing
minted is modified. This directory is where the correction lives instead.

## What changed vs the minted core (orient.py @ chain seq 2)

`render()` gains one substitution rule — a check may consume an earlier
check's output:

    "$RAS conn=$CONNECT_Z620"

- `alias=NAME` on a slot names its output for later reference.
- `$ALIAS` inside an arg substitutes that output and word-splits into argv
  (a connection string like `up ctl=... target=...` arrives as separate
  key=value tokens).
- Evaluation order is template order; references point upward.

Everything else is byte-identical to the minted core.

## What changed in checks/src/ (unminted working materials)

- New: `CONNECT.sh` — opens/reuses a ControlMaster socket per host
  (`/tmp/orient-ssh-<host>`), returns `up host ctl target` or `down ...`.
  Measured: 0.2 s cold open, 11 ms warm probes (was 1.1 s per probe cold).
- DATE, UNAME, FILESYSTEM, RAID, SMART, RAS, DNSMASQ accept `ctl=`/`target=`
  args and ride the shared connection; missing connection renders `down`.
- template-next.json puts `connections` first; z620 checks take
  `conn=$CONNECT_Z620`.

## The open mechanics question (for the review session)

A corrected check is a new check — but sign.py writes artifacts to fixed paths
(`checks/DATE.sh.enc`), and those paths are minted. Re-signing corrected
content would overwrite minted evidence and break the chain. So sign.py needs
generations: first mint `DATE.sh.enc`; correction mints a NEW artifact path
(e.g. `DATE.g2.sh.enc` + its own witness set), the template points at the
newest ratified generation, and old artifacts stay byte-immutable forever.

Same question applies to the core itself: this directory is one answer
(generation = directory). If the core is adopted, how does the runner name
resolve? Symlink, rename, or `orient.py` becomes a dispatcher — reviewer's
call. The chain never lies either way.

## State

- Chain green at head cdc40f25f01d after restore commit (see git log).
- First batch back at 1/2 (builder's witness intact, artifacts restored).
- New/changed checks here carry NO artifacts yet — signing follows the
  authoring session's transcript filing (witness: Sexton, discord session
  2026-09-18; keys spoken in that transcript).
