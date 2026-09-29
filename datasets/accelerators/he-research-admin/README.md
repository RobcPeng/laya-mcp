# he-research-admin

Triage for a sponsored research office inbox: which topic an email is about (so it lands with
pre-award, post-award, or compliance staff) and whether it mentions an upcoming deadline. Emails come
from PIs, department grant administrators, postdocs, subrecipient research offices, and the sponsored
programs office itself. Pack: `he-research-admin` in `laya_mcp/accelerator_packs.py`.

## Fields

| field | content |
|---|---|
| `email` | the email with From and Subject headers, body, and signature; some are forwarded or quote an earlier reply |

## Questions and labels

| id | type | labels |
|---|---|---|
| `topic` | choice | `proposal`, `budget`, `subaward`, `compliance`, `effort`, `award_setup`, `closeout`, `other` |
| `deadline` | noul | true when the email names an upcoming sponsor or internal due date or cutoff |

Labeling rules:

- The topic is what the sender asks the recipient to act on. A proposal email with a side question about
  the F&A rate is `proposal`; a closeout email where the last open item is one effort report is
  `closeout`. These mixed emails are their own families.
- `budget` covers rates, allowability, rebudgeting, and cost transfers, before or after award.
- `compliance` covers IRB, IACUC, conflict of interest, export control, and research security training.
- `deadline` is true only for an explicit upcoming date or cutoff ("the sponsor deadline is November
  14", "internal routing deadline is this Friday", "we need this back by Monday"). It is false when
  there is no date, when the sender says "no rush", or when the only date has passed ("the last deadline
  passed on March 3", "we missed the cutoff"). Deadline is assigned independently of topic, about half
  of rows each way.

## Size and balance

754 rows: train 480, val 66, test 208.

| question | balance (all splits) |
|---|---|
| topic | award_setup 78, budget 104, closeout 104, compliance 104, effort 78, other 78, proposal 130, subaward 78 |
| deadline | false 381, true 373 |

## How it was generated

`generate.py` (stdlib only, seed 5150) holds 29 phrasing families across the eight topics, two of them
mixed-topic families. Each family has 2-3 templates with slots for invented sponsors ("the Aldercrest
Foundation", "a federal science agency"), invented partner institutions, award numbers, amounts, rates,
protocol numbers, and cost items. Each template ends in a deadline slot filled from seven upcoming
phrasings or from blank, "no rush", and past-date phrasings. Emails get a sender at `example.edu` with a
placeholder name, a role-based signature, a noise pass, and sometimes a forward or quoted reply.

Test holds out 8 whole families, one per topic, including the closeout-with-effort mixed family.
Regenerate with `python datasets/accelerators/he-research-admin/generate.py`.

## Zero-shot base accuracy (test)

<!-- zero-shot:start -->
Base checkpoint, no fine-tuning, on the 208-row test split (held-out phrasing families). Majority = always answering the most common test label.

| question | type | accuracy | majority | within one level |
|---|---|---|---|---|
| topic | choice | 0.76 | 0.12 |  |
| deadline | noul | 0.65 | 0.53 |  |

Mean accuracy across questions: 0.71. Server revision: 55cf4c4ebb4ebe31b2550e8bdf3bd21b99753851.
<!-- zero-shot:end -->

## Known limitations

- Terms are generic (F&A, NCE, IRB, IACUC, effort certification, subrecipient monitoring). Real inboxes
  use sponsor-specific form names, system names, and acronyms; add scrubbed local emails.
- Deadline phrases are appended as a sentence, which makes them easier to spot than in real email, where
  dates hide in signatures, subject lines, and long threads.
- "Upcoming" is judged from the wording alone. A bare future-sounding date like "December 1"
  counts as upcoming; the model does not know today's date.
- No-cost extensions and prior-approval requests are not their own label; they fall under `budget` or
  `other` depending on the wording. Split them out if your office routes them separately.
