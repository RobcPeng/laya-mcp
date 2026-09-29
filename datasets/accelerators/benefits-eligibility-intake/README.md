# benefits-eligibility-intake

First-pass screening for a public benefits inquiry (web chat, email, voicemail transcript, or a
caseworker's intake note): which assistance program fits the stated need, whether there is an urgent
hardship that should jump the queue, and whether the intake is missing the details needed to start an
application. Pack: `benefits-eligibility-intake` in `laya_mcp/accelerator_packs.py`. All data is
synthetic; no real applicant data was used.

## Fields

| field | content |
|---|---|
| `message` | the inquiry as written or transcribed, in first person, a relative's voice, a caseworker note, a chat log, or a voicemail transcript |

## Questions and labels

| id | type | labels |
|---|---|---|
| `program` | choice | `snap`, `medicaid`, `unemployment`, `housing`, `childcare`, `energy_assistance`, `cash_assistance` |
| `urgent_hardship` | noul | true for an eviction or shutoff notice, no food in the home, homelessness, or a medical emergency happening now |
| `missing_info` | noul | true unless household size, monthly income, and county of residence are all stated |

Labeling rules:

- `program` is the help the person asks for. Benefits they already receive ("we already get SNAP, what
  I need is health coverage") are not the answer. When a hardship line mentions another need (a
  laid-off worker who also has an eviction notice), the explicit ask still decides the program.
- `urgent_hardship` is about the present. Near-misses are false: an eviction last year, worry about
  falling behind someday, a high bill with no shutoff notice, a hospital stay that is over. A message
  that says the person is homeless now is always true.
- `missing_info` is controlled by the generator: each of the three facts is independently included or
  left out. Vague versions count as missing: "me and my kids" (no number), "I don't make much", a town
  with no county. "No income right now" counts as a stated income. Amounts are monthly.

## Size and balance

840 rows: train 554, val 76, test 210.

| question | balance (all splits) |
|---|---|
| program | 120 per program (7 programs) |
| urgent_hardship | false 469, true 371 |
| missing_info | false 379, true 461 |

## How it was generated

`generate.py` (stdlib only, seed 2027). 28 core families (4 per program) hold the ask, 2-3 phrasings
each. They include renewals and cut benefits, denied claims, pregnancy, relative caregivers, after-school
care, propane, households that already receive a different benefit, and Spanish-English code-switched
messages. Each row adds a hardship line (about 42% urgent and program-specific, 20% near-miss, the rest
neutral context), then the three intake facts in random order, each present with probability 0.77.
It is then rendered in one of several voices: caseworker note, voicemail transcript, a relative writing
on someone's behalf, web chat, or plain first person. A noise pass adds typos and lowercase. Counties
and towns are invented (Pine County, Anytown, North Placeholder).

Test holds out one core family per program (SNAP renewal cuts, pregnancy coverage, unemployment claim
problems, housing vouchers, childcare for households already on Medicaid or SNAP, propane, relative
caregivers).

## Zero-shot base accuracy (test)

<!-- zero-shot:start -->
Base checkpoint, no fine-tuning, on the 210-row test split (held-out phrasing families). Majority = always answering the most common test label.

| question | type | accuracy | majority | within one level |
|---|---|---|---|---|
| program | choice | 0.78 | 0.14 |  |
| urgent_hardship | noul | 0.80 | 0.60 |  |
| missing_info | noul | 0.43 | 0.58 |  |

Mean accuracy across questions: 0.67. Server revision: 55cf4c4ebb4ebe31b2550e8bdf3bd21b99753851.
<!-- zero-shot:end -->

## Known limitations

- Program names and boundaries follow common US programs. A state's actual program list (WIC, LIHEAP
  by name, general assistance, state-specific child care programs) should replace or extend the seven
  labels, and `missing_info` should match the state's real minimum intake fields.
- One primary program per message. Real households often qualify for several at once; this set screens
  for the first referral, not eligibility.
- Spanish appears only as code-switching in a minority of rows. A Spanish-first population needs its
  own labeled data and possibly the multilingual checkpoint.
- The model does not determine eligibility. Income and household size are only checked for presence.
