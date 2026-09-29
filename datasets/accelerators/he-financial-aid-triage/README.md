# he-financial-aid-triage

Triages messages to a financial aid office by topic, flags messages tied to a near deadline, and flags
messages that carry sensitive financial or identity details (useful before a message is logged,
forwarded, or sent to an external LLM). Pack: `he-financial-aid-triage` in
`laya_mcp/accelerator_packs.py`.

## Fields

| field | content |
|---|---|
| `message` | the student's or parent's message: an aid inquiry form (student ID, school, aid year), an email with signature or forwarded headers, a parent forwarding for a student, or lowercase chat |

## Questions and labels

| id | type | labels |
|---|---|---|
| `topic` | choice | `verification`, `sap_appeal`, `dependency_override`, `award_letter`, `disbursement`, `work_study`, `loans`, `scholarships`, `other` |
| `deadline_sensitive` | noul | true when the message states a deadline or date that is days away |
| `sensitive_info` | noul | true when the message contains an actual income figure, tax-return value, bank account number, or SSN |

Labeling rules:

- `topic` comes from the core question. Special-circumstances and professional judgment requests
  ("my mom lost her job after we filed") are `award_letter`, because they ask to change the offer.
  Office hours, 1098-T, address changes, food pantry, and laptop loans are `other`.
- `deadline_sensitive` is set by an added sentence. Near: "classes start Monday and my bill is due",
  "census date is in 3 days", "the deadline on the letter is this Wednesday" (true). Far or past: "no
  rush, this is for next year", "I missed last year's deadline but that's in the past" (false).
- `sensitive_info` is set by an added sentence with values: parent or student income in dollars, AGI,
  wages and tax paid, a checking account and routing number, or an SSN (always the never-issued
  `000-xx-xxxx` form). Look-alikes are false: a student ID, a phone number, a Pell or work-study award
  amount, a bill balance, "our income went down a lot" with no figure, "I uploaded my tax transcript".
- The two flags are drawn independently of topic and of each other, so every topic has all four
  combinations.

## Size and balance

809 rows: train 474, val 65, test 270.

| question | balance (all splits) |
|---|---|
| topic | award_letter 90, dependency_override 90, disbursement 89, loans 90, other 90, sap_appeal 90, scholarships 90, verification 90, work_study 90 |
| deadline_sensitive | false 444, true 365 |
| sensitive_info | false 490, true 319 |

## How it was generated

`generate.py` (stdlib only, seed 5202) holds 27 families, three per topic, each with two core
questions written in FAFSA and aid-office language (verification groups, IRS tax return transcripts,
completion rate and maximum timeframe, unusual circumstances, Parent PLUS denial, MPN and entrance
counseling, outside scholarships). Each row adds an optional deadline or far-deadline sentence, an
optional sensitive or look-alike sentence, an opener, occasional Spanish-English code-switching, a
channel wrapper, and a noise pass. All names, IDs, and numbers are synthetic.

Test holds out one family per topic (27 families, 9 held out), so the test split is about a third of
the set. Regenerate with `python datasets/accelerators/he-financial-aid-triage/generate.py`.

## Zero-shot base accuracy (test)

<!-- zero-shot:start -->
Base checkpoint, no fine-tuning, on the 270-row test split (held-out phrasing families). Majority = always answering the most common test label.

| question | type | accuracy | majority | within one level |
|---|---|---|---|---|
| topic | choice | 0.83 | 0.11 |  |
| deadline_sensitive | noul | 0.64 | 0.53 |  |
| sensitive_info | noul | 0.68 | 0.62 |  |

Mean accuracy across questions: 0.72. Server revision: 55cf4c4ebb4ebe31b2550e8bdf3bd21b99753851.
<!-- zero-shot:end -->

## Known limitations

- "Close" deadlines are relative phrases ("Friday", "in 3 days"). If your messages carry absolute
  dates, prepend the received date to the message so the model can compare.
- The sensitive-info rule is a DLP rule. Award amounts and student IDs are labeled false here; see
  `he-ferpa-sensitive` for FERPA education-record classification.
- The added deadline and sensitive sentences are generic and sometimes read as bolted on to the core
  question. Real messages weave them in.
- One topic per message. Aid questions often span disbursement and billing; the core question decides.
