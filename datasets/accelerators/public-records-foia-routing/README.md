# public-records-foia-routing

Triage for a city or county open-records (FOIA) inbox: which department holds the records, whether the
submission is a records request at all or a complaint, service request, or question sent to the records
address, whether it carries personal data about a private individual, and how much work fulfilling it
will take. Pack: `public-records-foia-routing` in `laya_mcp/accelerator_packs.py`.

## Fields

| field | content |
|---|---|
| `request` | the submission as received: statute-citing letter, casual email, portal form, attorney letter, journalist request, forwarded portal notice, or a one-liner, with signature or contact block |

## Questions and labels

| id | type | labels |
|---|---|---|
| `department` | choice | `police`, `fire_ems`, `public_works`, `planning_zoning`, `finance`, `human_resources`, `clerk`, `parks`, `health` |
| `request_type` | choice | `records_request`, `complaint`, `service_request`, `question` |
| `contains_pii` | noul | true when the text has a private person's home address, phone number, date of birth, or government ID (driver's license, SSN) |
| `complexity` | score | 0 one known document, 1 a few records from one office, 2 many records / long date range / several offices, 3 large volume needing heavy review or redaction |

Labeling rules:

- `department` is the office that holds the records sought. For complaints, service requests, and
  questions it is the office the submission is about (a rude officer is `police`, a late council agenda
  is `clerk`). Complaints about the records process itself go to `clerk`.
- `request_type` follows what the sender wants, not the words used. "Pursuant to the open records act,
  fix the broken swing" is a `service_request`; "pursuant to the act, I demand my permit denial be
  reversed" is a `complaint`; "does the city keep records of vendor payments, and how would I request
  them?" is a `question`; "do you have X? if so send it" is a `records_request`.
- `contains_pii` is decided by the contact line and by requests for the requester's own records (which
  include DOB, SSN in the invalid 000-xx-xxxx form, or a home address). A name alone, a law-firm
  signature, a case or permit number, and business, project, or block-level locations are not PII here.
- `complexity` comes from the record object bank (four levels per department). Complaints, service
  requests, and questions are always 0 because there are no records to produce.

## Size and balance

869 rows: train 582, val 79, test 208.

| question | balance (all splits) |
|---|---|
| department | clerk 114, finance 77, fire_ems 88, health 92, human_resources 96, parks 91, planning_zoning 111, police 109, public_works 91 |
| request_type | records_request 536, complaint 131, question 106, service_request 96 |
| contains_pii | false 517, true 352 |
| complexity | 0: 436, 1: 155, 2: 143, 3: 135 |

Complexity level 0 is large because every non-records row is 0; among records requests the four levels
are close to even.

## How it was generated

`generate.py` (stdlib only, seed 4417). Records requests cross nine writing styles (statute letter,
casual, portal form, attorney, journalist with fee-waiver ask, researcher or nonprofit, one-liner,
forwarded portal notice, worried resident) with a record-object bank of 9 departments x 4 complexity
levels x 3 objects (incident reports, body-camera video, 911 audio, salary data, council minutes,
inspection reports, bid tabulations, and so on), filled with random dates, case numbers, blocks,
vendors, and projects. Extras vary format preferences, fee caps, fee waivers, and purpose statements.
Two "own records" families add requests for the requester's own report or personnel file. 28
hand-written non-records families cover complaints, service requests, and questions, including the
disguised near-misses above. A contact line (38% with PII) is appended. Noise: typos and lowercase
chat style, heavier in casual and one-liner styles.

Test holds out 10 whole families: the journalist and forwarded-portal styles, one own-records family,
three complaint families (records delays, EMS response, disguised complaint), two service families
(disguised parks request, patrol request), and two question families.

## Zero-shot base accuracy (test)

<!-- zero-shot:start -->
Base checkpoint, no fine-tuning, on the 208-row test split (held-out phrasing families). Majority = always answering the most common test label.

| question | type | accuracy | majority | within one level |
|---|---|---|---|---|
| department | choice | 0.77 | 0.18 |  |
| request_type | choice | 0.83 | 0.60 |  |
| contains_pii | noul | 0.64 | 0.57 |  |
| complexity | score | 0.28 | 0.52 | 0.86 |

Mean accuracy across questions: 0.63. Server revision: 55cf4c4ebb4ebe31b2550e8bdf3bd21b99753851.
<!-- zero-shot:end -->

## Known limitations

- Department boundaries follow a generic mid-size US city. Many places split functions differently
  (utility billing under public works, health at the county, a separate records office). Rename or
  merge labels to match the customer's org chart and relabel.
- One department per request. Real requests often span several ("all emails between police and public
  works about X"); these land at complexity 2-3 here but still carry one department label.
- `contains_pii` does not treat email addresses or names as PII, and bare property addresses are
  avoided in the record objects to keep the label clean. Real inboxes are messier.
- Statute names are generic ("the state Open Records Act"); no state-specific deadlines, exemptions,
  or fee rules are modeled.
