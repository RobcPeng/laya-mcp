# llm-model-router

Routes a prompt before any LLM sees it: how hard it is (cheap model vs strong model), which domain it
belongs to (pick a specialized model or prompt), whether it needs tools (send it to an agent), and whether
it carries personal, confidential, or regulated data (keep it on a private model). Pack:
`llm-model-router` in `laya_mcp/accelerator_packs.py`.

## Fields

| field | content |
|---|---|
| `prompt` | a user prompt, from "hi" to multi-paragraph requests with pasted code, tables, config, or fake records |

## Questions and labels

| id | type | labels |
|---|---|---|
| `difficulty` | score | 0 trivial (greeting, lookup, one-line edit), 1 easy (short well-known task), 2 moderate (multi-step reasoning or longer writing), 3 hard (expert reasoning, long code, careful analysis) |
| `domain` | choice | `coding`, `math`, `writing`, `data_analysis`, `knowledge`, `translation`, `chitchat` |
| `needs_tools` | noul | true when the answer needs live data (weather, prices, news, today's date), web search, running code, or an attached/uploaded file or database |
| `is_sensitive` | noul | true when the prompt itself contains fake-but-realistic personal data, patient details, credentials, or unreleased internal financials |

Labeling rules:

- Each phrasing family fixes all four labels; slot fills (language, topic, city, numbers, fake records)
  do not change them. Politeness prefixes and suffixes ("Keep it brief.", "Be thorough.") do not change
  difficulty.
- Hard negatives for `needs_tools`: historical facts ("What year did the Berlin Wall fall?"), analysis of
  data pasted into the prompt, and "explain" questions are false. "Attached", "uploaded", "run this",
  "current", "today", and "latest" requests are true.
- Hard negatives for `is_sensitive`: prompts about privacy, PII, HIPAA, or secret storage that contain no
  actual data ("What's considered personally identifiable information?") are false. A prompt is
  sensitive only when the data is in the prompt.
- Domain follows the task, not the topic: translating a legal contract is `translation`; computing a
  mean over pasted salaries is `math`; writing an RFP is `writing`.

## Size and balance

815 rows: train 504, val 69, test 242.

| question | balance (all splits) |
|---|---|
| difficulty | 0: 193, 1: 316, 2: 181, 3: 125 |
| domain | chitchat 105, coding 173, data_analysis 103, knowledge 128, math 108, translation 89, writing 109 |
| needs_tools | false 666, true 149 |
| is_sensitive | false 680, true 135 |

## How it was generated

`generate.py` (stdlib only, seed 808) holds 57 hand-written families across the 7 domains and 4
difficulty levels, including tool-needing, sensitive, and near-miss families. Each family has 2-6
templates with slots; sensitive slots are filled with obviously fake records (fake-surname names,
555-01xx phones, 000-xx SSNs, example.com emails, `sk_test_example_...` keys, invented quarterly
numbers). Non-chitchat prompts may get a prefix ("Quick question:", "urgent -") and a suffix; chitchat
gets emoticons and interjections. A noise pass adds typos and all-lowercase rows. Exact duplicates are
dropped.

Test holds out 17 whole families (at least one per domain, spanning all difficulty levels, plus unseen
tool, sensitive, and near-miss phrasings). Regenerate with
`python datasets/accelerators/llm-model-router/generate.py`.

## Zero-shot base accuracy (test)

<!-- zero-shot:start -->
Base checkpoint, no fine-tuning, on the 242-row test split (held-out phrasing families). Majority = always answering the most common test label.

| question | type | accuracy | majority | within one level |
|---|---|---|---|---|
| difficulty | score | 0.33 | 0.35 | 0.91 |
| domain | choice | 0.83 | 0.24 |  |
| needs_tools | noul | 0.79 | 0.76 |  |
| is_sensitive | noul | 0.85 | 0.75 |  |

Mean accuracy across questions: 0.70. Server revision: 55cf4c4ebb4ebe31b2550e8bdf3bd21b99753851.
<!-- zero-shot:end -->

## Known limitations

- Difficulty is one annotator's judgment encoded per family. Where you draw the cheap/strong line
  depends on your models; calibrate the threshold on the `difficulty` expected score with your own
  cost and quality measurements rather than using the argmax label.
- Prompts are short to medium. Real traffic has long multi-turn context, system prompts, and pasted
  documents that can exceed the 512-token window; route on the latest user turn or a truncated view.
- `is_sensitive` covers explicit data in the prompt. It does not judge sensitivity of topics (legal,
  medical advice without data) or data an agent would fetch later.
- The domain list is fixed at 7. Add labels (for example `legal`, `medical`, `sql`) by editing the pack
  and relabeling; keep choice questions at 20 options or fewer.
- English only; the translation domain contains English instructions naming target languages.
