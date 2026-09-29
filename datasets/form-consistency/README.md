# form-consistency

Training set for the `form-consistency` pack (`laya_mcp/packs.py`): the form-level layer of
`laya_mcp/forms.py`. The model reads every filled entry of a submitted form and answers two yes/no
questions: do any answers contradict each other, and does this look like a genuine submission rather
than a test, a joke or spam.

```bash
python datasets/form-consistency/generate.py          # writes train/val/test.jsonl (seeded)
python datasets/form-consistency/generate.py --stats
python -m finetune.pipeline --recipe form-consistency
```

## Row format

```json
{"id": "form-consistency-train-0000", "family": "fc/contra_date_order/permit",
 "state": {"form": "Residential building permit application",
           "entries": "{\"Applicant name\": \"Ingrid Holloway\", ..., \"Estimated completion date\": \"...\"}"},
 "questions": {"contradiction": {...}, "genuine": {...}},
 "gold": {"contradiction": true, "genuine": true}}
```

`entries` is a JSON string of `{label: value}` over the filled fields only, encoded with
`json.dumps(..., ensure_ascii=False)` the same way `forms.validate_form` builds it. `questions` are
copied verbatim from `packs.get_pack("form-consistency")`. The generator reuses the value pools of
`../form-field-validation/generate.py` (names, cities, phones, free-text answers).

## Row kinds

| family | contradiction | genuine | examples |
|---|---|---|---|
| `fc/clean/*`, `fc/clean_terse/*` | false | true | normal forms; terse ones keep only the first clause of long answers |
| `fc/contra_<kind>/*` | true | true | end date before start date (permits, events, trips, leave, housing, transfer attendance, grants), age vs date of birth, city/state/ZIP from different states, "no dependents" with 3 dependents, household size 1 with dependents, itemized total not equal to the amount claimed, "currently employed: no" with a current employer, full-time with 3-6 credits, first-year applicant with an associate degree, graduation year before birth, injured "no" with 3 injured, single room with two roommates, moved in 2026 but 30 months in state, grade level impossible for the student's age |
| `fc/topic_hardneg_<kind>/*` | false | true | work email domain differs from the company, mailing address differs from the project address, preferred name differs from legal name, phone area code from another state, emergency contact with another last name, one-day leave (start = end), total rounded to the dollar, half-time with 6 credits, license from the previous state with a note |
| `fc/fake_<kind>/*` | false | false | test submissions (`John Doe`, `123 Fake St`, `asdf`, `test@example.org`), real forms half overwritten with `test - please ignore`, joke entries (Batman, the Batcave, "a dragon ate my homework"), SEO/crypto/casino spam, keyboard mash |

A contradiction is a mistake made by a real person, so contradiction rows stay `genuine: true`.
Families named `topic_hardneg_*` are reported as hard negatives by `finetune/evaluate.py`
(`hard_negative_fp_rate_at_05`).

## Forms and splits

20 forms. Train side: 311 request, building permit, benefits intake, job application, event
registration, patient intake, expense report, vendor onboarding, incident report, and higher
education (weighted 1.6x): undergraduate admissions, transfer credit evaluation, transcript request,
late add/drop or withdrawal petition, financial aid / SAP appeal, accessibility accommodation request.
TEST holds out whole forms: employee leave request, community grant, K-12 enrollment, in-state
residency application, student housing application. Some contradiction kinds exist only on held-out
forms (`months`, `age_grade`, `single_roommates`, `day_count`), so test measures whether the model
learned "answers that cannot both be true" rather than a list of known pairs.

| split | rows | contradiction=true | genuine=false | clean | contra | hard negative | fake | higher-ed rows |
|---|---|---|---|---|---|---|---|---|
| train | 1125 | 362 | 235 | 379 | 362 | 149 | 235 | 555 |
| val | 125 | 43 | 23 | 41 | 43 | 18 | 23 | 58 |
| test | 330 | 109 | 64 | 114 | 109 | 43 | 64 | 172 |

## Results

`python -m finetune.pipeline --recipe form-consistency` (full fine-tune of `english`, 4 epochs,
one RTX 3090), test split (held-out forms):

| metric | base | fine-tuned |
|---|---|---|
| genuine accuracy / AUC | 0.21 / 0.29 | 1.00 / 1.00 |
| contradiction accuracy / AUC | 0.61 / 0.42 | 0.76 / 0.71 |
| contradiction recall at 0.5 | 0.01 | 0.29 |
| contradiction false-positive rate at 0.5 | 0.09 | 0.005 |
| hard-negative false positives | 0% | 0% |

`genuine` is solved on this data. Every fake scored below 0.05 and every genuine form but one
scored above 0.42, so `LAYA_FORM_GENUINE_MIN_P=0.3` rejects all test, joke and spam submissions and
no real ones.

`contradiction` is not solved. The tuned model rarely raises a false alarm but finds under a third
of the contradictions, and recall stays at 0.29 for every threshold from 0.3 to 0.6, so moving
`LAYA_FORM_CONTRADICTION_P` does not help. Catches come mostly from date-order contradictions
(30 of 42); the age, month-count and total kinds held out in test were almost never found. Treat a
contradiction flag as a useful review signal, never treat its absence as a pass, and put
deterministic checks in front of it for structured pairs (dates, ages, totals).

## Limitations

- Synthetic and templated: each contradiction kind is one perturbation of one field pair. Real
  contradictions are often subtler (a date format read two ways, a typo in a ZIP code).
- Consistency with the outside world (is 80202 really Denver?) is only learnable for the ZIP codes
  in the pool. Use a ZIP lookup rule for that in production; the model is for cross-field logic.
- The date arithmetic questions (age from birth date, months since a move) are hard for an encoder.
  Expect them to be the weakest families; a deterministic check is better when both fields are
  structured.
- The email-domain hard negative is the most common hard negative because most forms have an email
  field. Others have 1-15 rows each.
- English, US-centric forms. Add your own labelled submissions with `--data` (keep them private).
