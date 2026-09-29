# Accelerator training sets

Synthetic, labeled training sets for common production and POC use cases: twelve general and
public-sector sets and ten higher-education sets. Each one pairs a question pack in
`laya_mcp/accelerator_packs.py` with train/val/test JSONL, so a POC can fine-tune Laya on its domain on
day one instead of starting from a base checkpoint that is near chance on narrow labels.

The sets are starting points. They teach the model the label scheme, the
question wording, and the hard cases (look-alikes, near misses, noisy input). Before a real rollout, add
a few hundred labeled rows from your own traffic with `--data` (see below) and re-check the numbers on
data you did not write.

## Catalog

Rows, splits, and zero-shot accuracy of the base checkpoint (`convaiinnovations/laya`, English, no
fine-tuning) on each test split. The zero-shot numbers are the "before" picture for fine-tuning.
`build_all.py` and `eval_zero_shot.py` regenerate the tables below.

<!-- catalog:start -->
### General and public sector

| set | fields | questions | rows | train / val / test | zero-shot mean acc (test) |
|---|---|---|---|---|---|
| [benefits-eligibility-intake](benefits-eligibility-intake/README.md) | message | program (choice), urgent_hardship (noul), missing_info (noul) | 840 | 554 / 76 / 210 | 0.67 |
| [content-moderation](content-moderation/README.md) | text | toxic (noul), harassment (noul), threat (noul), spam (noul), severity (score) | 820 | 528 / 72 / 220 | 0.71 |
| [data-quality-record-check](data-quality-record-check/README.md) | schema, record | is_valid (noul), issue (choice), pii_in_text (noul) | 880 | 581 / 79 / 220 | 0.49 |
| [email-triage-phishing](email-triage-phishing/README.md) | sender, subject, body | route (choice), phishing (noul), spam (noul), needs_reply (noul), urgency (score) | 856 | 517 / 71 / 268 | 0.53 |
| [invoice-ap-exceptions](invoice-ap-exceptions/README.md) | invoice, purchase_order | exception (choice), needs_approval (noul), fraud_risk (score) | 720 | 422 / 58 / 240 | 0.34 |
| [llm-model-router](llm-model-router/README.md) | prompt | difficulty (score), domain (choice), needs_tools (noul), is_sensitive (noul) | 815 | 504 / 69 / 242 | 0.70 |
| [public-records-foia-routing](public-records-foia-routing/README.md) | request | department (choice), request_type (choice), contains_pii (noul), complexity (score) | 869 | 582 / 79 / 208 | 0.63 |
| [public-sector-311-intake](public-sector-311-intake/README.md) | channel, request | service (choice), emergency (noul), location_present (noul), priority (score) | 918 | 602 / 82 / 234 | 0.63 |
| [rag-relevance-filter](rag-relevance-filter/README.md) | query, passage | relevant (noul), answers (noul), relevance (score) | 792 | 523 / 71 / 198 | 0.65 |
| [sales-lead-qualification](sales-lead-qualification/README.md) | product, lead | budget (noul), authority (noul), need (noul), timing (noul), stage (choice), fit (score) | 810 | 594 / 81 / 135 | 0.56 |
| [security-incident-triage](security-incident-triage/README.md) | source, alert | category (choice), true_positive (noul), severity (score), needs_escalation (noul) | 832 | 526 / 72 / 234 | 0.47 |
| [support-ticket-triage](support-ticket-triage/README.md) | subject, body | queue (choice), urgency (score), churn_risk (noul), refund_requested (noul), needs_human (noul) | 864 | 549 / 75 / 240 | 0.70 |

### Higher education

| set | fields | questions | rows | train / val / test | zero-shot mean acc (test) |
|---|---|---|---|---|---|
| [he-accommodation-request-routing](he-accommodation-request-routing/README.md) | request | type (choice), documentation_mentioned (noul), time_sensitive (noul) | 796 | 490 / 67 / 239 | 0.68 |
| [he-admissions-inquiry](he-admissions-inquiry/README.md) | message | stage (choice), topic (choice), hot_lead (noul) | 972 | 635 / 87 / 250 | 0.73 |
| [he-course-evaluation-comments](he-course-evaluation-comments/README.md) | comment | theme (choice), sentiment (score), actionable (noul), inappropriate (noul) | 863 | 545 / 74 / 244 | 0.55 |
| [he-early-alert](he-early-alert/README.md) | note | academic_risk (noul), attendance (noul), financial_stress (noul), wellbeing_concern (noul), risk (score) | 875 | 550 / 75 / 250 | 0.69 |
| [he-ferpa-sensitive](he-ferpa-sensitive/README.md) | text | protected_record (noul), record_type (choice) | 778 | 447 / 61 / 270 | 0.42 |
| [he-financial-aid-triage](he-financial-aid-triage/README.md) | message | topic (choice), deadline_sensitive (noul), sensitive_info (noul) | 809 | 474 / 65 / 270 | 0.72 |
| [he-it-helpdesk](he-it-helpdesk/README.md) | ticket | category (choice), outage (noul), priority (score) | 862 | 547 / 75 / 240 | 0.75 |
| [he-research-admin](he-research-admin/README.md) | email | topic (choice), deadline (noul) | 754 | 480 / 66 / 208 | 0.71 |
| [he-safety-escalation](he-safety-escalation/README.md) | message | escalate_now (noul), category (choice) | 728 | 434 / 59 / 235 | 0.47 |
| [he-student-services-routing](he-student-services-routing/README.md) | message | office (choice), urgency (score), needs_human (noul) | 791 | 504 / 69 / 218 | 0.56 |

22 sets, 18244 rows.

### Per-question zero-shot accuracy

Test split, base checkpoint. Majority = always answering the most common test label.

| set | question | accuracy | majority baseline |
|---|---|---|---|
| benefits-eligibility-intake | program | 0.78 | 0.14 |
| benefits-eligibility-intake | urgent_hardship | 0.80 | 0.60 |
| benefits-eligibility-intake | missing_info | 0.43 | 0.58 |
| content-moderation | toxic | 0.80 | 0.73 |
| content-moderation | harassment | 0.70 | 0.71 |
| content-moderation | threat | 0.80 | 0.85 |
| content-moderation | spam | 0.96 | 0.84 |
| content-moderation | severity | 0.29 | 0.42 |
| data-quality-record-check | is_valid | 0.48 | 0.55 |
| data-quality-record-check | issue | 0.32 | 0.46 |
| data-quality-record-check | pii_in_text | 0.68 | 0.64 |
| email-triage-phishing | route | 0.47 | 0.31 |
| email-triage-phishing | phishing | 0.63 | 0.79 |
| email-triage-phishing | spam | 0.80 | 0.90 |
| email-triage-phishing | needs_reply | 0.52 | 0.69 |
| email-triage-phishing | urgency | 0.24 | 0.58 |
| he-accommodation-request-routing | type | 0.65 | 0.17 |
| he-accommodation-request-routing | documentation_mentioned | 0.71 | 0.53 |
| he-accommodation-request-routing | time_sensitive | 0.66 | 0.58 |
| he-admissions-inquiry | stage | 0.76 | 0.22 |
| he-admissions-inquiry | topic | 0.62 | 0.22 |
| he-admissions-inquiry | hot_lead | 0.83 | 0.75 |
| he-course-evaluation-comments | theme | 0.48 | 0.21 |
| he-course-evaluation-comments | sentiment | 0.39 | 0.29 |
| he-course-evaluation-comments | actionable | 0.42 | 0.59 |
| he-course-evaluation-comments | inappropriate | 0.89 | 0.79 |
| he-early-alert | academic_risk | 0.74 | 0.68 |
| he-early-alert | attendance | 0.85 | 0.68 |
| he-early-alert | financial_stress | 0.82 | 0.68 |
| he-early-alert | wellbeing_concern | 0.74 | 0.63 |
| he-early-alert | risk | 0.28 | 0.36 |
| he-ferpa-sensitive | protected_record | 0.40 | 0.74 |
| he-ferpa-sensitive | record_type | 0.45 | 0.15 |
| he-financial-aid-triage | topic | 0.83 | 0.11 |
| he-financial-aid-triage | deadline_sensitive | 0.64 | 0.53 |
| he-financial-aid-triage | sensitive_info | 0.68 | 0.62 |
| he-it-helpdesk | category | 0.80 | 0.20 |
| he-it-helpdesk | outage | 0.92 | 0.70 |
| he-it-helpdesk | priority | 0.52 | 0.30 |
| he-research-admin | topic | 0.76 | 0.12 |
| he-research-admin | deadline | 0.65 | 0.53 |
| he-safety-escalation | escalate_now | 0.49 | 0.50 |
| he-safety-escalation | category | 0.44 | 0.33 |
| he-student-services-routing | office | 0.63 | 0.16 |
| he-student-services-routing | urgency | 0.64 | 0.46 |
| he-student-services-routing | needs_human | 0.41 | 0.69 |
| invoice-ap-exceptions | exception | 0.19 | 0.47 |
| invoice-ap-exceptions | needs_approval | 0.53 | 0.53 |
| invoice-ap-exceptions | fraud_risk | 0.29 | 0.67 |
| llm-model-router | difficulty | 0.33 | 0.35 |
| llm-model-router | domain | 0.83 | 0.24 |
| llm-model-router | needs_tools | 0.79 | 0.76 |
| llm-model-router | is_sensitive | 0.85 | 0.75 |
| public-records-foia-routing | department | 0.77 | 0.18 |
| public-records-foia-routing | request_type | 0.83 | 0.60 |
| public-records-foia-routing | contains_pii | 0.64 | 0.57 |
| public-records-foia-routing | complexity | 0.28 | 0.52 |
| public-sector-311-intake | service | 0.73 | 0.15 |
| public-sector-311-intake | emergency | 0.77 | 0.77 |
| public-sector-311-intake | location_present | 0.54 | 0.73 |
| public-sector-311-intake | priority | 0.47 | 0.31 |
| rag-relevance-filter | relevant | 0.59 | 0.73 |
| rag-relevance-filter | answers | 0.83 | 0.73 |
| rag-relevance-filter | relevance | 0.52 | 0.27 |
| sales-lead-qualification | budget | 0.77 | 0.67 |
| sales-lead-qualification | authority | 0.61 | 0.61 |
| sales-lead-qualification | need | 0.57 | 0.52 |
| sales-lead-qualification | timing | 0.70 | 0.65 |
| sales-lead-qualification | stage | 0.44 | 0.33 |
| sales-lead-qualification | fit | 0.30 | 0.33 |
| security-incident-triage | category | 0.70 | 0.22 |
| security-incident-triage | true_positive | 0.38 | 0.67 |
| security-incident-triage | severity | 0.23 | 0.33 |
| security-incident-triage | needs_escalation | 0.57 | 0.56 |
| support-ticket-triage | queue | 0.80 | 0.20 |
| support-ticket-triage | urgency | 0.52 | 0.50 |
| support-ticket-triage | churn_risk | 0.77 | 0.68 |
| support-ticket-triage | refund_requested | 0.85 | 0.82 |
| support-ticket-triage | needs_human | 0.54 | 0.62 |
<!-- catalog:end -->

## Higher education

The `he-*` sets cover the front doors of a campus: student services, financial aid, admissions, IT, the
disability services office, the sponsored research office, course evaluations, and two sets that sit
in front of people who look after students.

| set | what it decides | who acts on it |
|---|---|---|
| he-student-services-routing | which office, urgency, needs a person | office queues |
| he-financial-aid-triage | aid topic, near deadline, sensitive financial data | aid counselors; sensitive messages stay out of LLM prompts |
| he-admissions-inquiry | funnel stage, topic, hot lead | admissions counselors via the CRM |
| he-early-alert | academic, attendance, financial, wellbeing signals, outreach level | advisors only |
| he-safety-escalation | needs a trained person now, and why | on-call staff and crisis resources |
| he-course-evaluation-comments | theme, sentiment, actionable, inappropriate | institutional research, chairs |
| he-ferpa-sensitive | protected education record or directory information | DLP before text leaves a system or reaches an LLM |
| he-accommodation-request-routing | accommodation type, documentation mentioned, time-sensitive | accessibility services coordinators |
| he-it-helpdesk | IT area, many-user outage, priority | help desk and on-call |
| he-research-admin | sponsored research topic, upcoming deadline | pre-award, post-award, compliance teams |

Two sets need care in how they are deployed:

- **he-early-alert** is decision support. It orders an advisor's caseload; it never places holds,
  changes grades or aid, starts conduct processes, or messages a student on its own.
- **he-safety-escalation** is high-recall routing to people. Tune its threshold for recall on val,
  track the false-negative rate on test (reported in its README), and never send an automated reply to
  the student. Trained staff and crisis resources decide and respond.

## What is in each folder

```
<set>/
  generate.py      deterministic, seeded, stdlib-only generator; rewrites the three JSONL files
  train.jsonl      training rows
  val.jsonl        never trained on; used for temperature fitting and serving thresholds
  test.jsonl       held-out phrasing families (see below)
  zero_shot.json   base-checkpoint accuracy on test, per question
  README.md        purpose, fields, labeling rules, balance, generation notes, limitations
```

Row format, the same one the fine-tune pipeline reads:

```json
{"id": "311-train-water-leak-00012",
 "state": {"channel": "text message", "request": "water bubbling up from the ground at 4410 Elm St ..."},
 "questions": {"service": {"type": "choice", "instructions": "Which city service should handle ...", "criteria": {...}}, ...},
 "gold": {"service": "water", "emergency": false, "location_present": true, "priority": 1},
 "family": "water/leak"}
```

Gold is `true`/`false` for noul questions, an option key for choice questions, and a 0-based level
index for score questions (0 = lowest). `family` is the phrasing family the row came from; the
fine-tune evaluator uses it for per-family breakdowns.

Every row carries the pack's questions verbatim. A fine-tuned checkpoint learns those literal
instruction strings, so inference must ask the same questions. Build them with
`laya_mcp.packs.get_pack("<set>")` rather than retyping them.

## How the test split works

Generators write examples in phrasing families. A family is one hand-written scenario with its own
templates and gold labels. Test holds out whole families, never individual rows, and each set's generator pins the
held-out list so that every label of every question appears in test. A model that memorizes templates
scores well on val and poorly on test; the gap between the two is the honest measure of how much it
generalizes. `build_all.py` also rejects any state that appears in both test and train/val.

## Fine-tuning on a set

Each set has a recipe in `finetune/recipes/<set>.json` that points at `datasets/accelerators/<set>`:

```
python -m finetune.pipeline --recipe public-sector-311-intake
python -m finetune.pipeline --recipe public-sector-311-intake --strategy full      # encoder too; more VRAM
python -m finetune.pipeline --recipe public-sector-311-intake --data my_rows.jsonl  # add your own rows
```

The recipes default to `strategy: head` (encoder frozen), which is fast and hard to overfit. On these
narrow label sets `--strategy full` usually buys more accuracy if the GPU has room. `--data` takes extra
JSONL rows in the same format; rows may omit `questions`, in which case the recipe's pack questions are
used.

## Regenerating and validating

```
python datasets/accelerators/build_all.py                # regenerate every set, validate, refresh the catalog
python datasets/accelerators/build_all.py --determinism  # also prove each generator is reproducible
python datasets/accelerators/eval_zero_shot.py           # re-measure zero-shot accuracy (needs a Laya server)
```

`build_all.py` checks that every row's questions equal the pack exactly, the state has exactly the
pack's fields, gold labels are valid for the question type, ids are unique, test does not leak into
train/val, split sizes are sane, and each question has more than one label in test. It exits non-zero
on any failure.

Changing a question's wording in `accelerator_packs.py` changes the contract, so rerun `build_all.py`,
`eval_zero_shot.py`, and the fine-tune.

## Data safety

All content is synthetic. Names come from a list of placeholder surnames (Doe, Roe, Sample, Example,
Placeholder, ...), phone numbers use the fictional 555-01xx range, email addresses and domains use
`example.com`, `example.org`, `example.net` or invented look-alikes of those, government ID numbers use
the never-issued 000 area number, IP addresses come from the documentation ranges (192.0.2.0/24,
198.51.100.0/24, 203.0.113.0/24) or private space, and companies, agencies, and counties are invented.
No row is derived from real tickets, emails, requests, or records.

## Shared limitations

- Template generation repeats sentence structures inside a family. Real traffic is more varied, has
  more multi-issue items, and includes languages other than English.
- Label policies (priority, severity, escalation, approval) encode one reasonable policy per use case.
  Each set's README states the rules; relabel to match your SLAs before relying on them.
- Zero-shot numbers come from one base checkpoint revision (recorded in each `zero_shot.json`) and the
  server's automatic English routing.
