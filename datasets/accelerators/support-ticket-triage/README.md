# support-ticket-triage

Routes an inbound customer support ticket (email or web form) to a queue, scores urgency, and flags
churn risk, refund requests, and tickets that should go to a human instead of an automated reply.
Pack: `support-ticket-triage` in `laya_mcp/accelerator_packs.py`.

## Fields

| field | content |
|---|---|
| `subject` | ticket subject line, sometimes `Re:`/`Fwd:` prefixed or uninformative ("help", "(no subject)") |
| `body` | the customer's message with greeting, signature, and in some rows a quoted support auto-reply or a forwarded-message header |

## Questions and labels

| id | type | labels |
|---|---|---|
| `queue` | choice | `billing`, `account_access`, `technical`, `shipping`, `cancellation`, `feature_request`, `how_to` |
| `urgency` | score | 0 low, 1 normal, 2 high (blocked or losing money), 3 critical (outage, security, many users) |
| `churn_risk` | noul | true when the text says or implies the customer may cancel, leave, or switch |
| `refund_requested` | noul | true when the text asks for a refund, credit, or money back |
| `needs_human` | noul | see rule below |

Labeling rules:

- `queue` is the main issue. A churn or refund sentence appended to a technical or shipping ticket does
  not change its queue.
- `cancellation` rows that cancel or switch vendors are `churn_risk = true`. Downgrades (fewer seats, a
  cheaper plan) are `churn_risk = false` unless a churn sentence was added.
- `needs_human = true` when any of these hold: `churn_risk`, `refund_requested`, `urgency >= 2`, or the
  family is flagged for a person (account takeover, data loss, legal notice). Otherwise false: how-to
  questions, feature ideas, password resets, order status, invoice copies.
- Near-miss families: a question about the refund policy (`refund_requested = false`), cancelling a
  single order before it ships (`shipping`, no churn), "is there a way to..." (`how_to`, not
  `feature_request`), and a happy customer who moved from a competitor asking how to import
  (`churn_risk = false`).

## Size and balance

864 rows: train 549, val 75, test 240.

| question | balance (all splits) |
|---|---|
| queue | account_access 120, billing 144, cancellation 120, feature_request 96, how_to 120, shipping 120, technical 144 |
| urgency | 0: 288, 1: 336, 2: 168, 3: 72 |
| churn_risk | false 612, true 252 |
| refund_requested | false 680, true 184 |
| needs_human | false 379, true 485 |

## How it was generated

`generate.py` (stdlib only, seed 4101) holds 36 hand-written phrasing families across the seven
queues, including near-miss families. Each family has 2-3 subject/body templates with slots for
product, device, amount, order and invoice numbers, error messages, durations, features, and tasks;
one value per slot is shared between subject and body. Eligible rows get a churn sentence (22%) or a
refund sentence (30% of billing, technical, and shipping rows), which sets those labels. A noise pass
adds keyboard typos and all-lowercase rows; wrappers add greetings, signatures with fake names and
555-01xx phone numbers, quoted support auto-replies, and forwarded-message headers. Company names are
fictional.

Test holds out 10 whole families (`billing/wrong-plan`, `billing/refund-policy-nearmiss`, `access/2fa`,
`access/hacked`, `tech/sync`, `ship/damaged`, `cancel/switching`, `cancel/downgrade`,
`feature/dealbreaker`, `howto/competitor-import-nearmiss`). Regenerate with
`python datasets/accelerators/support-ticket-triage/generate.py`.

## Zero-shot base accuracy (test)

<!-- zero-shot:start -->
Base checkpoint, no fine-tuning, on the 240-row test split (held-out phrasing families). Majority = always answering the most common test label.

| question | type | accuracy | majority | within one level |
|---|---|---|---|---|
| queue | choice | 0.80 | 0.20 |  |
| urgency | score | 0.52 | 0.50 | 0.95 |
| churn_risk | noul | 0.77 | 0.68 |  |
| refund_requested | noul | 0.85 | 0.82 |  |
| needs_human | noul | 0.54 | 0.62 |  |

Mean accuracy across questions: 0.70. Server revision: 55cf4c4ebb4ebe31b2550e8bdf3bd21b99753851.
<!-- zero-shot:end -->

## Known limitations

- Template-based: Sentence structures repeat within a family. Real tickets are longer, often cover two
  issues, and include screenshots, logs, and order tables.
- The churn and refund modifiers are appended sentences, so their position is predictable. Mix in real
  tickets where churn signals are indirect ("our budget review is next month").
- `needs_human` encodes one escalation policy. Teams that auto-process refunds or route every
  cancellation to a bot should relabel it.
- Mixed product catalog (software subscription plus physical devices). A single-product company should
  drop the queues it does not have.
