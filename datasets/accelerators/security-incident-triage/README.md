# security-incident-triage

First-pass SOC triage of a security alert: what kind of event it is, whether it is likely a real
malicious or unauthorized event, how severe it is, and whether it goes to incident response now.
Pack: `security-incident-triage` in `laya_mcp/accelerator_packs.py`.

## Fields

| field | content |
|---|---|
| `source` | the tool that raised the alert: EDR, SIEM correlation, email gateway, identity provider sign-in logs, DLP, IDS, WAF, CASB, posture scan, and so on |
| `alert` | the alert as a SOC sees it: key/value block, JSON, syslog line, analyst note, or ticket text, including enrichment notes (change tickets, travel records, user statements) |

## Questions and labels

| id | type | labels |
|---|---|---|
| `category` | choice | `malware`, `phishing`, `account_compromise`, `data_exfiltration`, `reconnaissance`, `denial_of_service`, `misconfiguration`, `policy_violation` |
| `true_positive` | noul | true when the event is real and not approved; false for authorized scanners, load tests, phishing simulations, approved travel, backup jobs, EICAR tests, documented exceptions |
| `severity` | score | 0 informational, 1 low, 2 medium, 3 high, 4 critical |
| `needs_escalation` | noul | `true_positive and severity >= 3` |

Labeling rules:

- The category describes what the alert is about, even for false positives. An authorized
  vulnerability scan is still `reconnaissance`, with `true_positive = false` and severity 0.
- False positives are always severity 0.
- Real but contained events are low: blocked internet scanning (0), quarantined adware (1), a reported
  phish nobody clicked (1), rate-limited login floods (1).
- Real misconfigurations (public storage, open RDP, missing critical patch) are true positives because
  the risky state exists and is not approved.
- Every alert carries a vendor severity (`Low`, `High`, `9`, ...) chosen at random. It is noise on
  purpose; gold severity comes from the facts in the alert, not the tool's rating.

## Size and balance

832 rows: train 526, val 72, test 234.

| question | balance (all splits) |
|---|---|
| category | account_compromise 104, data_exfiltration 104, denial_of_service 78, malware 130, misconfiguration 104, phishing 104, policy_violation 104, reconnaissance 104 |
| true_positive | false 234, true 598 |
| severity | 0: 260, 1: 156, 2: 130, 3: 234, 4: 52 |
| needs_escalation | false 546, true 286 |

## How it was generated

`generate.py` (stdlib only, seed 4242) holds 32 scenario families across the eight categories. Each
family has 1-3 hand-written variants (rule name, summary, enrichment note) with slots for hosts, users,
documentation-range IP addresses (203.0.113.0/24, 198.51.100.0/24), private addresses, invented
look-alike domains on `example`-style names, change ticket numbers, file counts, and data volumes. Each
row renders in one of five alert formats and gets a random vendor severity; 30% of summaries get light
typos.

Test holds out 9 whole families, one or more per category, including unseen false-positive patterns
(EICAR test, phishing simulation, announced load test) and a critical admin token theft. Regenerate with
`python datasets/accelerators/security-incident-triage/generate.py`.

## Zero-shot base accuracy (test)

<!-- zero-shot:start -->
Base checkpoint, no fine-tuning, on the 234-row test split (held-out phrasing families). Majority = always answering the most common test label.

| question | type | accuracy | majority | within one level |
|---|---|---|---|---|
| category | choice | 0.70 | 0.22 |  |
| true_positive | noul | 0.38 | 0.67 |  |
| severity | score | 0.23 | 0.33 | 0.62 |
| needs_escalation | noul | 0.57 | 0.56 |  |

Mean accuracy across questions: 0.47. Server revision: 55cf4c4ebb4ebe31b2550e8bdf3bd21b99753851.
<!-- zero-shot:end -->

## Known limitations

- One event per alert. Real alerts often chain (phish, then sign-in, then exfiltration); the category
  here is the first-order event.
- Enrichment notes are explicit ("approved under CHG-12345"). In production that context comes from a
  CMDB or ticket lookup; put it in the `alert` text before asking.
- Severity and escalation follow one reasonable SOC policy. Map them to your own runbook and relabel if
  your thresholds differ (for example, escalating every medium in a regulated environment).
- Host, user, and domain names are synthetic and repetitive in structure; there is no raw log noise at
  real volume.
