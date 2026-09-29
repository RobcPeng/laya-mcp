# data-quality-record-check

Checks one record against its table's rules, the way an ingest pipeline decides between the silver table
and a quarantine table: is the record valid, what is the main problem, and does a free-text field leak
personal data. The schema travels in the state, so one checkpoint covers many tables. Pack:
`data-quality-record-check` in `laya_mcp/accelerator_packs.py`.

Where it fits: Deterministic checks (types, ranges, regexes, CHECK constraints) belong in the pipeline
itself, for example as declarative pipeline expectations. This set is for the cases where rules live in
prose, schemas vary per source, or you want a PII screen on free text before it lands in a shared table.

## Fields

| field | content |
|---|---|
| `schema` | the table name and one rule per field, rendered either as a bullet list or as `field -- rule` lines plus SQL-style `CHECK (...)` constraints |
| `record` | the record as a JSON string (spaced or compact) |

## Questions and labels

| id | type | labels |
|---|---|---|
| `is_valid` | noul | true when the record passes every rule |
| `issue` | choice | `none`, `missing_value`, `wrong_type`, `out_of_range`, `bad_format`, `inconsistent` |
| `pii_in_text` | noul | true when the free-text field (notes, comment, description, manager_notes, adjuster_comments, feedback_text, driver_notes, caseworker_notes) holds an email address, phone number, SSN, date of birth, home address, or license number |

Labeling rules:

- Every invalid record has exactly one corruption, so `issue` has one right answer and
  `is_valid = (issue == none)`. Corruptions that would break a second rule are paired with a fix-up
  (changing `quantity` also recomputes `total`).
- `missing_value`: a required key is absent, `null`, or `""`. `wrong_type`: a number sent as a string
  (`"12"`, `"$84,000"`, `"7,579.73 USD"`), a word for a number, a float for an integer, a list.
  `out_of_range`: a number outside its bounds or a value not in the allowed set. `bad_format`: a
  malformed date (`03/14/2025`), id, email, zip, URL, or code. `inconsistent`: two fields contradict each
  other (end before start, a close time on a ticket that is still open, total not equal to quantity x price, paid
  more than billed, revenue on a page view).
- `pii_in_text` is independent of validity and looks only at the free-text field. Structured fields such
  as `work_email` do not count. Look-alikes are false: order numbers, SKUs, tracking numbers, ticket and
  case ids, invoice numbers, lot numbers, timestamps, firmware serials, internal extensions.

## Size and balance

880 rows: train 581, val 79, test 220.

| question | balance (all splits) |
|---|---|
| is_valid | false 480, true 400 |
| issue | none 400; missing_value, wrong_type, out_of_range, bad_format, inconsistent 96 each |
| pii_in_text | false 565, true 315 |

## How it was generated

`generate.py` (stdlib only, seed 1101) defines eight schemas: orders, sensor telemetry, 311 service
tickets, HR employees, health claims, web events, shipments, and benefits applications. Each has a valid
record generator and 1-4 hand-written corruptions per issue type. Per schema it emits 50 valid records
and 12 per issue type. The free-text field is filled with fake personal data (38%), a look-alike
identifier, plain operational prose, an empty string, `null`, or left out. Personal data uses
fake-surname names, 555-01xx phones, example.com/.org/.net emails, and 000-xx SSNs.

Test holds out two whole schemas (`claims`, `web_events`), so test measures transfer to tables and field
names the model never saw. Regenerate with
`python datasets/accelerators/data-quality-record-check/generate.py`.

## Zero-shot base accuracy (test)

<!-- zero-shot:start -->
Base checkpoint, no fine-tuning, on the 220-row test split (held-out phrasing families). Majority = always answering the most common test label.

| question | type | accuracy | majority | within one level |
|---|---|---|---|---|
| is_valid | noul | 0.48 | 0.55 |  |
| issue | choice | 0.32 | 0.46 |  |
| pii_in_text | noul | 0.68 | 0.64 |  |

Mean accuracy across questions: 0.49. Server revision: 55cf4c4ebb4ebe31b2550e8bdf3bd21b99753851.
<!-- zero-shot:end -->

## Known limitations

- One issue per record. Real bad records often have several; the pack asks for the main one, and this
  set does not teach how to rank them.
- Some corruptions are easy to spot by shape (US-style dates, `"$"` in numbers). Subtle ones such as a
  total off by one cent, or a date that is valid but wrong, are underrepresented.
- Arithmetic checks (`total = quantity x unit_price`) are hard for an encoder model. Use Laya for the
  fuzzy parts (rules in prose, PII in text) and compute arithmetic and regex rules in code.
- Records are flat JSON with 7-9 fields. Nested structures and wide tables (50+ columns) will exceed
  the 512-token window; check a projection of the relevant fields.
- Free text in the look-alike pool is not always topical for the table (an invoice note on a sensor
  reading). This does not affect labels.
