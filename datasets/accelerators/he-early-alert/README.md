# he-early-alert

This set trains a decision-support model for advisors. It reads an early-alert note from faculty,
advisors, coaches, tutors, or residence life and flags academic, attendance, financial, and wellbeing
signals, with an overall level of advisor outreach. Its output orders a human advisor's caseload. It must
never act on a student by itself: no automated holds, grade changes, aid changes, conduct or disciplinary
referrals, and no automated messages to the student. A person reads every note it scores.

Notes that suggest a crisis (hopelessness, a student who has disappeared) also belong in the campus
safety process; see `he-safety-escalation`. Pack: `he-early-alert` in `laya_mcp/accelerator_packs.py`.

## Fields

| field | content |
|---|---|
| `note` | an early-alert note: LMS flag, advisor case note, faculty email, coach report, residence life note, tutoring center log, or progress report |

## Questions and labels

| id | type | labels |
|---|---|---|
| `academic_risk` | noul | failing grades, missing work, falling behind |
| `attendance` | noul | unexcused or unexplained missed classes, labs, or sections |
| `financial_stress` | noul | trouble paying tuition, rent, food, books, or transport, or working long hours to pay |
| `wellbeing_concern` | noul | withdrawn, anxious, isolated, ill, grieving, or other mood or behavior change |
| `risk` | score | 0 none, 1 low (check-in), 2 moderate (reach out this week), 3 high (reach out promptly and refer) |

`risk` rule, applied in this order:

1. Crisis-adjacent wellbeing language (hopelessness, not leaving the room for a week, stopped eating) = 3.
2. No signals = 0.
3. Three or more signals, or wellbeing plus any other signal = 3.
4. Two signals, or wellbeing alone = 2.
5. One non-wellbeing signal = 1.

Neutral snippets reuse the vocabulary without the signal and do not count: an excused absence for team
travel with the work caught up, a scholarship that covers costs, a manageable part-time job, a strong
midterm score.

## Size and balance

875 rows: train 550, val 75, test 250.

| question | balance (all splits) |
|---|---|
| academic_risk | false 597, true 278 |
| attendance | false 580, true 295 |
| financial_stress | false 601, true 274 |
| wellbeing_concern | false 583, true 292 |
| risk | 0: 253, 1: 186, 2: 164, 3: 272 |

## How it was generated

`generate.py` (stdlib only, seed 2718) is compositional. Each row picks a note style, draws the four
signals independently (18% of rows have none), adds one snippet per signal and zero to two neutral
snippets, shuffles them, and renders the note in its style. Numbers (missing assignments, grades, dates)
are slot-filled; names are placeholders; some rows get typos or all-lowercase text.

Snippets come in two banks. Train and val use bank A in five styles (LMS flag, advisor note, coach,
tutoring, progress report). Test uses bank B in two held-out styles (faculty email, residence life
note), so test wording is new in both the frame and the signal sentences. Regenerate with
`python datasets/accelerators/he-early-alert/generate.py`.

## Zero-shot base accuracy (test)

<!-- zero-shot:start -->
Base checkpoint, no fine-tuning, on the 250-row test split (held-out phrasing families). Majority = always answering the most common test label.

| question | type | accuracy | majority | within one level |
|---|---|---|---|---|
| academic_risk | noul | 0.74 | 0.68 |  |
| attendance | noul | 0.85 | 0.68 |  |
| financial_stress | noul | 0.82 | 0.68 |  |
| wellbeing_concern | noul | 0.74 | 0.63 |  |
| risk | score | 0.28 | 0.36 | 0.63 |

Mean accuracy across questions: 0.69. Server revision: 55cf4c4ebb4ebe31b2550e8bdf3bd21b99753851.
<!-- zero-shot:end -->

## Known limitations

- The risk rule is a simple count with a wellbeing weight. Advising offices weigh signals differently
  (first-generation status, credit load, prior alerts); relabel `risk` to match your outreach model.
- One note at a time. Real risk shows up across several notes and systems (LMS activity, grades,
  holds); combine this with structured data rather than replacing it.
- Notes are short and written in a clean professional register. Real faculty notes are sometimes one
  word ("concerned") or full of course-specific shorthand.
- Bias risk: A model that orders outreach can under-serve students whose situations are described in
  unfamiliar terms. Review flagged and unflagged notes regularly across student groups.
