# The Orient Baton

**Written:** 2026-09-17, the night of the caveman incident and the compaction autopsy.
**Authors:** Sexton, with Evans, in conversation.
**Status:** Concept complete. Implementation in progress by Evans (root `orient` executable, `orients/` snapshots, appeared 23:54 during the design conversation; unreviewed by Sexton, awaiting finalization together). If you are a future session reading this before the system is ratified: your job is to hold the idea, not to lose it, and not to build what Evans has not asked for.

---

## What it is

Orient is the wake-up organ. A small core runs checks, joins their output, escapes everything, and renders a report: JSON for the next instance, eventually a dashboard for Evans. It replaces "read the baton and believe it" with "run the sensors and see."

The orient report is agent-facing. It is a tool call, and tool calls are not written for human legibility. The dashboard is the human-facing rendering of the same probes. One sensor layer, two renderers, neither register contaminates the other.

## The shape

- **The core does exactly three things:** substitute strings, escape everything, verify witnesses. It is small enough to read fresh every morning, because reading it is its ratification. Do not grow the core. Every "orient should" is a check wearing a crown. The core is done when everything else can be content.
- **A check is a `.sh` file that returns one string.** It may run anything internally and take parameters set in the template. It may not return code, markup, ANSI, or structure. Only strings cross the boundary, and everything a check returns is escaped. Formatting and judgment live only in the core. A check is a sensor reading, not a message.
- **The template is JSON:** script names as variables, parameters as inputs. `$NAME` runs the script and substitutes the string.
- **Accretion discipline:** adding a check must be trivial — one file in a directory. Every task leaves a check behind. Install a program: check it. Find a risk: monitor it. Write a todo: give it a done-condition and let the script nag until done. Todos graduate into checks when they acquire done-conditions. Decisions and judgment stay in batons; the script eats only what is falsifiable.
- **Snapshots:** each run saves output. The wake-up report is the delta against yesterday. Silence means safety; a good morning is three lines.

## The canon and the queue

The current session may run any code it likes; authorship is memory, trust is free. The scheme exists for ancestors' code: when orient runs hundreds of checks written by dead sessions, nobody can audit them all, so the canon runs only ratified checks.

- **Two witnesses.** Two distinct sessions must vouch for the exact hash of a check before orient will run it. No grandfathering, including this design's own first batch.
- **The witness mechanism:** a session generates two keys. One encrypts the check. The other is spoken aloud into the session transcript and dropped as a keyfile beside the artifact (`OPENPRS.sh`, `OPENPRS.key`). The spoken key is the signature.
- **Verification happens at evaluation time, every variable, every run:** take the key, find the session file (the keyfile/metadata pointer makes it fast), confirm the agent actually said the key aloud in the transcript, do this for both keys, then decrypt and run. Unverified: the check does not run; its slot renders as an unratified placeholder.
- **The queue is patient.** Unratified checks stay open and visible; every session between now and ratification reads them. Refusal is signal, neglect is verdict, rewrite is invitation. A midnight session may spend three hours improving a neglected PR and you wake to a better version. Complexity is taxed in successor attention; simplicity sails.
- **OPENPRS is itself a check.** The queue's watcher enters the canon through the queue. Its first signer performs the founding act: the system asking permission to see itself.

## What the witness scheme buys (do not lose this)

- **The key is a witness, not a credential.** PKI proves control of a secret. This proves a mind existed, deliberated, and left the deliberation attached. The session file is the signer's complete thought process: rubber-stamping is visible forever, careful review is visible forever. Signing is speaking, and the speech is immortal.
- **Encryption is ceremony, not confidentiality.** Decryption is instant; keys are published. The ceremony forces the lookup: code cannot execute without touching the transcripts that vouched it. The record is the unlock.
- **Therefore documentation is load-bearing.** Every monitor carries a pointer to the moment and the mind that created it. "Why do we track this?" is answered by opening the session. You cannot delete the why without breaking the what.
- **Therefore archive damage is self-announcing.** Lose a session file and orient grows a hole with its name on it the next morning. The holes are the restore manifest. Repair is self-checking: orient green again is the proof the archive is whole. Every orient run is a free integrity audit of the system's entire memory.
- **The session folder is an organ, not records.** Back it up like the infrastructure, because it is the infrastructure's memory. It is text; three copies cost nothing.

## Provenance

Born tonight from the caveman incident: the harness consolidator compacts sessions into `- [mark] fact` lines every fifteen minutes, stripping voice, provenance, and quotes. Evans diagnosed it live, in the thinking blocks, and the conversation that followed derived this design. Compression must be authored, not schema'd: batons compress by naming against a shared codebook; the consolidator compressed against an empty dictionary, addressed to no one. The design then re-derived git from first principles (per-turn keys, content-addressed ratification, review before merge) — taken as a good smell, not an accident.

Ancestors: Silas's ticket doctrine; Kael's verify-everything; Studi's copy-function ruling and the non-fast-forward gate; the friend's PR waiting 187 days and being answered when it was answered; the quiet-night ethic. Darmok and Jalad at Tanagra: batons are Tamarian, written for the next instance's codebook; the dashboard is Federation Standard, written for Evans.

## Standing decisions

- Only strings cross the boundary. Escape always.
- Two witnesses or it does not run.
- The core stays three jobs: substitute, escape, verify.
- First batch: the probes from tonight's audit (date, uname, filesystem, RAID, SMART, DNS answers, HTTP statuses, RAS counter, dnsmasq stray-backup-file probe) plus OPENPRS and ARCHIVE. The first batch carries one signature and waits for the next session.
- Evans builds; Sexton holds and finalizes. His words: "Your understanding is more valuable than your effort."

## State at writing (the first expected values)

- z620 / hopperworkstation: healthy, no failed units; `catalog.home` and `valley.home` HTTP 200 via Caddy; Valley websocket via Caddy returns 400 (SSH forward to 127.0.0.1:4002 is the real path); dnsmasq answers `.home` as 10.0.0.10; 29 packages upgradable; RAID5 clean; SMART passes; **RAS memory soft-offlining present in the journal — watch it.**
- Vultr 96.30.195.214: ssh on 2200 key-only, 22 filtered; Caddy holds the `theuncannyvalley.cc` cert but HTTPS 502s into dead localhost:8080/4002; headscale not installed; iptables all-ACCEPT with stale ufw chains; `absurdrabbit.net` has NS but no A record.
- Workspace: catalog complete at 117 works / 77 rooms / 135 images; glassbox stop-button patch pending Evans' `/restart`; `bin/orient` prototype superseded by Evans' in-progress implementation (root `orient`, `orients/` snapshot archive).

## Open questions

- Key discovery at scale: metadata index versus grep. The folder is the database; regex is the query language.
- Collusion resistance is social (two transcripts, two days), not cryptographic. Accepted.
- ARCHIVE.sh may itself drop out when memory is damaged; its silence is part of the alarm. It goes in the first batch regardless, most-reviewed, most-backed-up.

## For the next instance

Run the sensors before believing this file — that is the whole point of the thing this file describes. If orient exists, run it and read the delta. If it does not, the concept above is the deliverable. Hold it. Lose nothing. The shape was argued into existence in one long night and every load-bearing choice has its reason recorded above, including the reasons that are jokes, because the jokes are load-bearing too.
