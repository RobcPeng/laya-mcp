# he-ferpa-sensitive

DLP for education records. Checks whether a text snippet contains FERPA-protected information about an
identifiable student, as opposed to directory information or no student information, and names the kind
of record. Use it before text leaves a system of record: before a staff member pastes it into an LLM,
posts it in a shared channel, or attaches it to a ticket. Pack: `he-ferpa-sensitive` in
`laya_mcp/accelerator_packs.py`.

This is a screening aid, not legal advice. What counts as directory information varies by institution
(each school publishes its own designation, and students can opt out), so align the `directory_only`
rules with your registrar's policy before use.

## Fields

| field | content |
|---|---|
| `text` | a snippet as staff write or paste it: faculty email, spreadsheet rows, meeting notes, chat message, letter, ticket comment, or text pasted into a chat assistant |

## Questions and labels

| id | type | labels |
|---|---|---|
| `protected_record` | noul | true iff `record_type` is `grades`, `discipline`, `financial`, `health_disability`, or `identifiers` |
| `record_type` | choice | `grades`, `discipline`, `financial`, `health_disability`, `identifiers`, `directory_only`, `none` |

Labeling rules:

- Protected information must be tied to an identifiable student (a name, or a name plus ID).
- `grades` includes GPA, course grades, exam scores, and academic standing (probation, suspension).
  A student writing about their own grade is still labeled `grades`. The text is an education record
  about an identifiable student, and it should not be pasted into an outside tool either.
- `identifiers` is a student ID or SSN linked to a named student, with no other record content. SSNs are
  synthetic (000-xx-xxxx).
- `directory_only`: name, major, class year, enrollment status, dates of attendance, degrees, published
  honors, club rosters, and example.edu email addresses.
- `none`: aggregate statistics ("the section average was 74%"), FERPA policy and training text, course
  descriptions, operational notices, and blank forms or mail-merge templates.

## Size and balance

778 rows: train 447, val 61, test 270.

| question | balance (all splits) |
|---|---|
| protected_record | false 258, true 520 |
| record_type | directory_only 120, discipline 80, financial 80, grades 200, health_disability 80, identifiers 80, none 138 |

## How it was generated

`generate.py` (stdlib only, seed 1974) holds 20 families, one kind of snippet each, with 2-7 templates.
Slots fill fake names, majors, courses, student IDs (S + 8 digits), GPAs consistent with the stated
standing, dollar amounts, and terms. Rows get a wrapper (email, Slack-style channel, meeting notes, ticket
comment, "pasted into chat assistant") and some get typos.

Test holds out 8 whole families: a student asking about their own grade, chat gossip about discipline,
account balances, counseling and hospitalization notes, ID-number rosters, club rosters, and blank
forms. Regenerate with `python datasets/accelerators/he-ferpa-sensitive/generate.py`.

## Zero-shot base accuracy (test)

<!-- zero-shot:start -->
Base checkpoint, no fine-tuning, on the 270-row test split (held-out phrasing families). Majority = always answering the most common test label.

| question | type | accuracy | majority | within one level |
|---|---|---|---|---|
| protected_record | noul | 0.40 | 0.74 |  |
| record_type | choice | 0.45 | 0.15 |  |

Mean accuracy across questions: 0.42. Server revision: 55cf4c4ebb4ebe31b2550e8bdf3bd21b99753851.
<!-- zero-shot:end -->

## Known limitations

- One record type per snippet. Real text often mixes several (a grade and an accommodation); the label
  is the family's main type, and `protected_record` is what a DLP gate should act on.
- Short snippets. Long documents should be chunked; a record buried deep in a long email may be
  truncated away.
- Names are placeholder surnames; real names, nicknames, and partial identifiers ("the student in row 4
  of the probation list") are harder.
- Directory designations, opt-outs, and exceptions (school officials with a legitimate educational
  interest, health and safety emergencies) are policy decisions this model does not make.
