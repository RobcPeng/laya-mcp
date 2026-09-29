# he-it-helpdesk

Triage for a campus IT help desk: which IT area a ticket belongs to, whether it describes an outage
affecting many users, and what priority it gets. Tickets come from students, faculty, staff, TAs, and
researchers. Pack: `he-it-helpdesk` in `laya_mcp/accelerator_packs.py`.

## Fields

| field | content |
|---|---|
| `ticket` | the ticket as the help desk sees it: a portal submission (with the role and the category the user picked, which is often wrong), an email with headers and signature, a chat transcript, or phone notes with a 555 callback number |

## Questions and labels

| id | type | labels |
|---|---|---|
| `category` | choice | `lms`, `sso_mfa`, `wifi`, `email`, `software`, `classroom_tech`, `research_computing`, `other` |
| `outage` | noul | true when many users are affected (a building, a class, a department, a lab, everyone); false for one person |
| `priority` | score | 0 low, 1 medium, 2 high, 3 critical |

Labeling rules:

- Priority 3: many users fully unable to work (single sign-on down, a building offline, the license
  server down, lecture capture failed in every room, the LMS down during an exam).
- Priority 2: a class, exam, or deadline is affected right now for one person or one room (a projector
  dead before a lecture, locked out before an online exam, an assignment due tonight), or many users
  are degraded but still working (slow Wi-Fi, an intermittently slow course site).
- Priority 1: one person blocked with no deadline mentioned (locked account, mailbox full, a laptop
  that will not join Wi-Fi, a cluster job stuck).
- Priority 0: questions and minor issues with a workaround (how to share a calendar, a loose HDMI
  adapter that works, requesting a license for next term).
- `outage` is independent of category. The portal's "selected category" is random noise; gold comes from
  the description.
- Near misses: "Is the Wi-Fi down?? ... but I'm the only one here", "Everyone says the course site works
  for them but I can't see my grades", and "login was down for everyone earlier but it's back now" are
  all `outage = false` (the last one is priority 0).
- The LMS is described generically ("the LMS", "course site"), as is MFA ("authenticator app", "push
  notification"), so the set does not favor one vendor.

## Size and balance

862 rows: train 547, val 75, test 240.

| question | balance (all splits) |
|---|---|
| category | classroom_tech 96, email 96, lms 144, other 96, research_computing 95, software 96, sso_mfa 120, wifi 119 |
| outage | false 623, true 239 |
| priority | 0: 239, 1: 216, 2: 216, 3: 191 |

## How it was generated

`generate.py` (stdlib only, seed 7070) holds 36 phrasing families: 33 core families (four or five per
category, covering single-user, class-affecting, many-user, and question cases) and 3 near-miss
families. Each family has 2-3 templates with slots for buildings, rooms, course numbers, timing ("in 20
minutes", "due tonight at 11:59"), scope ("everyone on my floor", "the whole class"), and software
names written generically. Each row gets a channel wrapper with a fake requester (placeholder surnames,
`example.edu` addresses, 555-01xx phones) and a noise pass (typos, all-lowercase chat).

Test holds out 10 whole families: at least one per category, including a many-user degraded family, an
all-rooms classroom outage, a research-computing deadline, and the "only me" Wi-Fi near miss.
Regenerate with `python datasets/accelerators/he-it-helpdesk/generate.py`.

## Zero-shot base accuracy (test)

<!-- zero-shot:start -->
Base checkpoint, no fine-tuning, on the 240-row test split (held-out phrasing families). Majority = always answering the most common test label.

| question | type | accuracy | majority | within one level |
|---|---|---|---|---|
| category | choice | 0.80 | 0.20 |  |
| outage | noul | 0.92 | 0.70 |  |
| priority | score | 0.52 | 0.30 | 0.91 |

Mean accuracy across questions: 0.75. Server revision: 55cf4c4ebb4ebe31b2550e8bdf3bd21b99753851.
<!-- zero-shot:end -->

## Known limitations

- One issue per ticket. Real tickets often mix two ("can't log in so I can't submit").
- Priority follows one reasonable help-desk policy tied to class and exam timing. Campuses with formal
  ITSM impact/urgency matrices should relabel `priority` to their matrix.
- Scope words ("everyone", "the whole class") carry most of the `outage` signal. Real tickets are
  vaguer; the help desk's own monitoring should confirm an outage before a status page goes up.
- Template structures repeat inside a family; add scrubbed real tickets before trusting the numbers.
