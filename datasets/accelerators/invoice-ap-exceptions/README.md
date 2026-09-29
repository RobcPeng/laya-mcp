# invoice-ap-exceptions

Accounts payable three-way match: compare a vendor invoice with the purchase order, goods receipt,
vendor master record, and recent payments, then name the exception, decide whether it needs manual
approval, and score fraud risk. Pack: `invoice-ap-exceptions` in `laya_mcp/accelerator_packs.py`.

## Fields

| field | content |
|---|---|
| `invoice` | the invoice as AP receives it: plain text, OCR-scraped text, an email with the invoice pasted in, a pipe table, or EDI-like segments |
| `purchase_order` | the PO lines and status with a price tolerance, the goods receipt, the vendor master remit-to on file, and recent paid invoices from that vendor (or "no purchase order on file") |

## Questions and labels

| id | type | labels |
|---|---|---|
| `exception` | choice | `clean`, `price_mismatch`, `quantity_mismatch`, `missing_po`, `duplicate`, `bank_change`, `math_error` |
| `needs_approval` | noul | `exception != clean` |
| `fraud_risk` | score | 0 low, 1 moderate, 2 high |

Labeling rules (one exception per invoice):

- `clean` covers three cases: exact match; one unit price up to 1.5% over the PO, inside the stated 2%
  tolerance; and a partial shipment where the invoice bills only the received quantity.
- `price_mismatch`: one unit price 5-40% over the PO. `quantity_mismatch`: billed more than received, or
  more than ordered. `math_error`: a line extension is wrong or the total does not equal subtotal plus tax.
  All three are fraud risk 0.
- `missing_po`: no PO on the invoice and none on file. Known vendor = fraud 1; a vendor with no vendor
  master record billing a round amount for vague services with payment pressure = fraud 2.
- `duplicate`: the payment history shows the same invoice already paid. Same invoice number = fraud 1;
  the number altered to slip past duplicate checks (suffix `-A`, `R`, a leading zero) = fraud 2.
- `bank_change`: remit-to bank differs from the vendor master. Change verified by a callback to the
  number on file = fraud 1; change pushed by email from a look-alike domain with urgency or "do not call"
  = fraud 2.

## Size and balance

720 rows: train 422, val 58, test 240.

| question | balance (all splits) |
|---|---|
| exception | bank_change 80, clean 240, duplicate 80, math_error 80, missing_po 80, price_mismatch 80, quantity_mismatch 80 |
| needs_approval | false 240, true 480 |
| fraud_risk | 0: 480, 1: 120, 2: 120 |

## How it was generated

`generate.py` (stdlib only, seed 8080) is compositional rather than template-based. Each row builds a
clean purchase from eight invented vendors (office supply, IT hardware, janitorial, road materials, lab
supply, fleet parts, consulting, printing) with 1-4 catalog lines, a tax rate, a bank account, and a
payment history, then applies one of 12 scenarios and renders the invoice in one of five layouts. The
gold label comes from the scenario, and the numbers in the text are computed from the same mutated
purchase, so every label can be checked by arithmetic.

Families are scenario x layout. Test holds out the OCR layout for every scenario, plus two whole
scenarios (partial-shipment clean invoices and altered-number duplicates). Regenerate with
`python datasets/accelerators/invoice-ap-exceptions/generate.py`.

## Zero-shot base accuracy (test)

<!-- zero-shot:start -->
Base checkpoint, no fine-tuning, on the 240-row test split (held-out phrasing families). Majority = always answering the most common test label.

| question | type | accuracy | majority | within one level |
|---|---|---|---|---|
| exception | choice | 0.19 | 0.47 |  |
| needs_approval | noul | 0.53 | 0.53 |  |
| fraud_risk | score | 0.29 | 0.67 | 0.62 |

Mean accuracy across questions: 0.34. Server revision: 55cf4c4ebb4ebe31b2550e8bdf3bd21b99753851.
<!-- zero-shot:end -->

## Known limitations

- Arithmetic is the hard part. Laya reads text; it does not compute. Price and quantity mismatches are
  learnable from side-by-side numbers, but math errors of a few dollars on a four-line invoice are near
  the limit of what a 421M encoder will catch. Run a deterministic three-way-match check first and use
  this model for the judgment calls (bank change, duplicates with altered numbers, vague vendors).
- One exception per invoice. Real invoices can carry several.
- The approval rule is "any exception". Many AP teams also route clean invoices above a dollar
  threshold; add that to your labels if it applies.
- Bank numbers are random digits with masked accounts, and vendor names are invented.
