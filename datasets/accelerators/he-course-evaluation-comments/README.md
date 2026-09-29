# he-course-evaluation-comments

Codes open-ended end-of-term course evaluation comments by theme and sentiment, and flags comments that
give actionable feedback and comments that contain personal attacks or inappropriate remarks. Built for
institutional research offices and department chairs who read thousands of comments a term. Pack:
`he-course-evaluation-comments` in `laya_mcp/accelerator_packs.py`.

## Fields

| field | content |
|---|---|
| `comment` | one student comment, sometimes with the eval form's prompt in front ("What could be improved?") |

## Questions and labels

| id | type | labels |
|---|---|---|
| `theme` | choice | `instruction`, `workload`, `grading`, `materials`, `accessibility`, `organization`, `instructor_conduct`, `other` |
| `sentiment` | score | 0 very negative, 1 negative, 2 mixed or neutral, 3 positive, 4 very positive |
| `actionable` | noul | true when the comment names a specific change or a concrete problem |
| `inappropriate` | noul | true for personal attacks, insults, or remarks about someone's appearance |

Labeling rules:

- Theme is the main subject. A comment that praises lectures and criticizes exam fairness ("great
  lectures but the exams were unfair") is `grading`, because the complaint carries the point.
- Sentiment: 4 for strong praise, 3 for plain approval (including approval with a suggestion), 2 for mixed,
  neutral, or non-comments ("N/A"), 1 for criticism, and 0 for rants, insults, and reports of being
  harmed by the course (an accommodation that was never set up, an instructor mocking students).
  Sarcastic praise ("Loved spending every weekend on this class. Really.") is 1.
- `actionable` is true when a reader could act on the comment: "post slides before lecture", "the rubric
  for essays was never shared", "grades took a month to come back". Vague praise or complaints
  ("worst class ever", "loved it", "way too much work") are false.
- `inappropriate` covers insults aimed at a person ("clueless idiot", "lazy clown"), comments on the
  instructor's appearance, including ones meant as compliments ("super hot lol"), and similar. Harsh
  criticism of teaching is not inappropriate ("brutal but fair", "made fun of students' questions, that
  needs to stop"). A comment can be both actionable and inappropriate ("arrogant jerk who never posted
  the slides").
- Comments about the instructor's appearance, and about the room or facilities, are theme `other`.

## Size and balance

863 rows: train 545, val 74, test 244.

| question | balance (all splits) |
|---|---|
| theme | accessibility 73, grading 116, instruction 180, instructor_conduct 77, materials 97, organization 96, other 101, workload 123 |
| sentiment | 0: 195, 1: 319, 2: 120, 3: 127, 4: 102 |
| actionable | false 446, true 417 |
| inappropriate | false 713, true 150 |

## How it was generated

`generate.py` (stdlib only, seed 5150) holds 35 hand-written comment families across the eight themes,
each with 3-6 templates and fixed labels. Slots fill in course codes, instructor references ("Dr.
Sample", "the instructor", "our prof"), assignment types, and durations. Rows then get an optional eval
form prompt, an optional neutral lead-in ("Junior bio major here.") or tail ("That's all."), and a noise
pass: typos, all-lowercase, and ALL CAPS on some very negative comments. Insults are mild and contain no
slurs. Instructor names come from the fake-surname list in `_common.py`.

Test holds out 10 whole families: brutal-but-fair criticism, an insult with a concrete complaint,
sarcasm about workload, mixed grading comments, praise of materials, missed accommodations,
LMS-organization complaints, disrespectful conduct reports, appearance comments, and plain workload
approval. Regenerate with `python datasets/accelerators/he-course-evaluation-comments/generate.py`.

## Zero-shot base accuracy (test)

<!-- zero-shot:start -->
Base checkpoint, no fine-tuning, on the 244-row test split (held-out phrasing families). Majority = always answering the most common test label.

| question | type | accuracy | majority | within one level |
|---|---|---|---|---|
| theme | choice | 0.48 | 0.21 |  |
| sentiment | score | 0.39 | 0.29 | 0.74 |
| actionable | noul | 0.42 | 0.59 |  |
| inappropriate | noul | 0.89 | 0.79 |  |

Mean accuracy across questions: 0.55. Server revision: 55cf4c4ebb4ebe31b2550e8bdf3bd21b99753851.
<!-- zero-shot:end -->

## Known limitations

- One theme per comment. Real comments often cover two or three; a production coder may want to split
  comments into sentences first.
- Sentiment boundaries (positive vs very positive, negative vs very negative) are a judgment call and
  follow the rules above; expect disagreement with human coders at the edges.
- Comments are short (one to three sentences). Long multi-paragraph comments are not represented.
- English only, US higher-ed vocabulary (course codes, LMS names, "gen ed").
- Use the output to summarize and to route inappropriate comments for review before instructors see
  them. It should not feed into personnel decisions on its own.
