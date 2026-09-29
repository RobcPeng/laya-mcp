# he-admissions-inquiry

Classifies a message to an admissions office by where the writer is in the funnel (prospect,
applicant, admitted, deposited, or outside the process) and by what it is mainly asking about, and
flags hot leads: people showing concrete intent to apply or enroll soon. Use it to route inquiries to
the right counselor queue and to surface leads for a same-day follow-up. It does not make admission
decisions and should not change how an application is reviewed. Pack: `he-admissions-inquiry` in
`laya_mcp/accelerator_packs.py`.

## Fields

| field | content |
|---|---|
| `message` | the inquiry: a request-for-information form (name, email, intended major, school, comments), an email with subject and signature or forwarded headers, or a lowercase text/chat message |

## Questions and labels

| id | type | labels |
|---|---|---|
| `stage` | choice | `prospect`, `applicant`, `admitted`, `deposited`, `other` |
| `topic` | choice | `application_status`, `requirements`, `transfer_credit`, `international`, `test_policy`, `campus_visit`, `cost_aid` |
| `hot_lead` | noul | true when the message shows strong intent to apply or enroll soon |

Labeling rules:

- `stage` comes from a stage cue sentence ("I applied early action last month", "I already paid my
  enrollment deposit"). Parents writing for a student take the student's stage. School counselors,
  current students, alumni, and vendors are `other`, even when they ask about someone's application.
- `topic` comes from the core question, which is written to fit the stage (an admitted student asks
  about a final transcript, a prospect asks about the GPA needed).
- `hot_lead` is true only when an intent sentence is present: a specific term to apply or start, a
  request to book a visit or a dated visit, or asking for next steps to apply or commit. Deposited
  students are already committed and `other` writers are not leads, so both are always false.
  Browsing hedges ("maybe someday I'll apply, just curious") are added as hard negatives.

## Size and balance

972 rows: train 635, val 87, test 250.

| question | balance (all splits) |
|---|---|
| stage | admitted 139, applicant 252, deposited 138, other 248, prospect 195 |
| topic | application_status 112, campus_visit 137, cost_aid 140, international 139, requirements 139, test_policy 165, transfer_credit 140 |
| hot_lead | false 677, true 295 |

## How it was generated

`generate.py` (stdlib only, seed 5303) is compositional. Each row = a stage cue + a topic question
from the bucket that fits the stage + an optional intent cue (about half of prospect, applicant, and
admitted rows) or a browsing hedge, then an opener, occasional Spanish-English code-switching, a
channel wrapper (inquiry form, email, lowercase chat, or plain text), and a typo pass. Visit-request
intent cues only appear on `campus_visit` questions so the topic stays unambiguous. Names, emails,
phone numbers, and schools are synthetic.

A family is a topic/stage pair (30 families, 28 rows each, doubled for `application_status` and
`test_policy`). Test holds out one topic/stage pair per topic (7 families, for example
`transfer_credit/prospect` and `cost_aid/deposited`), and held-out rows can also draw stage cues from a
pool that train never sees. Regenerate with `python datasets/accelerators/he-admissions-inquiry/generate.py`.

## Zero-shot base accuracy (test)

<!-- zero-shot:start -->
Base checkpoint, no fine-tuning, on the 250-row test split (held-out phrasing families). Majority = always answering the most common test label.

| question | type | accuracy | majority | within one level |
|---|---|---|---|---|
| stage | choice | 0.76 | 0.22 |  |
| topic | choice | 0.62 | 0.22 |  |
| hot_lead | noul | 0.83 | 0.75 |  |

Mean accuracy across questions: 0.73. Server revision: 55cf4c4ebb4ebe31b2550e8bdf3bd21b99753851.
<!-- zero-shot:end -->

## Known limitations

- One stage and one topic per message. Real inquiries often ask two things (cost and a visit); the
  core question decides here, so relabel or split multi-question messages for your own data.
- `hot_lead` is a rule about explicit intent sentences. It does not use CRM signals (prior visits,
  email opens, application started) that admissions teams usually weigh, and it misses implicit
  intent.
- Stage cues are explicit ("I got my acceptance letter"). Real messages often leave stage unstated,
  and the office has to look the person up; treat `stage` as a hint.
- US admissions vocabulary only (early action, SAT/ACT, I-20, enrollment deposit). Other systems use
  different terms and stages.
- Bias risk: A lead score can steer counselor time toward writers who phrase intent in familiar ways.
  First-generation and non-native English writers may express intent differently. Review unflagged
  messages across groups before using this to prioritize outreach.
