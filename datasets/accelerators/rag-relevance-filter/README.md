# rag-relevance-filter

Filters or reranks retrieved passages in a RAG pipeline: is the passage on the query's subject, does it
contain the answer, and how useful is it. Use it after vector search to drop off-topic chunks before they
reach the LLM, or to reorder the top-k. Pack: `rag-relevance-filter` in `laya_mcp/accelerator_packs.py`.

## Fields

| field | content |
|---|---|
| `query` | a user question, sometimes two questions joined ("How do I reset the B200? And how long is the warranty?"), with casual casing, typos, and preambles |
| `passage` | a retrieved chunk: optional doc header, breadcrumb, chunk counter or FAQ layout, 1-3 sentences or bullets, sometimes a leading `...` or a sentence cut off at the chunk boundary |

## Questions and labels

| id | type | labels |
|---|---|---|
| `relevant` | noul | true when the passage is about the same subject as the query (relevance >= 1) |
| `answers` | noul | true when the passage contains everything the query asks for (relevance = 3) |
| `relevance` | score | 0 irrelevant, 1 related (same subject, does not help), 2 partial (answers part), 3 complete |

Labeling rules. The generator knows which facts each passage contains, so labels follow mechanically:

- 3 complete: the passage states the asked fact (or both facts of a two-part query). It may also carry
  other facts about the same entity and a filler line.
- 2 partial: a two-part query where the passage states only one of the two facts.
- 1 related: the passage covers the same entity but a different attribute (asked about the warranty,
  got the reset steps), or the same attribute of a close sibling entity with heavy word overlap (asked
  about the B400 warranty, got the B200 warranty; asked about PTO, got parental leave).
- 0 irrelevant: a fact from a different domain, or a keyword-overlap distractor that shares words with
  the query but not its subject ("Leave No Trace" for a leave-policy query, "warranty deed" for a router
  warranty query, "vacuum cleaner filter" for the VACUUM command).

## Size and balance

792 rows: train 523, val 71, test 198.

| question | balance (all splits) |
|---|---|
| relevant | false 216, true 576 |
| answers | false 576, true 216 |
| relevance | 0: 216, 1: 216, 2: 144, 3: 216 |

## How it was generated

`generate.py` (stdlib only, seed 707) holds an invented knowledge base of 6 domains (HR policy, consumer
product support docs, lakehouse/data engineering docs, city and county program rules, a health-plan
member FAQ, IT service desk articles) x 4 entities x 3 attributes. Each attribute has 3 hand-written
question phrasings and one answer sentence. Per entity it emits, for each attribute, two complete rows,
two related rows, and two irrelevant rows; and for each attribute pair, one complete two-part row, two
partial rows, one related row, and one irrelevant row. Passages get a random header style (markdown
heading, breadcrumb, chunk counter, section number, none), a random layout (prose, bullets, FAQ Q/A), and
optional filler and cut-off tails. Queries get preambles, casing changes, dropped question marks, and
typos.

Test holds out the whole health-plan domain and two more entities (`product/b400`, `dataeng/vacuum`), so
test covers an unseen domain and unseen entities. Regenerate with
`python datasets/accelerators/rag-relevance-filter/generate.py`.

## Zero-shot base accuracy (test)

<!-- zero-shot:start -->
Base checkpoint, no fine-tuning, on the 198-row test split (held-out phrasing families). Majority = always answering the most common test label.

| question | type | accuracy | majority | within one level |
|---|---|---|---|---|
| relevant | noul | 0.59 | 0.73 |  |
| answers | noul | 0.83 | 0.73 |  |
| relevance | score | 0.52 | 0.27 | 0.87 |

Mean accuracy across questions: 0.65. Server revision: 55cf4c4ebb4ebe31b2550e8bdf3bd21b99753851.
<!-- zero-shot:end -->

## Known limitations

- The knowledge base is small (72 facts), so passages repeat across rows with different headers and
  queries. Fine-tune on it to teach the task shape, then add pairs mined from your own retriever logs:
  a few hundred labeled (query, top-k chunk) pairs from the target corpus matter more than more synthetic
  rows.
- Partial answers come only from two-part queries. Real partial chunks also include hedged answers,
  answers split across chunk boundaries, and stale versions of a fact; these are not modeled.
- Passages are short (1-3 sentences). Production chunks of 300-800 tokens put the answer among more
  noise, and long chunks can be truncated at the model's 512-token limit together with the query.
- Facts are invented and self-consistent; the set does not test contradictory or outdated passages.
- English only.
