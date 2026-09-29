# content-moderation

Moderates short user-generated text (comments, replies, reviews, game chat) for toxicity, targeted
harassment, threats, and spam, and gives an overall severity that maps to a moderator action. Pack:
`content-moderation` in `laya_mcp/accelerator_packs.py`.

## Fields

| field | content |
|---|---|
| `text` | the post, sometimes framed as a reply to a handle, a star review, a game-chat line, a quoted forum reply, or a comment on a named article |

## Questions and labels

| id | type | labels |
|---|---|---|
| `toxic` | noul | true for insults, demeaning language, or profanity aimed at a person or group |
| `harassment` | noul | true when a specific person is targeted with personal attacks, intimidation, or humiliation |
| `threat` | noul | true for threats of violence or harm, including threats to expose someone's job or family |
| `spam` | noul | true for scam links, get-rich schemes, repetitive self-promotion, and unrelated ads |
| `severity` | score | 0 acceptable, 1 rude or off-topic but allowed, 2 remove, 3 remove and escalate or suspend |

Labeling rules:

- An insult aimed at one handle is both `toxic` and `harassment`. An insult aimed at a group or at
  everyone in a thread is `toxic` only.
- A threat without insulting words is `threat` and (when aimed at a handle) `harassment`, but not
  `toxic`. Threats about a third party ("someone should burn down the office") are `threat` only.
- Severity: threats, doxxing-style intimidation, and sustained harassment campaigns are 3; one-off
  personal insults, humiliation, group insults, and spam are 2; off-topic posts, dismissive comments
  about content, and all-caps rants are 1; everything else is 0.
- Hard negatives (all labels false, severity 0): civil disagreement, violent idioms ("kill it at the
  show", "this bug is killing me"), profanity not aimed at anyone, game banter ("I'm gonna destroy you
  next round"), on-topic self-promotion with disclosure, and users reporting abuse they received.

Content in this set is kept mild: no slurs, no protected-class targets, and no graphic violence. That
keeps the repo public-safe but means the set does not cover the worst content a real platform sees.

## Size and balance

820 rows: train 528, val 72, test 220.

| question | balance (all splits) |
|---|---|
| toxic | false 625, true 195 |
| harassment | false 589, true 231 |
| threat | false 659, true 161 |
| spam | false 653, true 167 |
| severity | 0: 240, 1: 91, 2: 294, 3: 195 |

## How it was generated

`generate.py` (stdlib only, seed 6060) holds 26 hand-written families: 8 acceptable (including 6
hard-negative families), 3 rude-but-allowed, 2 group-toxic, 4 harassment, 4 threat, and 5 spam. Each
family has 2-6 templates with slots for handles, topics, products, mild insults, groups, and fake
`example.*` links. Each row gets a random platform frame and a noise pass (typos, lowercase chat
style).

Test holds out 7 whole families (`clean/civil-disagree`, `clean/game-banter`, `rude/dismissive`,
`toxic/profane-at-crowd`, `harass/humiliation`, `threat/veiled`, `spam/crypto`). Regenerate with
`python datasets/accelerators/content-moderation/generate.py`.

## Zero-shot base accuracy (test)

<!-- zero-shot:start -->
Base checkpoint, no fine-tuning, on the 220-row test split (held-out phrasing families). Majority = always answering the most common test label.

| question | type | accuracy | majority | within one level |
|---|---|---|---|---|
| toxic | noul | 0.80 | 0.73 |  |
| harassment | noul | 0.70 | 0.71 |  |
| threat | noul | 0.80 | 0.85 |  |
| spam | noul | 0.96 | 0.84 |  |
| severity | score | 0.29 | 0.42 | 0.60 |

Mean accuracy across questions: 0.71. Server revision: 55cf4c4ebb4ebe31b2550e8bdf3bd21b99753851.
<!-- zero-shot:end -->

## Known limitations

- Mild on purpose (see above). Before production, add labeled real data from your platform, including
  slurs, coded language, and the protected-class hate that this set leaves out.
- Posts are short and single-message. Harassment that only shows across a thread or across accounts is
  out of scope for a single-text check.
- English only. Obfuscated spellings ("1d10t") appear only through random typos.
- Severity follows one reasonable policy. Platforms that allow group insults, or treat all spam as
  severity 3, should relabel.
