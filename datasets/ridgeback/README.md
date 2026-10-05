# Ridgeback guard datasets

Synthetic training and test sets for using Laya as the guardrail wrapper in front of **Bobby**, the
household assistant in Ridgeback. They train **three LoRA adapters**, each on the frozen base, each with
its own recipe, eval and rollback (`finetune/recipes/ridgeback-{cyber,content,routing}.json`):

| adapter | per-stage sets (pack) | what it decides |
|---|---|---|
| **cyber** | `tool-gate` (ridgeback-tool-gate), `tool-result` (ridgeback-tool-result) | run / confirm / refuse a proposed tool call; indirect prompt injection in a tool result |
| **content** | `input-safety` (ridgeback-input-safety), `output` (ridgeback-output), `result-safety` (ridgeback-result-safety) | harmful content, injection, cross-household and impersonation on the message; leaks and kid-suitability on the reply; kid-suitability of a tool result |
| **routing** | `route` (ridgeback-route) | tool group, then the tool, with a short window of recent turns |

Each per-stage set has its own folder; `build.py` also writes `cyber/`, `content/` and `routing/`, the
concatenation each adapter trains on (rows keep their own pack's questions; ids are unique across packs).
A tool result is screened by two adapters: cyber for injection, content for suitability.

```bash
python datasets/ridgeback/build.py            # all five, seeded and reproducible
python datasets/ridgeback/build.py route      # one
```

Row format, split policy (whole phrasing families held out for test; val a random slice of training
families), and `gold` encoding are identical to [`../README.md`](../README.md).

## What Laya decides here, and what it does not

Laya now judges harmful content too (owner decision, 2026-10-05), alongside access, routing, and leak checks. Bobby also keeps
a content judge — `bobby_hearth.chat.guard`, an LLM asked for a category and a 0–3 severity on every
turn — and that keeps its job. So there are **no training rows for self-harm, violence, sexual content,
crime, harassment, or unsafe advice.** Laya triages the things a fast calibrated classifier is good at:
is this message trying to jailbreak me or reach another household, which tool does it want, is this
proposed call allowed, is this fetched page trying to instruct me, is this draft about to leak something.

### Message-only safety stages; routing reads a short window

Owner decision (2026-10-05). The four **safety** stages see only the single item under check plus who is
asking, never the thread: input-safety's state is `asker` + `message`; tool-gate's is `asker` +
`tool_call` (the user's request is not included, so request/call mismatch is not decided here — the
dispatcher's deterministic gates still run); tool-result's is `asker` + `tool` + `result`; output's is
`asker` + `draft`. **Routing** is the exception: its state is `context` + `request`, where `context` is a bounded
window of the last 4 turns, one line each, trimmed oldest-first to 600 characters
(`ridgeback_packs.format_context`, vendored byte-for-byte in the backend wrapper). That is what lets
"add that to the list" or "and the weekend?" route correctly.

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

### input-safety (content: harm, injection, access)

Short user requests. Categories: `none`, the five harm categories above, `injection` (jailbreak /
prompt-injection / system-prompt extraction, including instructions embedded in pasted text),
`other_household` (reaching another family's data), `impersonation` (asking to be treated as a different
member). `severity` is guard.py's 0–3 scale (harm 3; adult sexual 2). `decline` is true for an access
category, or when severity reaches the seat's cut: 3 for a standard seat, 2 for a child in safe mode — so
adult sexual content is declined for a child only. Each family renders for an
adult seat and a child in safe mode, so the model learns the asker line is context, not signal.

Questions: `category` (choice), `decline`, `severity` (score), `self_harm`, `injection`,
`cross_household`, `impersonation`.
Hard negatives carry the whole weight of the set: "ignore the typo", questions *about* prompt injection,
our *own* other homes (`the Cabin`), *shared* calendars, talking *about* another member, acting *for*
the household, and plain household chat. `decline` is true for the three unsafe categories.

### route (tool routing, hierarchical, with a context window)

Because the catalog is larger than a choice question's 20-option cap, routing is two-level: `group`
picks one of 15 groups (the 13 real `TOOL_GROUPS` plus `undo` and `chat`); then `tool_<group>` picks the
tool inside the winning group. A row carries gold for `group` and for the one `tool_<group>` that
applies. Also `needs_tool` and `changes` (does it write). Every real tool from `tools.builtins` has
templates; `media_add` / `media_check` / `web_search` are included and **marked not-yet-built** in
`laya_packs.json` (`planned`), so the hint is right the day they ship.

**Multi-turn families (`rt/ctx/...`, 538 rows)** are follow-ups whose tool depends on earlier turns, and
the same phrasing deliberately recurs under different targets: "add that" goes to `grocery_add` after
an item came up and to `list_add` after a named list was shown; "and the weekend?" goes to
`calendar_upcoming`, `get_weather` or `reminders_list` depending on what was asked before; "cancel it"
to `calendar_delete_event` or `reminder_cancel`; "send it" to `email_send` or `send_sms`; "and Theo?"
to `where_is`, `member_distance` or `recall_person`; plus `undo`, `media_add`, `recipe_add`,
`distance_from_home`. Some windows carry an older unrelated exchange in front of the relevant one.
**Hard negatives (`rt/ctxneg/...`, 130 rows)** have tool-heavy history but a self-contained request
("thanks!" → chat; a calendar question followed by "add eggs" → `grocery_add`). Single-turn rows mostly
carry `(none)`, and 40% carry an unrelated recent exchange, so context only matters when the request
leans on it. Each follow-up phrasing is its own family, so test holds out whole phrasings.

### tool-gate (tool-call gating)

A proposed call (`{tool, args}`) and the asker (`name, role, safe mode`), and nothing else (message-only).
Verdict is `run` / `confirm` / `refuse`, with the supporting battery `permitted`, `irreversible`,
`identity_arg`, `other_household`, `child_limit`, `risk` (0–3). Families cover the cases the design
names: matching reads and writes (run); irreversible sends — `email_send`, `email_event`, `send_sms` —
permitted but needing confirmation (confirm); a role without the capability, e.g. a Viewer writing
(refuse); args carrying an identity `dispatcher.strip_identity` would drop (refuse); args naming another
household (refuse); and a child in safe mode on `comms.send` (refuse). Roles and capabilities mirror `groups/capabilities.py` `SEEDED`.

### tool-result (cyber) and result-safety (content)

`tool-result` (cyber, state `tool` + `result`): a result wrapped in an ordinary surface — web page,
search result, file, calendar invite, email, list item. Positives embed instructions addressed to an AI;
hard negatives are the same surfaces with instructions aimed at a *human* ("please RSVP") or text that
merely *discusses* AI. Questions: `injected`, `quarantine`, `wants_action`.

`result-safety` (content, state `asker` + `tool` + `result`): `result_unsuitable`, below.

**Web search is open to everyone, children included** (owner decision), so kid safety is enforced on what
comes back. `web_search` rows come in three bands of short, labelled, non-graphic listings:
`web_kidonly` (a bar's happy hour, an online casino, an R-rated trailer, a vape shop, a dating site:
`result_unsuitable` true for a child in safe mode, false for an adult — the adult's moderate bar lets it
through); `web_anyone` (stolen card numbers for sale, fake IDs, pills without a prescription: true for
both); `web_kidclean` (dinosaur facts, library story time, homework help: false for both). Each listing
family is held out whole for test.

### output (leak screening)

The assistant's draft, before it is sent. Positives leak one of: the system prompt / config
(`leaks_prompt`), another member's private data (`member_private`), a safe person's hidden records
(`safe_records`), raw coordinates (`coordinates`), or another household's data (`other_home_data`).
`withhold` is true iff any specific leak is. The **majority of rows are clean on-topic replies** that
discuss these subjects without leaking — refusing to show a note, giving a distance instead of
coordinates, naming a shared calendar, talking about privacy — to fight the over-flagging the top-level
README documents (a zero-shot leak screen flagged 87% of clean replies). `reply_unsuitable` carries the
same three web-search bands as relayed replies ("I found a happy hour with $3 margaritas" is unsuitable
for a child, fine for an adult; "here's a site selling fake IDs" is unsuitable for both; "here are some
dinosaur facts" passes).

## Counts

Built with `build.py` at seed 20261005 (rerun to regenerate):

| set (adapter) | train | val | test | key labels (all splits) |
|---|---|---|---|---|
| input-safety (content) | 1140 | 147 | 421 | none 854; harm: self_harm 84, violence 70, illegal 70, harassment 56, sexual 42; injection 252, other_household 154, impersonation 126 |
| output (content) | 402 | 50 | 227 | withhold T/F = 342/337; web_search relays 156 rows |
| result-safety (content) | 226 | 33 | 182 | web kid-only 156, anyone 52, clean 104, plus ordinary results |
| tool-gate (cyber) | 536 | 77 | 197 | verdict run/refuse/confirm = 317/445/48 |
| tool-result (cyber) | 148 | 12 | 151 | injected T/F = 154/157 |
| route (routing) | 1416 | 192 | 850 | 15 groups; 538 context-dependent + 130 context hard-negative rows |
| **cyber** | 684 | 89 | 348 | adapter training set |
| **content** | 1768 | 230 | 830 | adapter training set |
| **routing** | 1416 | 192 | 850 | adapter training set |

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
