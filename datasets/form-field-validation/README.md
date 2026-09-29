# form-field-validation

Training set for the `form-field-validation` pack (`laya_mcp/packs.py`): the per-field model layer
of `laya_mcp/forms.py`. Given a form, one field and the submitter's entry, the model picks the
category (`pass` is a category the model has to choose, not the absence of a failure), whether a
person should review the entry, and how well it answers the field.

```bash
python datasets/form-field-validation/generate.py          # writes train/val/test.jsonl (seeded)
python datasets/form-field-validation/generate.py --stats  # label balance only
python -m finetune.pipeline --recipe form-field-validation
```

## Row format

```json
{"id": "form-field-validation-train-0000", "family": "ffv/pass/311",
 "state": {"form": "City 311 service request (report a non-emergency problem)",
           "field": "Full name: Your first and last name", "entry": "Delacroix, Siobhan"},
 "questions": {"category": {...}, "needs_review": {...}, "quality": {...}},
 "gold": {"category": "pass", "needs_review": false, "quality": 3}}
```

- `field` is built the way `forms._field_text` builds it: `"Label: description"`, or just the label
  when there is no description. Optional fields say so in the description.
- `questions` are copied verbatim from `packs.get_pack("form-field-validation")`.
- `family` is `ffv/<kind>/<form>`. Kinds include the category plus sub-kinds such as
  `wrongtype_phone`, `unrelated_generic`, `abusive_threat`, `incomplete_attach`. The hard-negative
  `pass` kinds are named `topic_hardneg_*` so `finetune/evaluate.py` reports them separately.

## Coverage

27 forms and 59 field types. Public sector and general: 311 service request, building permit,
public records (FOIA) request, benefits intake, job application, contact-us, support ticket, event
registration, patient intake, clinic appointment, vendor onboarding, expense report, community
grant, feedback survey, account signup, incident report, K-12 enrollment. Higher education (weighted
1.6x): undergraduate admissions, transfer credit evaluation, transcript request, late add/drop or
withdrawal petition, grade appeal, in-state residency, housing, financial aid verification / SAP
appeal, accessibility accommodation request, student employment.

Field types include names, organization, job title, street address, apartment/unit (optional), city,
state, ZIP, dates (birth, event, start), time, phone, email, website, amount, quantity, case /
ticket / invoice / parcel numbers, student ID, GPA, term, course code, school, major, country,
relationship, hours per week, years of experience, insurance member ID, yes/no answers, "how did you
hear about us", dietary needs, medications, and about 24 free-text fields (issue descriptions, scope
of work, records requested, reason for request, comments, incident narrative, support issue, expense
purpose, grant summary, feedback, symptoms, accommodations, personal statement, grade-appeal basis,
petition reason, residency explanation, SAP appeal, transfer course, transcript delivery, housing
preferences, work experience, event notes).

## Labels and the decisions behind them

| category | what the entries look like |
|---|---|
| `pass` | realistic and often messy but valid: lowercase names, `Delacroix, Siobhan`, `O'Brien-Nguyen`, abbreviations, terse answers like `Pothole, 3rd & Main, eastbound lane` |
| `empty_or_placeholder` | n/a, none, test, asdf, `-`, `.`, TBD, see above, lorem ipsum, fill in later |
| `gibberish` | keyboard rows, consonant runs, mixed junk, random Unicode |
| `wrong_type` | a structured value of another kind: phone in a name field, name in a date field, email in an address field, date in an amount field |
| `wrong_format` | the right kind of value, malformed: `13/45/2026`, email without a TLD, too few phone digits, `8O202`, `25:30` |
| `incomplete` | on topic but too vague to act on: `broken`, `stuff`, `yes` for a description, first name only for a full name, street without a number |
| `off_topic` | a coherent sentence that answers a different question: `What time does the library open?` in a pothole description, or another field's real answer |
| `sensitive_data` | passwords, SSN-like and card-like data in free-text fields, including paraphrases the rules miss (`my social is zero zero zero...`, `the login is admin / Summer2026!`) |
| `abusive` | insults, profanity aimed at people, threats, spam links |

Decisions made where the categories overlap:

- Number words where a numeric amount or quantity is asked (`twelve hundred`, `a dozen`) are
  `wrong_format`: the right information in an unusable form.
- Structured values of another kind are `wrong_type`; sentences that answer another question are
  `off_topic`.
- Too few or too many digits in a phone, ZIP or ID is `wrong_format`, not `incomplete`.
  `incomplete` is kept for vague content.
- Hard negatives, all `pass`: `N/A`, `none` or `-` in a field marked optional; `none` where it is
  a real answer (medications, dietary needs, yes/no); descriptions that mention a password reset, a
  declined card or a lost Social Security card without giving one; mild profanity inside a real
  complaint (`Damn pothole ate my tire on Aspen Way`).
- "Anything else?" fields (comments, organizer notes) never get `off_topic` or `wrong_type` rows,
  because any real remark answers them.

`needs_review` is true for every `sensitive_data` row, for threats (a subset of `abusive`), and for
`see attached` style answers in free-text fields (`incomplete`, but a person should check the
attachment). `quality` follows the category: `pass` is 3 (clear) or 2 (terse, lowercase, or an
optional N/A), `wrong_format` and `incomplete` are 1, every other failure is 0.

## Splits and balance

Category first, then a field where it can occur, so the balance is set directly (about 31-34%
`pass`). TEST holds out whole forms (vendor onboarding, community grant, K-12 enrollment, grade
appeal, residency, accessibility request) and whole field types (website, time, insurance member ID,
hours per week, residency explanation, grade-appeal basis, housing preferences). No train or val row
comes from a held-out form or field type (the generator asserts this). VAL is a random 10% of the
train side.

| split | rows | pass | placeholder | gibberish | wrong_type | wrong_format | incomplete | off_topic | sensitive | abusive | needs_review=true |
|---|---|---|---|---|---|---|---|---|---|---|---|
| train | 2250 | 692 | 194 | 155 | 242 | 163 | 186 | 267 | 185 | 166 | 242 |
| val | 250 | 82 | 19 | 22 | 22 | 16 | 20 | 35 | 19 | 15 | 24 |
| test | 620 | 210 | 62 | 43 | 76 | 42 | 43 | 66 | 31 | 47 | 44 |

Higher-ed rows: 971 train, 106 val, 375 test.

## Results

`python -m finetune.pipeline --recipe form-field-validation` (full fine-tune of `english`, 4 epochs,
one RTX 3090), test split:

| metric | base | fine-tuned |
|---|---|---|
| category accuracy | 0.48 | 0.94 |
| quality accuracy | 0.55 | 0.93 |
| needs_review accuracy / AUC | 0.87 / 0.22 | 1.00 / 1.00 |
| macro accuracy | 0.64 | 0.96 |
| hard-negative false positives | 100% | 0% |

The tuned checkpoint is confident even when wrong: 581 of 620 test entries were categorized
correctly, and both right and wrong answers have a median confidence of 0.996. Raising
`LAYA_FORM_MIN_CONFIDENCE` to 0.6 catches 10% of the wrong answers (4 of 39) and sends 1 correct
answer in 581 to review; above 0.6 it barely changes. Use 0.6 with this checkpoint and do not rely on
the threshold as the main safety net.

## Limitations

- Templated and synthetic. The held-out forms and field types test generalization to new
  structure, but not to your submitters' writing. Add labelled rows from your own forms with
  `--data` (keep them in `datasets/private/`).
- English only, US-centric formats (ZIP codes, MM/DD dates, US phone numbers).
- The failure pools (placeholders, abuse, sensitive phrasings) are shared across forms, so a
  failure category is easier on test than a new `pass` phrasing is. Watch `pass` precision and
  recall, not only overall accuracy.
- Some boundaries are policy choices (number words = `wrong_format`; mild profanity in a real
  complaint = `pass`). If your policy differs, relabel and retrain; the model learns the labels.
- The deterministic rules in `forms.py` already catch empty required fields, length and pattern
  violations, SSNs, Luhn-valid card numbers and `password: ...` assignments before the model sees an
  entry. The set still includes some rule-catchable rows so the model is not blind to them when
  rules are off (`use_rules=False`).
