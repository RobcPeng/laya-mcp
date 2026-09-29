# he-accommodation-request-routing

Routes requests sent to a campus disability or accessibility services office by accommodation type, and
flags whether the request mentions documentation and whether it is time-sensitive. It sorts a queue for
accessibility coordinators; it does not approve or deny anything. Pack:
`he-accommodation-request-routing` in `laya_mcp/accelerator_packs.py`.

## Fields

| field | content |
|---|---|
| `request` | the request as it arrives: a portal form with a student ID, a student email, a parent email, a message forwarded by staff, a faculty question, or bare text |

## Questions and labels

| id | type | labels |
|---|---|---|
| `type` | choice | `testing`, `housing`, `course_materials`, `attendance`, `animal`, `other` |
| `documentation_mentioned` | noul | true when a document is referenced: a doctor's letter, an IEP or 504 plan, diagnosis paperwork, an existing accommodation letter, records the provider will send |
| `time_sensitive` | noul | true when an exam, move-in, class start, or deadline falls within the next two weeks |

Labeling rules:

- Rescheduling exams around flare-ups is `testing`; flexibility with attendance or assignment deadlines
  is `attendance`. Captions, transcripts, interpreters, and alternative formats are `course_materials`.
  Note-taking, recording lectures, parking, dining, and lab stations are `other`.
- Emotional support animals and service animals are `animal`. Asking to bring an ordinary pet to the
  dorms ("she's just my pet") is `housing`, because it is a housing policy question and not a disability
  accommodation, and it never has documentation.
- Faculty questions about implementing an accommodation that already exists (extended time on online
  quizzes, captioning their videos) take the type of that accommodation and always have
  `documentation_mentioned = true`, since they reference the accommodation letter.
- Near misses for documentation are false: "my doctor suggested I ask", "I see a specialist for this",
  "my counselor told me to reach out" mention a person, not a document.
- Near misses for timing are false: "for next semester", "finals aren't until December (it's September
  now)", "I had a hard time with exams last year". Timing sentences that count give a concrete date
  inside two weeks ("my midterm is this Thursday", "move-in is Aug 20 and today is Aug 12").

## Size and balance

796 rows: train 490, val 67, test 239.

| question | balance (all splits) |
|---|---|
| type | animal 80, attendance 119, course_materials 119, housing 159, other 159, testing 160 |
| documentation_mentioned | false 410, true 386 |
| time_sensitive | false 490, true 306 |

## How it was generated

`generate.py` (stdlib only, seed 4504) holds 20 hand-written request families across the six types,
with slots for course codes, residence halls, and conditions described in general, respectful terms
("a chronic health condition", "low vision", "ADHD"). The two flags are composed independently of the
type. Each row gets a documentation sentence (45%), a documentation near miss (25%), or neither, and a
timing sentence (40%), a timing near miss (30%), or neither, in shuffled order. Rows are wrapped as a
portal form, a student email, a parent email, a staff forward, a faculty email, or bare text, then get
light typos and casing noise. Student IDs look like `S00123456`, email addresses use `example.edu`, and
institution names are invented.

Test holds out 6 whole families, one per type: faculty implementing extended time, the ordinary-pet
housing question, caption requests, attendance for medical treatment, service dogs, and dining.
Regenerate with `python datasets/accelerators/he-accommodation-request-routing/generate.py`.

## Zero-shot base accuracy (test)

<!-- zero-shot:start -->
Base checkpoint, no fine-tuning, on the 239-row test split (held-out phrasing families). Majority = always answering the most common test label.

| question | type | accuracy | majority | within one level |
|---|---|---|---|---|
| type | choice | 0.65 | 0.17 |  |
| documentation_mentioned | noul | 0.71 | 0.53 |  |
| time_sensitive | noul | 0.66 | 0.58 |  |

Mean accuracy across questions: 0.68. Server revision: 55cf4c4ebb4ebe31b2550e8bdf3bd21b99753851.
<!-- zero-shot:end -->

## Known limitations

- One accommodation type per request. Real requests often ask for several (extended time and a
  note-taker); route on the primary one or split the request.
- Time sensitivity depends on dates written in the text. Real messages rarely say "today is Aug 12";
  in production, put the received date in the state (for example, prefix the request with it).
- Conditions are named only in general terms. The set does not teach anything about specific diagnoses
  and should not be used to infer them.
- This is routing support for coordinators. Eligibility decisions stay with the office's interactive
  process and its staff.
