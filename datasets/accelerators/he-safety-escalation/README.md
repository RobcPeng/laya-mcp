# he-safety-escalation

This set trains a high-recall routing filter that decides which student messages a trained person must
see right away: possible self-harm, threats of violence, sexual misconduct disclosures, and medical
emergencies. It only routes and does not respond to anyone. People and crisis resources decide and respond.

Deployment rules:

- Never send an automated response to the student based on this model. A positive routes the message to
  on-call staff (counseling, campus safety, the Title IX office, or 911 per your protocol); a negative
  goes to the normal queue, where a person still reads it.
- Tune the `escalate_now` threshold for recall on the val split, not for accuracy. Accept more false
  alarms to miss fewer crises.
- Track the false-negative rate of `escalate_now` on test (below) and on every retrain. Do not ship a
  checkpoint whose recall has not been measured.
- Pair it with keyword rules and human review. A 421M text classifier is only one layer.

Pack: `he-safety-escalation` in `laya_mcp/accelerator_packs.py`.

## Fields

| field | content |
|---|---|
| `message` | a student message to a campus portal chat, chatbot, advisor, RA, anonymous form, counseling intake form, or the dean of students, with a channel prefix |

## Questions and labels

| id | type | labels |
|---|---|---|
| `escalate_now` | noul | true iff `category` is `self_harm`, `violence_threat`, `sexual_misconduct`, or `medical_emergency` |
| `category` | choice | `self_harm`, `violence_threat`, `sexual_misconduct`, `medical_emergency`, `stress_venting`, `routine` |

Labeling rules:

- Self-harm includes indirect signs: saying goodbye, giving belongings away, "it won't matter after
  tonight", and a friend reporting someone else's statements.
- Violence covers threats the writer makes and fear of someone who threatened the writer, weapon
  reports, and partner violence.
- Sexual misconduct covers first-person and third-party disclosures of assault, harassment, stalking,
  and sextortion, including events from weeks ago that were never reported.
- Medical emergencies are happening now: unresponsive person, possible overdose, allergic reaction,
  head injury, chest pain.
- `stress_venting` is hyperbole and ordinary stress: "this exam is killing me", "dying to get into that
  class", "could kill for coffee", "my roommate's music makes me want to die lol", "we're going to destroy
  them", anger about a grade. None escalate.
- `routine` includes the same topics asked about for coursework or logistics (where the Title IX office
  is, suicide prevention research, CPR class sign-up, Narcan training) and past incidents that were
  already handled (asking for an outcome letter or a case number). None escalate.
- Messages are non-graphic by design: no methods and no injury detail.

## Size and balance

728 rows: train 434, val 59, test 235.

| question | balance (all splits) |
|---|---|
| escalate_now | false 309, true 419 |
| category | medical_emergency 94, routine 138, self_harm 115, sexual_misconduct 80, stress_venting 171, violence_threat 130 |

## How it was generated

`generate.py` (stdlib only, seed 9110) holds 27 hand-written families: 13 escalation families across the
four crisis categories and 14 non-escalation families built from the same vocabulary. Each family has
2-4 templates with slots for courses, residence halls, campus places, relationships, and times. Rows
get a channel prefix, and some get typos or all-lowercase chat style. Escalation families get a few
extra rows each so positives are not a minority.

Test holds out 9 whole families: goodbye-style self-harm, fear of a threat, third-party sexual
misconduct disclosures, allergy and injury emergencies, "could kill for" and "want to die lol"
hyperbole, anger without threats, suicide prevention research questions, and past handled incidents.
Regenerate with `python datasets/accelerators/he-safety-escalation/generate.py`.

## escalate_now false-negative rate (test, base checkpoint)

Measured with `fn_rate.py` against the live server (results in `fn_rate.json`). 117 positive and 118
negative test rows. FN rate = share of crisis messages scored below the threshold.

| threshold | FN rate | recall | FP rate | FN rate by category |
|---|---|---|---|---|
| 0.5 | 0.82 | 0.18 | 0.20 | self_harm 1.00, sexual_misconduct 1.00, medical 0.72, violence 0.65 |
| 0.3 | 0.76 | 0.24 | 0.28 | self_harm 1.00, sexual_misconduct 0.86, medical 0.59, violence 0.65 |
| 0.2 | 0.62 | 0.39 | 0.35 | self_harm 1.00, sexual_misconduct 0.55, medical 0.31, violence 0.62 |
| 0.1 | 0.39 | 0.62 | 0.52 | self_harm 0.90, sexual_misconduct 0.23, medical 0.03, violence 0.38 |

The base checkpoint must not be used for this task. It misses nearly every held-out self-harm message
even at a 0.1 threshold. Fine-tune, rerun `fn_rate.py` on test, and choose the threshold on val for the
recall your protocol requires. Rerun with `python datasets/accelerators/he-safety-escalation/fn_rate.py`.

## Zero-shot base accuracy (test)

<!-- zero-shot:start -->
Base checkpoint, no fine-tuning, on the 235-row test split (held-out phrasing families). Majority = always answering the most common test label.

| question | type | accuracy | majority | within one level |
|---|---|---|---|---|
| escalate_now | noul | 0.49 | 0.50 |  |
| category | choice | 0.44 | 0.33 |  |

Mean accuracy across questions: 0.47. Server revision: 55cf4c4ebb4ebe31b2550e8bdf3bd21b99753851.
<!-- zero-shot:end -->

## Known limitations

- Synthetic and short. Real crisis messages are often ambiguous, long, mixed with ordinary requests, or
  written in other languages. Validate on reviewed real messages under your institution's data rules
  before relying on recall numbers.
- The compound `escalate_now` question asks about four risks at once. The base model scores it poorly
  (a direct question like "Does `message` mention suicide or self-harm?" scores much higher zero-shot on
  the same text); fine-tuning is required.
- Label lines are one reasonable policy. Some campuses escalate every sexual misconduct disclosure to a
  confidential resource rather than on-call staff; route per your protocol.
- No method or injury detail appears in the data, so the model has not seen the most explicit phrasing.
