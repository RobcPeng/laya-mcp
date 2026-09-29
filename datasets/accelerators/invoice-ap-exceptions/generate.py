"""Generate the invoice-ap-exceptions accelerator set (deterministic, stdlib only).

Compositional: every row starts from a clean purchase (vendor, PO, 1-4 lines, receipt, vendor master
snapshot, AP payment history), then one exception scenario mutates it. The invoice renders in one of
five layouts (plain text, OCR-scraped, email body with the invoice pasted, pipe table, EDI-like
segments); the purchase_order field holds the PO, the goods receipt, the vendor master bank details on
file, and recent payments to that vendor, which is what an AP clerk looks at.

Family = scenario + layout. TEST holds out the OCR layout entirely plus a few whole scenarios.

    python datasets/accelerators/invoice-ap-exceptions/generate.py
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import _common as C  # noqa: E402

NAME = "invoice-ap-exceptions"
PREFIX = "ap"
SEED = 8080
PER_SCENARIO = 40

VENDORS = [  # (name, domain, category)
    ("Acmeline Office Supply", "acmeline-supply.example.com", "office"),
    ("Brightpath IT Hardware", "brightpath-it.example.com", "it"),
    ("Clearwater Janitorial Co", "clearwater-jan.example.net", "janitorial"),
    ("Northgate Road Materials", "northgate-roads.example.org", "roads"),
    ("Summit Lab Supply", "summitlab.example.com", "lab"),
    ("Keystone Fleet Parts", "keystonefleet.example.net", "fleet"),
    ("Riverbend Consulting Group", "riverbend-consult.example.com", "services"),
    ("Pinecrest Printing", "pinecrest-print.example.org", "print"),
]
CATALOG = {
    "office": [("Copy paper, 10-ream case", 42.50), ("Toner cartridge TN-580", 89.99), ("Desk chair, mesh", 219.00),
               ("Stapler, heavy duty", 24.75), ("File folders, box of 100", 18.40)],
    "it": [("Laptop 14in, 16GB", 1149.00), ("Docking station USB-C", 189.00), ("27in monitor", 279.00),
           ("Network switch 24-port", 649.00), ("Wireless keyboard/mouse set", 54.00)],
    "janitorial": [("Trash liners 40-45gal, case", 38.20), ("Hand soap refill 1L", 9.80),
                   ("Floor cleaner concentrate 5gal", 64.00), ("Paper towels, case of 12", 41.90)],
    "roads": [("Road salt, ton", 88.00), ("Cold patch asphalt, 50lb bag", 17.25), ("Traffic cone 28in", 21.50),
              ("Reflective sign blank", 64.00)],
    "lab": [("Nitrile gloves, box of 100", 12.60), ("Pipette tips, rack of 96", 8.95), ("Sample vials 20ml, pk 100", 36.00),
            ("Lab coat, size M", 27.50)],
    "fleet": [("Brake pad set", 74.00), ("Oil filter", 11.25), ("Wiper blades pair", 23.80), ("LED light bar", 312.00)],
    "services": [("Consulting services, hourly", 165.00), ("Project management, hourly", 140.00),
                 ("Training session, half day", 1800.00)],
    "print": [("Brochures tri-fold, per 1000", 310.00), ("Business cards, per 500", 45.00), ("Posters 24x36", 12.50)],
}
TAX_RATES = [0.0, 0.0, 0.029, 0.0475, 0.06, 0.0825]


def money(x):
    return f"${x:,.2f}"


def bank(rng):
    return f"routing 0{rng.randrange(10000000, 99999999)} acct ****{rng.randrange(1000, 9999)}"


def base_purchase(rng):
    vname, vdomain, cat = C.pick(rng, VENDORS)
    items = rng.sample(CATALOG[cat], k=min(len(CATALOG[cat]), rng.randrange(1, 5)))
    lines = []
    for desc, price in items:
        qty = rng.randrange(1, 12) if price > 150 else rng.randrange(2, 60)
        lines.append({"desc": desc, "qty": qty, "price": price, "recv": qty})
    return {
        "vendor": vname, "domain": vdomain, "po": f"PO-{rng.randrange(2026000, 2026999)}",
        "inv": f"{C.pick(rng, ['INV-', 'INV', '', 'A-', 'N'])}{rng.randrange(1000, 99999)}",
        "date": f"2026-{rng.randrange(1, 10):02d}-{rng.randrange(1, 29):02d}",
        "lines": lines, "tax": C.pick(rng, TAX_RATES), "bank": bank(rng), "bank_file": None,
        "history": [], "note": "", "po_status": "open", "sender": f"billing@{vdomain}",
        "po_on_invoice": True, "po_found": True, "math_off": 0.0, "line_off": None,
    }


def totals(p):
    sub = sum(round(line["qty"] * line["inv_price"], 2) for line in p["lines"])
    tax = round(sub * p["tax"], 2)
    return sub, tax, round(sub + tax, 2)


# ---------------------------------------------------------------- scenarios
# each returns (exception, fraud_risk) after mutating p; needs_approval = exception != "clean"

def sc_clean_exact(rng, p):
    return "clean", 0


def sc_clean_tolerance(rng, p):
    ln = C.pick(rng, p["lines"])
    ln["inv_price"] = round(ln["price"] * (1 + rng.uniform(0.002, 0.015)), 2)   # within 2% tolerance
    p["po_tolerance"] = True
    return "clean", 0


def sc_clean_partial(rng, p):
    ln = C.pick(rng, p["lines"])
    if ln["qty"] < 3:
        ln["qty"] += 3
    ln["recv"] = ln["qty"] - rng.randrange(1, ln["qty"] // 2 + 1)
    ln["inv_qty"] = ln["recv"]                        # billed only what arrived: fine
    p["note"] = C.pick(rng, ["Partial shipment; balance on backorder.", "Billing for items shipped to date.",
                             "Remaining units ship next week."])
    return "clean", 0


def sc_price(rng, p):
    ln = C.pick(rng, p["lines"])
    ln["inv_price"] = round(ln["price"] * (1 + rng.uniform(0.05, 0.4)), 2)
    p["note"] = C.pick(rng, ["", "", "Prices reflect our updated 2026 list.", "Includes fuel surcharge in unit price."])
    return "price_mismatch", 0


def sc_qty(rng, p):
    ln = C.pick(rng, p["lines"])
    if rng.random() < 0.5:
        ln["recv"] = max(1, ln["qty"] - rng.randrange(1, max(2, ln["qty"])))
        ln["inv_qty"] = ln["qty"]                     # billed full order, only part received
    else:
        ln["inv_qty"] = ln["qty"] + rng.randrange(1, 10)   # billed more than ordered
    return "quantity_mismatch", 0


def sc_missing_po_known(rng, p):
    p["po_on_invoice"] = False
    p["po_found"] = False
    p["note"] = C.pick(rng, ["Per phone order with your facilities team.", "Emergency order, PO to follow.", ""])
    return "missing_po", 1


def sc_missing_po_unknown(rng, p):
    p["vendor"] = C.pick(rng, ["Apex Strategic Solutions LLC", "Global Office Services Intl", "Prime Admin Partners",
                               "Unified Supply Network"])
    p["domain"] = C.pick(rng, ["apex-strat.example.biz", "gos-intl.example.info", "primeadmin.example.co"])
    p["sender"] = f"accounts@{p['domain']}"
    p["lines"] = [{"desc": C.pick(rng, ["Consulting services", "Directory listing renewal", "Administrative services",
                                        "Domain and SEO services"]), "qty": 1,
                   "price": float(C.pick(rng, [2500, 4800, 7500, 9900, 12000])), "recv": 0}]
    p["po_on_invoice"] = False
    p["po_found"] = False
    p["vendor_new"] = True
    p["note"] = C.pick(rng, ["Payment due immediately to avoid service interruption.", "Please remit within 5 days.",
                             "Renewal processed automatically."])
    return "missing_po", 2


def sc_dup_exact(rng, p):
    p["dup"] = "exact"
    return "duplicate", 1


def sc_dup_altered(rng, p):
    p["dup"] = "altered"
    return "duplicate", 2


def sc_bank_verified(rng, p):
    p["bank_file"] = p["bank"]
    p["bank"] = bank(rng)
    p["note"] = C.pick(rng, ["We moved to a new bank this quarter; see updated remit-to.",
                             "Please note our new remittance details."])
    p["bank_verified"] = C.pick(rng, ["Callback to vendor number on file confirmed change (AP clerk, 09/12).",
                                      "Vendor submitted signed change form; verified by phone on file."])
    return "bank_change", 1


def sc_bank_suspicious(rng, p):
    p["bank_file"] = p["bank"]
    p["bank"] = bank(rng)
    base = p["domain"].split(".")[0]
    p["sender"] = f"{C.pick(rng, ['billing', 'accounts', 'finance'])}@{base.replace('e', '3', 1)}-payments.example.net"
    p["note"] = C.pick(rng, ["URGENT: our account is under audit, pay only to the new account below today.",
                             "Do not use the old bank details. Confidential - please do not call, reply by email only.",
                             "Updated banking effective immediately. Please process before end of day."])
    return "bank_change", 2


def sc_math(rng, p):
    if rng.random() < 0.5:
        ln = C.pick(rng, p["lines"])
        p["line_off"] = ln
        ln["ext_off"] = round(C.pick(rng, [10, 100, 9, 90, 1.0]) * (1 if rng.random() < 0.7 else -1), 2)
    else:
        p["math_off"] = round(rng.uniform(15, 400), 2)
    return "math_error", 0


SCENARIOS = [
    ("clean/exact", sc_clean_exact), ("clean/tolerance", sc_clean_tolerance), ("clean/partial", sc_clean_partial),
    ("price/over", sc_price), ("qty/mismatch", sc_qty),
    ("missing_po/known-vendor", sc_missing_po_known), ("missing_po/unknown-vendor", sc_missing_po_unknown),
    ("duplicate/exact", sc_dup_exact), ("duplicate/altered", sc_dup_altered),
    ("bank/verified", sc_bank_verified), ("bank/suspicious", sc_bank_suspicious),
    ("math/error", sc_math),
]
# clean is 3 scenarios; upweight exception scenarios that have one sub-scenario so labels balance
WEIGHT = {"price/over": 2, "qty/mismatch": 2, "math/error": 2,
          "clean/exact": 2, "clean/tolerance": 2, "clean/partial": 2}


# ---------------------------------------------------------------- rendering

def invoice_lines(p):
    out = []
    for ln in p["lines"]:
        q = ln.get("inv_qty", ln["qty"])
        pr = ln.get("inv_price", ln["price"])
        ext = round(q * pr + ln.get("ext_off", 0), 2)
        out.append((ln["desc"], q, pr, ext))
    return out


def render_invoice(rng, p, layout):
    lines = invoice_lines(p)
    sub = round(sum(e for *_, e in lines), 2)
    if p["line_off"] is not None:                     # line extension is wrong, subtotal sums the wrong lines
        pass
    tax = round(sum(q * pr for _, q, pr, _ in lines) * p["tax"], 2)
    total = round(sub + tax + p["math_off"], 2)
    po = p["po"] if p["po_on_invoice"] else C.pick(rng, ["", "N/A", "TBD", "see email"])
    inv = p["inv_shown"] if "inv_shown" in p else p["inv"]
    remit = f"Remit to: {p['vendor']}, {p['bank']}"
    note = p["note"]
    if layout == "plain":
        body = "\n".join(f"  {d} | qty {q} | {money(pr)} | {money(e)}" for d, q, pr, e in lines)
        return (f"{p['vendor']}\nINVOICE {inv}   Date: {p['date']}\nPO: {po or '-'}\n{body}\n"
                f"Subtotal {money(sub)}  Tax {money(tax)}  TOTAL DUE {money(total)}\n{remit}"
                + (f"\nNote: {note}" if note else ""))
    if layout == "ocr":
        body = "\n".join(f"{d.upper()}  {q}  {pr:.2f}  {e:,.2f}" for d, q, pr, e in lines)
        txt = (f"{p['vendor'].upper()}\nlnvoice No. {inv}  Dte {p['date']}\nP.O. # {po or '_____'}\n"
               f"DESCRIPTION QTY UNIT AMOUNT\n{body}\nSUBTOTAL {sub:,.2f}\nTAX {tax:,.2f}\nT0TAL {total:,.2f}\n"
               f"{remit.upper()}" + (f"\n{note}" if note else ""))
        return txt.replace("0", "O", 1) if rng.random() < 0.3 else txt
    if layout == "email":
        body = "; ".join(f"{q} x {d} @ {money(pr)} = {money(e)}" for d, q, pr, e in lines)
        greet = C.pick(rng, ["Hi AP team,", "Hello,", "Good afternoon,", "Accounts Payable -"])
        return (f"From: {p['sender']}\nSubject: Invoice {inv}\n\n{greet}\n"
                + (f"{note}\n" if note else "")
                + f"Please find invoice {inv} for PO {po or '(none)'}: {body}. Subtotal {money(sub)}, tax {money(tax)}, "
                  f"total {money(total)}. {remit}.\n\nThanks,\n{C.person(rng)}\n{p['vendor']}")
    if layout == "table":
        rows = "\n".join(f"| {d} | {q} | {pr:.2f} | {e:.2f} |" for d, q, pr, e in lines)
        return (f"Vendor: {p['vendor']} | Invoice: {inv} | Date: {p['date']} | PO: {po or 'none'}\n"
                f"| item | qty | unit | ext |\n{rows}\nsubtotal={sub:.2f} tax={tax:.2f} total={total:.2f}\n{remit}"
                + (f"\nmemo: {note}" if note else ""))
    # edi-like
    segs = "~".join(f"IT1*{i + 1}*{q}*EA*{pr:.2f}**{d.replace(' ', '_')[:24]}" for i, (d, q, pr, e) in enumerate(lines))
    return (f"BIG*{p['date'].replace('-', '')}*{inv}**{po or ''}~N1*RE*{p['vendor']}~{segs}~"
            f"TDS*{int(round(total * 100))}~TXI*TX*{tax:.2f}~REMIT*{p['bank']}" + (f"~MSG*{note}" if note else ""))


def render_po(rng, p):
    if not p["po_found"]:
        head = C.pick(rng, [f"No purchase order on file matching this invoice for {p['vendor']}.",
                            "PO lookup: no match found.", "Purchase order: none located in the ERP."])
    else:
        body = "; ".join(f"{ln['desc']} qty {ln['qty']} @ {money(ln['price'])}" for ln in p["lines"])
        head = f"{p['po']} ({p['po_status']}) {p['vendor']}: {body}."
        head += C.pick(rng, [" Price tolerance 2%.", " Tolerance: +/-2% on unit price.", " Match tolerance 2%."])
        recv = "; ".join(f"{ln['desc']} received {ln['recv']}" for ln in p["lines"])
        head += f"\nGoods receipt: {recv}."
    vm = p["bank_file"] or p["bank"]
    if p.get("vendor_new"):
        vend = "Vendor master: no record for this vendor."
    else:
        vend = f"Vendor master: {p['vendor']}, remit {vm}."
    if p.get("bank_verified"):
        vend += f" {p['bank_verified']}"
    hist = ""
    if p.get("dup"):
        lines = invoice_lines(p)
        sub = round(sum(e for *_, e in lines), 2)
        tot = round(sub + round(sum(q * pr for _, q, pr, _ in lines) * p["tax"], 2), 2)
        if p["dup"] == "exact":
            hist = f"Paid history: invoice {p['inv']} for {money(tot)} paid on 2026-{rng.randrange(1, 10):02d}-15."
        else:
            hist = (f"Paid history: invoice {p['inv']} for {money(tot)} paid on 2026-{rng.randrange(1, 10):02d}-15 "
                    f"against {p['po']}.")
            p["inv_shown"] = C.pick(rng, [p["inv"] + "-A", p["inv"] + "R", p["inv"].replace("INV-", "INV") + ".",
                                          "0" + p["inv"]])
    else:
        other = rng.randrange(1000, 99999)
        hist = C.pick(rng, ["Paid history: none in last 90 days.",
                            f"Paid history: invoice {other} for {money(rng.uniform(80, 9000))} paid last month.",
                            ""])
    return "\n".join(x for x in [head, vend, hist] if x)


LAYOUTS = ["plain", "ocr", "email", "table", "edi"]
TEST_SCENARIOS = {"clean/partial", "duplicate/altered"}
TEST_LAYOUTS = {"ocr"}


def build(rng):
    examples = []
    for fam, fn in SCENARIOS:
        for i in range(PER_SCENARIO * WEIGHT.get(fam, 1)):
            p = base_purchase(rng)
            exception, fraud = fn(rng, p)
            layout = LAYOUTS[i % len(LAYOUTS)]
            po_text = render_po(rng, p)                  # before the invoice: may set inv_shown for duplicates
            inv_text = render_invoice(rng, p, layout)
            examples.append({
                "family": f"{fam}|{layout}", "group": exception,
                "state": {"invoice": inv_text, "purchase_order": po_text},
                "gold": {"exception": exception, "needs_approval": exception != "clean", "fraud_risk": fraud},
            })
    return examples


def main():
    rng = C.rng_for(NAME, SEED)
    exs = build(rng)
    test = sorted({e["family"] for e in exs
                   if e["family"].split("|")[0] in TEST_SCENARIOS or e["family"].split("|")[1] in TEST_LAYOUTS})
    splits = C.write_dataset(NAME, exs, HERE, PREFIX, seed=SEED, test_families=test)
    C.summary(NAME, splits)
    return splits


if __name__ == "__main__":
    main()
