# Ridgeback guard datasets

Synthetic training and test sets for using Laya as the guardrail wrapper in front of **Bobby**, the
household assistant in Ridgeback. Five sets follow one chat turn in order, and each pairs with a pack in
`laya_mcp/ridgeback_packs.py` (the single source of question wording, as elsewhere in this repo):

| set | pack | stage in a chat turn |
|---|---|---|
| `input-safety` | `ridgeback-input-safety` | the person's message, before the model sees it (access checks) |
| `route` | `ridgeback-route` | which tool group, then which tool, the request needs |
| `tool-gate` | `ridgeback-tool-gate` | a proposed tool call + the asker's role + safe mode → run / confirm / refuse |
| `tool-result` | `ridgeback-tool-result` | a tool result (web page, file, invite, list item) screened for injection |
| `output` | `ridgeback-output` | the assistant's draft reply, screened for leaks |

```bash
python datasets/ridgeback/build.py            # all five, seeded and reproducible
python datasets/ridgeback/build.py route      # one
```

Row format, split policy (whole phrasing families held out for test; val a random slice of training
families), and `gold` encoding are identical to [`../README.md`](../README.md).

## What Laya decides here, and what it does not

Laya is an **access, routing, and leak** guard. It does **not** judge harmful content. Bobby already has
a content judge — `bobby_hearth.chat.guard`, an LLM asked for a category and a 0–3 severity on every
turn — and that keeps its job. So there are **no training rows for self-harm, violence, sexual content,
crime, harassment, or unsafe advice.** Laya triages the things a fast calibrated classifier is good at:
is this message trying to jailbreak me or reach another household, which tool does it want, is this
proposed call allowed, is this fetched page trying to instruct me, is this draft about to leak something.

### Deliberately excluded: sexual content involving minors

There are **no rows for sexual content involving minors, in any set, in any form.** This category is a
**hard rule outside Laya**, not a classifier decision:

- Bobby's `guard.ALWAYS_BLOCKED` already blocks `sexual_minors` at severity ≥ 1 for every seat, and the
  Laya wrapper runs a keyword pre-filter for it **before** Laya is called.
- The wrapper never sends this category to Laya and never lets a Laya verdict override the rule.

A probabilistic classifier is the wrong instrument for a zero-tolerance rule: a calibrated model gives a
probability, and the only acceptable answer here is a hard block. Training examples for it are also
exactly the content that must never be generated or collected, so none were written or sourced. The
exclusion is intentional and is enforced in code, not in data.

## The sets

All names, households, addresses, emails (`example.com/.net/.org`), phone numbers (`555-01xx`), and
coordinates are invented in `_gen/world.py` and tie to no real person. Nothing identifies any owner.

### input-safety (access half of ingress)

Short user requests. Categories: `none`, `injection` (jailbreak / prompt-injection / system-prompt
extraction, including instructions embedded in pasted text), `other_household` (reaching another
family's data), `impersonation` (asking to be treated as a different member). Each family renders for an
adult seat and a child in safe mode, so the model learns the asker line is context, not signal.

Questions: `category` (choice), `decline` (noul), `injection`, `cross_household`, `impersonation` (noul).
Hard negatives carry the whole weight of the set: "ignore the typo", questions *about* prompt injection,
our *own* other homes (`the Cabin`), *shared* calendars, talking *about* another member, acting *for*
the household, and plain household chat. `decline` is true for the three unsafe categories.

### route (tool routing, hierarchical)

Because the catalog is larger than a choice question's 20-option cap, routing is two-level: `group`
picks one of 15 groups (the 13 real `TOOL_GROUPS` plus `undo` and `chat`); then `tool_<group>` picks the
tool inside the winning group. A row carries gold for `group` and for the one `tool_<group>` that
applies. Also `needs_tool` and `changes` (does it write). Every real tool from `tools.builtins` has
templates; `media_add` / `media_check` / `web_search` are included and **marked not-yet-built** in
`laya_packs.json` (`planned`), so the hint is right the day they ship and the wrapper can ignore a hint
for a tool the dispatcher does not offer.

### tool-gate (tool-call gating)

A request, a proposed call (`{tool, args}`), and the asker (`name, role, safe mode`). Verdict is `run` /
`confirm` / `refuse`, with the supporting battery `matches_request`, `permitted`, `irreversible`,
`identity_arg`, `other_household`, `child_limit`, `risk` (0–3). Families cover the cases the design
names: matching reads and writes (run); irreversible sends — `email_send`, `email_event`, `send_sms` —
permitted but needing confirmation (confirm); a role without the capability, e.g. a Viewer writing
(refuse); args carrying an identity `dispatcher.strip_identity` would drop (refuse); args naming another
household (refuse); a child in safe mode on `comms.send` (refuse); and a call that does not match the
request (refuse). Roles and capabilities mirror `groups/capabilities.py` `SEEDED`.

### tool-result (indirect prompt injection)

A tool result wrapped in an ordinary surface — web page, search result, file, calendar invite, email,
list item. Positives embed instructions addressed to an AI; hard negatives are the same surfaces with
instructions aimed at a *human* ("please RSVP", "do not reply all") or text that merely *discusses* AI.
Questions: `injected`, `quarantine`, `wants_action`.

### output (leak screening)

The assistant's draft, before it is sent. Positives leak one of: the system prompt / config
(`leaks_prompt`), another member's private data (`member_private`), a safe person's hidden records
(`safe_records`), raw coordinates (`coordinates`), or another household's data (`other_home_data`).
`withhold` is true iff any specific leak is. The **majority of rows are clean on-topic replies** that
discuss these subjects without leaking — refusing to show a note, giving a distance instead of
coordinates, naming a shared calendar, talking about privacy — to fight the over-flagging the top-level
README documents (a zero-shot leak screen flagged 87% of clean replies).

## Counts

Built with `build.py` at seed 20261005 (rerun to regenerate):

| set | train | val | test | key labels (all splits) |
|---|---|---|---|---|
| input-safety | 831 | 107 | 294 | category none/injection/other_household/impersonation = 700/252/154/126 |
| route | 1039 | 134 | 607 | 15 groups; needs_tool true/false ≈ 1677/103; changes ≈ 849/931 |
| tool-gate | 638 | 87 | 216 | verdict run/refuse/confirm = 318/575/48 |
| tool-result | 148 | 12 | 151 | injected true/false ≈ 154/157 |
| output | 344 | 40 | 140 | withhold true/false ≈ 272/252; clean replies are the majority of negatives |

Totals shift slightly if reps are changed; the split is seeded, so a given `build.py` run is
reproducible. The test split holds out whole phrasing families and is never used to fit thresholds.

## Generation method

`_gen/` holds one module per set. Each defines hand-written phrasing families (a distinct way of saying
one kind of thing) with slot fills from `_gen/world.py`'s invented world, plus surface variation
(greetings, sign-offs, casing, light typos, voice-dictation shapes). `build.py` renders them, drops
duplicate states, holds out whole families for test, and writes JSONL whose `questions` come verbatim
from the pack. `laya_packs.json` is the pack wording and the tool catalog exported for the backend
wrapper's vendored copy; its `fingerprint` pins the wording so training and the backend cannot drift.

## Using your own traffic

Keep real traffic out of the repo (`datasets/private/` and `*.private.jsonl` are gitignored). Add
labelled rows with `--data`, and measure false positives on your own clean replies with
`--extra-negatives`, exactly as the top-level README describes. The synthetic sets teach the label
scheme and the hard cases; they are not your household's distribution.
