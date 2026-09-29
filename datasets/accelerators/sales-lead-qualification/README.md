# sales-lead-qualification

BANT-style qualification of inbound leads (web forms, emails, SDR call notes, event badge scans, chat,
partner referrals, social DMs) against a product description: budget, authority, need, timing, pipeline
stage, and an overall fit score. Pack: `sales-lead-qualification` in `laya_mcp/accelerator_packs.py`.

## Fields

| field | content |
|---|---|
| `product` | one-line description of what is being sold (six invented products: a data platform, a field-service app, payroll software, a local-government request portal, endpoint security, a learning management system) |
| `lead` | the lead as captured, with name, title, company, and the prospect's words |

Putting the product in the state lets one checkpoint qualify leads for several product lines.

## Questions and labels

| id | type | labels |
|---|---|---|
| `budget` | noul | true when money is stated as available or approved; "no budget yet", "next fiscal year", or silence are false |
| `authority` | noul | true for a decision-making title (owner, director, VP, CFO, IT manager, ...) or a statement like "I sign the contracts"; false for interns, analysts, consultants, or "not my call" |
| `need` | noul | true only when the lead states a problem that the product in `product` solves |
| `timing` | noul | true for a plan within six months ("live within 90 days", "contract ends in four months"); nine months, next year, or no timeline are false |
| `stage` | choice | `not_a_fit`, `research`, `evaluating`, `ready_to_buy` |
| `fit` | score | 0 poor, 1 weak, 2 good, 3 strong |

Labeling rules:

- `need` is judged against the product. A whiteboard-dispatching pain is a need for the field-service
  app and not for the payroll product. About a third of qualified-stage leads carry another product's
  pain or none, which is the main hard negative.
- `stage` comes from the stage sentence: research ("no active project"), evaluating (demo, trial,
  pricing comparison), ready_to_buy (quote, contract, W-9, PO). Research leads never have timing;
  ready-to-buy leads always do.
- `not_a_fit` covers students, vendors pitching their own services, job seekers, and requests for
  something the company does not sell. These have need false and fit 0. Wrong-product leads from an
  office manager count as `authority = true` (they buy for their office) and may state budget or timing.
- `fit` = 0 for not_a_fit; 1 when need is false or no other BANT signal is present; 3 when need, budget,
  authority, and timing are all true; otherwise 2.

## Size and balance

810 rows: train 594, val 81, test 135.

| question | balance (all splits) |
|---|---|
| budget | false 473, true 337 |
| authority | false 407, true 403 |
| need | false 332, true 478 |
| timing | false 480, true 330 |
| stage | not_a_fit 180, research 210, evaluating 210, ready_to_buy 210 |
| fit | 0: 180, 1: 216, 2: 302, 3: 112 |

## How it was generated

`generate.py` (stdlib only, seed 818). For each stage and each of seven styles, 30 leads are composed
from sentence banks: a pain (from the matching product about 70% of the time, otherwise another
product's pain or none), a budget sentence, a timing sentence, an optional authority statement, and a
stage sentence, shuffled. The title is drawn from decision-maker or non-decision-maker lists to match
`authority`. Four not-a-fit families (45 rows each) are written separately. Companies and people use
placeholder names; emails are on example.com/org/net. A noise pass adds typos and lowercase.

Test holds out four families: social-DM research leads, SDR call-note evaluating leads, partner-referred
ready-to-buy leads, and vendor pitches.

## Zero-shot base accuracy (test)

<!-- zero-shot:start -->
Base checkpoint, no fine-tuning, on the 135-row test split (held-out phrasing families). Majority = always answering the most common test label.

| question | type | accuracy | majority | within one level |
|---|---|---|---|---|
| budget | noul | 0.77 | 0.67 |  |
| authority | noul | 0.61 | 0.61 |  |
| need | noul | 0.57 | 0.52 |  |
| timing | noul | 0.70 | 0.65 |  |
| stage | choice | 0.44 | 0.33 |  |
| fit | score | 0.30 | 0.33 | 0.68 |

Mean accuracy across questions: 0.56. Server revision: 55cf4c4ebb4ebe31b2550e8bdf3bd21b99753851.
<!-- zero-shot:end -->

## Known limitations

- BANT sentences are fairly explicit. Real leads imply budget and authority ("we're a 2,000-person
  county", "my team") far more often than they state them; expect lower accuracy on sparse form fills.
- The fit formula is one reasonable scoring policy. Replace it with the team's own lead-scoring rules
  and relabel `fit` before using it for routing.
- Six products and fifteen companies is a small world. Add the real product descriptions and a few
  hundred labeled historical leads (scrubbed) for a production POC.
- Test is the smallest of the accelerator sets (135 rows); per-question numbers on it move a few points
  between runs of different checkpoints.
