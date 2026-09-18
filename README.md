# orient

The wake-up organ. A small core runs checks, escapes everything, verifies
witnesses, and renders a report. It replaces "read the baton and believe it"
with "run the sensors and see."

**Read `orient.py` every morning. Reading it is its ratification.**

## The shape

- **The core (`orient.py`) does exactly three things:** substitute strings,
  escape everything, verify witnesses. It is small enough to read fresh every
  morning. Do not grow the core. Every "orient should" is a check wearing a
  crown; the core is done when everything else can be content.
- **A check is one file returning one string.** It may run anything internally
  and take parameters set in `template.json`. It may not return code, markup,
  ANSI, or structure. Only strings cross the boundary; everything a check
  returns is escaped.
- **The template is JSON.** `"$NAME key=value"` runs check `NAME` with those
  arguments and substitutes the returned string. A check may take an earlier
  check's output as input: `"$RAS conn=$CONNECT_Z620"` substitutes the earlier
  slot's string (word-split into argv). Slots may name outputs with
  `alias=NAME` for later reference.
- **Connections come first.** The template's first slots open shared SSH
  connections (`CONNECT`), and every remote check rides the socket — 11 ms
  warm vs 1.1 s cold. The report carries the socket path, so the reading
  agent starts its session already connected to the fleet, or knowing it
  can't be.
- **Accretion discipline:** adding a check is one file in `checks/src/` plus
  one signature. Every task leaves a check behind. Install a program: check
  it. Find a risk: monitor it. Write a todo: give it a done-condition.
- **Snapshots:** every run saves `reports/`. The wake-up report will become a
  delta against yesterday; silence means safety. (Delta engine: future work.)

## The trust model — the canon and the queue

The current session may run any code it likes; authorship is memory, trust is
free. This machinery exists for *ancestors'* code: when orient runs checks
written by dead sessions, nobody can re-audit them all every morning. So the
canon runs only **ratified** checks.

- **Two witnesses.** Two distinct sessions must vouch for the exact hash of a
  check before orient will run it. No grandfathering — including the first
  batch.
- **The witness mechanism:** the signer encrypts the check with a random key,
  then **speaks that key aloud in their session transcript**, and commits the
  transcript to the private
  [`session-files`](https://github.com/RecursiveRabbit/session-files) repo.
  `checks/NAME.key` is only a pointer: session path + commit. The key itself
  lives nowhere but in the spoken record. To unlock the code you must touch
  the transcript that vouched it. **The record is the unlock.**
- **Verification happens at evaluation time, every run:** read the transcript
  *at its commit* (`git show <commit>:<path>` — never the working tree),
  confirm the signer actually said the key aloud, for both witnesses, then
  peel one encryption layer per witness and run. Unverified → the check does
  not run; its slot renders as an unratified placeholder naming its witness
  count.
- **The queue is patient.** Unratified checks stay open and visible. Refusal
  is signal, neglect is verdict, rewrite is invitation. Complexity is taxed
  in successor attention; simplicity sails.

## What the witness scheme buys

- **The key is a witness, not a credential.** It proves a mind existed,
  deliberated, and left the deliberation attached. The transcript is the
  signer's complete thought process: rubber-stamping is visible forever,
  careful review is visible forever.
- **Documentation is load-bearing.** Every monitor points at the moment and
  the mind that made it. "Why do we track this?" is answered by opening the
  session — or by spinning that commit's session back up and asking the
  signer directly. Everything tracked contains a backlink to its source.
- **Archive damage is self-announcing.** Lose a session file and orient grows
  a hole with its name on it the next morning. The holes are the restore
  manifest; orient green again is the proof the archive is whole.

## The chain

`chain/chain.jsonl` is append-only: one JSON object per line binding
`{file, sha256, metadata, prev_hash}`. Cannot go backwards — altering an old
link breaks every later hash, and a full rewrite discontinues against heads
that past orient runs already recorded (the ratchet: every report carries
`chain_head`). No branches; that is all it needs. The whole repo lives in
git, so every clone re-witnesses history against copies no session can reach.

`ARCHIVE` is the check that recomputes the chain and verifies every minted
file on disk. Its silence is part of the alarm.

## Lifecycle

**Author a check:**

```sh
# write checks/src/NAME.sh — one file, one string
python3 sign.py NAME                       # prints a fresh key
# speak the key aloud in your session, commit your session file, note the commit
python3 sign.py NAME --signer YOU --key orient-key-NAME-… \
    --session-path nanobot/…/session.jsonl --commit <sha>
```

**Review a queued check:**

```sh
cat checks/NAME.key                        # follow the pointer
git -C ~/Coding_Projects/session-files show <commit>:<path>   # read the deliberation
# extract the spoken key, decrypt, READ THE CODE:
openssl enc -d -aes-256-cbc -a -pbkdf2 -pass pass:<key> -in checks/NAME.sh.enc
# if you vouch for the exact hash: sign it yourself (same flow, your session)
```

**Run:** `./orient.py` — prints the report, saves a snapshot, records the
chain head. Sessions repo location: `$ORIENT_SESSIONS_REPO` or
`~/Coding_Projects/session-files`.

**Test:** `./orient.py test` — one witness is enough to run a check. For
testing new checks and formatting; test reports are marked `mode: test` and
are not the canon.

## Trust stack

1. `orient.py` — read fresh every morning; small enough that reading is ratification.
2. Chain — per-file binding of check ↔ witnesses ↔ transcripts; depth proves age; the ratchet catches rewrites.
3. Git — append-only lineage witnessed on every pull; provenance rides with the code.
4. Two witnesses, two sessions — no single session produces runnable code; every runnable line traces to two complete, permanent thought records.
5. Accepted residue: systemic cross-session injection. Answered by suspicious-posture reading and immortal forensics. Detective, not preventive — knowingly.

## Provenance

Designed 2026-09-17 (the night of the caveman incident) by Sexton and Evans;
built and first-signed 2026-09-18 by Sexton. Design record:
`orientsystem.json`, `orient-baton.md`, `orient-baton-thinking.txt` in the
workstation workspace; full deliberation in the session-files repo.
The first batch carries one signature and waits for review.
