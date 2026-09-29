# public-sector-311-intake

Routes a city 311 service request (web form, phone transcript, app, email, text, or social DM) to the
service that handles it, catches emergencies that belong with 911, checks that the request has a usable
location, and sets a priority. Pack: `public-sector-311-intake` in `laya_mcp/accelerator_packs.py`.

## Fields

| field | content |
|---|---|
| `channel` | how the request arrived: `web form`, `phone call transcript`, `mobile app`, `email`, `text message`, `social media DM` |
| `request` | the resident's words, with channel cruft (email subject and signature, call-taker prefix, app category tag) |

## Questions and labels

| id | type | labels |
|---|---|---|
| `service` | choice | `pothole`, `streetlight`, `trash`, `noise`, `graffiti`, `water`, `animal`, `parking`, `other` |
| `emergency` | noul | true when the text describes a fire, crime in progress, injury, gas leak, or immediate danger |
| `location_present` | noul | true for a street address, intersection, block, or named landmark; false for "near my house", "on my street", or no location |
| `priority` | score | 0 routine, 1 standard, 2 elevated (safety hazard or many residents), 3 urgent (immediate public safety risk) |

Labeling rules:

- Emergencies keep the closest service label (a dog attack is `animal`, a dumpster fire is `trash`, a gas
  smell or house fire is `other`) and always get priority 3. Non-emergencies never get priority 3.
- Near-miss rows use emergency vocabulary without an emergency: a leaking fire hydrant, debris from a fire
  last month, a streetlight by a gas station, a pothole that "could" hurt someone, fireworks, a dog bite
  last year. These are `emergency = false`.
- `location_present` is decided by the location slot the generator filled, not by the service.

## Size and balance

918 rows: train 602, val 82, test 234.

| question | balance (all splits) |
|---|---|
| service | animal 108, graffiti 72, noise 108, other 126, parking 72, pothole 108, streetlight 108, trash 108, water 108 |
| emergency | false 756, true 162 |
| location_present | false 240, true 678 |
| priority | 0: 180, 1: 378, 2: 198, 3: 162 |

## How it was generated

`generate.py` (stdlib only, seed 311) holds 50 hand-written phrasing families: 44 core families across
the nine services, including one emergency family per service, and 6 near-miss families. Each family has
2-3 templates with slots for duration, repeat-report remarks, time of day, and politeness. Each row
then gets a location (address, intersection, landmark, block number, a vague phrase, or nothing), an
optional opener and filler sentence, a channel wrapper, and a noise pass (keyboard typos, all-lowercase
chat style). Names are drawn from a fake-surname list, phone numbers use the reserved 555-01xx range,
and street and landmark names are generic.

Test holds out 13 whole families (one per service, three emergency families, one near-miss family), so
test measures transfer to wording the model never saw. Regenerate with
`python datasets/accelerators/public-sector-311-intake/generate.py`.

## Zero-shot base accuracy (test)

<!-- zero-shot:start -->
Base checkpoint, no fine-tuning, on the 234-row test split (held-out phrasing families). Majority = always answering the most common test label.

| question | type | accuracy | majority | within one level |
|---|---|---|---|---|
| service | choice | 0.73 | 0.15 |  |
| emergency | noul | 0.77 | 0.77 |  |
| location_present | noul | 0.54 | 0.73 |  |
| priority | score | 0.47 | 0.31 | 0.88 |

Mean accuracy across questions: 0.63. Server revision: 55cf4c4ebb4ebe31b2550e8bdf3bd21b99753851.
<!-- zero-shot:end -->

## Known limitations

- Template-based: Sentence structures repeat within a family, and a real 311 stream has more variety,
  more multi-issue requests, and more Spanish and other languages. Add a few hundred labeled real
  requests (scrubbed) before trusting the numbers for production.
- One issue per request. Real requests sometimes mention two ("streetlight out and a pothole under it").
- Priority rules are one reasonable municipal policy, not a standard. Cities differ on whether a water
  main break or a downed tree is elevated or urgent; relabel `priority` to match local SLAs.
- US-centric: Addresses, 911, and service names follow US city conventions.
