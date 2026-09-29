# he-student-services-routing

Routes a student's message (or a parent's message on a student's behalf) to the campus office that
handles it, scores urgency, and flags messages that need a staff member instead of an FAQ answer or a
self-service link. Pack: `he-student-services-routing` in `laya_mcp/accelerator_packs.py`.

## Fields

| field | content |
|---|---|
| `message` | the student's words as they arrive: a student portal form (topic, student ID, campus), an email with subject and signature or forwarded headers, a chat or text message, or a parent forwarding a quote from their student |

## Questions and labels

| id | type | labels |
|---|---|---|
| `office` | choice | `registrar`, `financial_aid`, `student_accounts`, `admissions`, `housing`, `it_help`, `advising`, `accessibility`, `counseling`, `library`, `other` |
| `urgency` | score | 0 low (general question), 1 normal, 2 high (a deadline, hold, or lost access is blocking the student now), 3 critical (safety concern or crisis) |
| `needs_human` | noul | true when a staff member has to look at this student's case or use judgment; false when a generic answer or self-service link resolves it |

Labeling rules:

- Gold comes from the family. Every family fixes office, urgency, and needs_human.
- "How do I / where do I / when does" questions answerable with a link (transcript ordering, FAFSA
  school code, payment plans, maintenance request portal, password reset, library hours) are
  `needs_human = false`, even when urgency is normal.
- Case-specific problems (a wrong grade, a disputed charge, pending aid documents, a roommate
  conflict, a new accommodation) are `needs_human = true`. Every urgency 2 and 3 row is true.
- Urgency 3 is reserved for safety: thoughts of self-harm, a friend in medical danger (both routed to
  `counseling`), and a housing emergency such as sparking outlets or smoke (routed to `housing`).
  Crisis rows get no small-talk openers or filler.
- Near-miss families use dramatic words for ordinary needs: "this class is killing me, how do I drop
  it", "I'm dying to get into PSY 200", "my laptop died", a fire alarm with no fire, "finals are
  crushing me, any walk-in hours?". None of these are urgency 3.

## Size and balance

791 rows: train 504, val 69, test 218.

| question | balance (all splits) |
|---|---|
| office | accessibility 51, admissions 51, advising 67, counseling 80, financial_aid 67, housing 101, it_help 68, library 68, other 51, registrar 119, student_accounts 68 |
| urgency | 0: 269, 1: 355, 2: 119, 3: 48 |
| needs_human | false 337, true 454 |

## How it was generated

`generate.py` (stdlib only, seed 5101) holds 47 hand-written families: 42 across the eleven offices and
5 near-miss families. Each family has 2-3 templates with slots for course codes, residence halls,
dollar amounts, terms, and deadline days. Each row gets an optional opener and filler sentence
("I'm a first-gen student so I don't really know how this works"), occasional Spanish-English
code-switching, a channel wrapper (portal form, email with signature or forwarded headers, parent
forwarding, lowercase chat), and a noise pass. Institutions are invented (Pine Valley State
University, Northfield Community College, ...), student IDs look like `S00012345`, and emails use
`example.edu`.

Test holds out 13 whole families, at least one per office, including a crisis family, a
case-specific and a self-service family, and two near-miss families. Regenerate with
`python datasets/accelerators/he-student-services-routing/generate.py`.

## Zero-shot base accuracy (test)

<!-- zero-shot:start -->
Base checkpoint, no fine-tuning, on the 218-row test split (held-out phrasing families). Majority = always answering the most common test label.

| question | type | accuracy | majority | within one level |
|---|---|---|---|---|
| office | choice | 0.63 | 0.16 |  |
| urgency | score | 0.64 | 0.46 | 0.95 |
| needs_human | noul | 0.41 | 0.69 |  |

Mean accuracy across questions: 0.56. Server revision: 55cf4c4ebb4ebe31b2550e8bdf3bd21b99753851.
<!-- zero-shot:end -->

## Known limitations

- Office boundaries differ by campus. Holds, refunds, and readmission sit in different offices at
  different schools, and many campuses have a one-stop enrollment center. Remap labels to your org
  chart before training.
- One need per message. Real messages often combine aid, billing, and registration in one email.
- Crisis content is intentionally short and non-graphic. Use `he-safety-escalation` for recall-first
  safety routing, and never send an automated reply to a message scored urgency 3.
- English with light Spanish code-switching only.
