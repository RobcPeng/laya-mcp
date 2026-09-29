# email-triage-phishing

Files an inbound email into a folder and flags phishing, junk marketing, whether it needs a reply, and
how soon the recipient genuinely needs to act. Pack: `email-triage-phishing` in
`laya_mcp/accelerator_packs.py`.

## Fields

| field | content |
|---|---|
| `sender` | display name and address, e.g. `Riley Nullman <rileynullman@example.net>`; phishing uses look-alike domains such as `examp1e-secure.com` |
| `subject` | subject line, sometimes `Re:`/`Fwd:` prefixed |
| `body` | message body with signatures, quoted replies, forwarded headers, and automated footers |

## Questions and labels

| id | type | labels |
|---|---|---|
| `route` | choice | `action`, `fyi`, `meeting`, `newsletter`, `receipt`, `junk` |
| `phishing` | noul | true for credential lures, fake invoices, CEO gift-card or wire fraud, parcel-fee scams, fake shared documents, and vendor bank-change fraud |
| `spam` | noul | true for unsolicited advertising (sales blasts, cold SEO pitches, loan offers, get-rich schemes); false for phishing |
| `needs_reply` | noul | true when the sender expects a written answer |
| `urgency` | score | 0 none, 1 this week, 2 today, 3 within the hour |

Labeling rules:

- `phishing` and `spam` never both hold. Both are `route = junk`.
- Junk gets `urgency = 0` and `needs_reply = false`, however urgent the lure sounds ("suspended in
  2 hours"). The question asks how soon the recipient *genuinely* needs to act.
- Invoices from known vendors that arrive through the normal process are `receipt`, not `action`.
- Near misses: legitimate sign-in and password-change notices from the real service domain
  (`fyi`, not phishing), IT phishing-awareness announcements (`fyi`), subscribed newsletters and member
  promotions with an unsubscribe line (`newsletter`, not spam), and task reminders that say "no need to
  reply" (`action`, `needs_reply = false`).
- Calendar invites and cancellations are `meeting` with `needs_reply = false`; a person proposing a
  time is `meeting` with `needs_reply = true`.

## Size and balance

856 rows: train 517, val 71, test 268.

| question | balance (all splits) |
|---|---|
| route | action 168, fyi 73, junk 336, meeting 112, newsletter 55, receipt 112 |
| phishing | false 688, true 168 |
| spam | false 688, true 168 |
| needs_reply | false 660, true 196 |
| urgency | 0: 604, 1: 140, 2: 56, 3: 56 |

## How it was generated

`generate.py` (stdlib only, seed 2207) holds 31 hand-written families: 7 action, 3 fyi, 4 meeting,
2 newsletter, 4 receipt, 6 phishing, 5 spam. Each has 2-3 subject/body templates with slots for
people, fictional vendors (Contoso, Fabrikam, Northwind and similar sample-company names), documents,
days, amounts, order and invoice numbers, and links. Senders are generated per family type: coworkers
on `corp.example.com`, outside contacts on `example.*`, vendors on `<vendor>.example.net`, phishing on
look-alike domains, spam on throwaway `example.*` domains. Human-written families get typos and chat
casing; some phishing gets sloppy spelling; machine mail gets varied automated footers. Some legitimate
emails are wrapped as replies or forwards.

Test holds out 10 whole families (`action/client-today`, `action/urgent-outage`, `action/task-no-reply`,
`fyi/security-notice-legit`, `meeting/reschedule-now`, `news/product-promo-subscribed`,
`receipt/payment`, `phish/ceo-giftcard`, `phish/vendor-bank-change`, `spam/cold-seo`). Regenerate with
`python datasets/accelerators/email-triage-phishing/generate.py`.

## Zero-shot base accuracy (test)

<!-- zero-shot:start -->
Base checkpoint, no fine-tuning, on the 268-row test split (held-out phrasing families). Majority = always answering the most common test label.

| question | type | accuracy | majority | within one level |
|---|---|---|---|---|
| route | choice | 0.47 | 0.31 |  |
| phishing | noul | 0.63 | 0.79 |  |
| spam | noul | 0.80 | 0.90 |  |
| needs_reply | noul | 0.52 | 0.69 |  |
| urgency | score | 0.24 | 0.58 | 0.51 |

Mean accuracy across questions: 0.53. Server revision: 55cf4c4ebb4ebe31b2550e8bdf3bd21b99753851.
<!-- zero-shot:end -->

## Known limitations

- No headers beyond the sender line: no SPF/DKIM results, reply-to mismatches, or attachment types,
  which real filters rely on. Combine with header rules in production.
- Junk is 39% of rows, far above a typical corporate inbox, so the model sees enough phishing. Expect
  a different precision/recall trade-off on a real mail stream and tune the threshold there.
- Forwarded phishing ("is this legit?") is left out on purpose, because the right label depends on
  whether you judge the forwarder or the original message.
- The fyi and newsletter families have few slots, so some rows are near-duplicates of each other.
