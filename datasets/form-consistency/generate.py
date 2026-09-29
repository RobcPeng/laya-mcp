#!/usr/bin/env python3
"""Generate the form-consistency set: a whole submitted form -> contradiction / genuine.

    python datasets/form-consistency/generate.py            # writes train/val/test.jsonl here
    python datasets/form-consistency/generate.py --stats

Stdlib only, seeded, deterministic, fully synthetic (invented names, 555-01xx phones, example.* email
domains). Value pools are shared with datasets/form-field-validation/generate.py.

Row format (questions from laya_mcp.packs, verbatim):
  {"id", "family", "state": {"form", "entries": <JSON string of {label: value}>}, "questions": {...},
   "gold": {"contradiction": bool, "genuine": bool}}

`entries` is encoded exactly like laya_mcp.forms.validate_form does it: json.dumps({label: value},
ensure_ascii=False) over the filled fields only.

Row kinds (the `family` names them):
  fc/clean/*                 consistent, genuine forms, including terse ones           -> F / T
  fc/contra_<kind>/*         one real contradiction; a genuine person made a mistake   -> T / T
  fc/topic_hardneg_<kind>/*  looks like a mismatch but is fine (work email domain differs from the
                             company, mailing address differs from the project address, preferred
                             name differs from legal name, out-of-state phone area code) -> F / T
  fc/fake_<kind>/*           test submissions, joke entries, spam, keyboard mash       -> F / F
(family names with "topic" are reported as hard negatives by finetune/evaluate.py.)

Splits: TEST holds out whole forms (HELDOUT_FORMS). VAL is a random slice of the train-side forms.
"""
import argparse
import datetime as dt
import importlib.util
import json
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, ROOT)
from laya_mcp import packs  # noqa: E402

_spec = importlib.util.spec_from_file_location(
    "ffv_gen", os.path.join(os.path.dirname(HERE), "form-field-validation", "generate.py"))
V = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(V)

SEED = 20261001
PACK = "form-consistency"
TODAY = dt.date(2026, 9, 1)
KIND_W = {"clean": 0.34, "contra": 0.33, "hardneg": 0.13, "fake": 0.20}
TARGET = {"trainside": 1250, "test": 330}
VAL_FRAC = 0.1
P = V.P


def fmt_date(rng, d):
    return P(rng, [d.strftime("%m/%d/%Y"), d.isoformat(), f"{V.MONTHS[d.month - 1]} {d.day}, {d.year}",
                   f"{d.month}/{d.day}/{d.year}", f"{d.day} {V.MONTHS[d.month - 1][:3]} {d.year}"])


def rdate(rng, lo, hi):
    return lo + dt.timedelta(days=rng.randrange((hi - lo).days))


def age_on(b, today=TODAY):
    return today.year - b.year - ((today.month, today.day) < (b.month, b.day))


def name(rng):
    return f"{P(rng, V.FIRST)} {P(rng, V.LAST)}"


def email_for(rng, n, dom=None):
    f, l = n.split(" ", 1)
    f = f.lower().replace("é", "e").replace("ë", "e").replace("ö", "o").replace("ó", "o")
    l = l.lower().replace("'", "").replace(" ", "").replace("-", "").replace(".", "")
    return f"{P(rng, [f + '.' + l, f[0] + l, f + str(rng.randrange(10, 99))])}@{dom or P(rng, V.EMAIL_DOM)}"


def geo(rng):
    c, s, z = P(rng, V.CITYSTATEZIP)
    return c, s, z


def wrong_geo(rng, c, s, z):
    """A city/state/ZIP triple where one piece belongs to a different state."""
    others = [g for g in V.CITYSTATEZIP if g[1] != s]
    o = P(rng, others)
    k = rng.randrange(3)
    return [(c, s, o[2]), (c, o[1], z), (o[0], s, z)][k]


def itemize(rng, n=None, labels=None):
    labels = labels or ["Hotel", "Meals", "Taxi", "Airfare", "Parking", "Registration", "Mileage", "Supplies", "Rental car"]
    items = [(l, round(rng.uniform(8, 480), 2)) for l in rng.sample(labels, n or rng.randrange(2, 5))]
    return items, round(sum(v for _, v in items), 2)


def items_text(items):
    return "; ".join(f"{l} ${v:,.2f}" for l, v in items)


# --------------------------------------------------------------------------------------------------
# Each form builder returns (entries: dict, contra_kinds: {kind: fn(rng, e) -> e'}, hardneg: {kind: fn}).
def f_311(rng):
    n, (c, s, z) = name(rng), geo(rng)
    e = {"Full name": n, "Phone": V.phone(rng), "Email": email_for(rng, n),
         "Location": f"{rng.randrange(10, 9999)} {P(rng, V.STREETS)}", "City": c, "ZIP code": z,
         "Description": V.vals(V.T["issue_311"]["pass"], rng)}
    contra = {"geo": lambda e: {**e, "ZIP code": P(rng, [g[2] for g in V.CITYSTATEZIP if g[1] != s])}}
    hard = {"phone_area": lambda e: {**e, "Phone": f"(212) 555-01{rng.randrange(10, 99)}"},
            "mailing_diff": lambda e: {**e, "Mailing address": f"PO Box {rng.randrange(100, 999)}, {c} {z}"}}
    return e, contra, hard


def f_permit(rng):
    n, (c, s, z) = name(rng), geo(rng)
    st = rdate(rng, dt.date(2026, 9, 1), dt.date(2027, 3, 1))
    en = st + dt.timedelta(days=rng.randrange(14, 200))
    org = P(rng, V.ORGS)
    e = {"Applicant name": n, "Contractor": org, "Project address": f"{rng.randrange(10, 9999)} {P(rng, V.STREETS)}",
         "City": c, "State": s, "ZIP": z, "Scope of work": V.vals(V.T["permit_work"]["pass"], rng),
         "Estimated start date": fmt_date(rng, st), "Estimated completion date": fmt_date(rng, en),
         "Valuation": f"${rng.randrange(2, 90) * 500:,}"}
    contra = {"date_order": lambda e: {**e, "Estimated completion date": fmt_date(rng, st - dt.timedelta(days=rng.randrange(20, 120)))},
              "geo": lambda e: {**e, **dict(zip(("City", "State", "ZIP"), wrong_geo(rng, c, s, z)))}}
    hard = {"mailing_diff": lambda e: {**e, "Owner mailing address": f"{rng.randrange(10, 9999)} {P(rng, V.STREETS)}, {P(rng, V.CITYSTATEZIP)[0]}"},
            "email_domain": lambda e: {**e, "Contractor email": email_for(rng, n, "example.org")}}
    return e, contra, hard


def f_benefits(rng):
    n, (c, s, z) = name(rng), geo(rng)
    b = rdate(rng, dt.date(1950, 1, 1), dt.date(2006, 1, 1))
    deps = rng.randrange(0, 4)
    e = {"Applicant name": n, "Date of birth": fmt_date(rng, b), "Age": str(age_on(b)),
         "Household size": str(1 + deps + rng.randrange(0, 2)), "Any dependents?": "Yes" if deps else "No",
         "Number of dependents": str(deps), "Monthly income": f"${rng.randrange(0, 45) * 100:,}",
         "City": c, "State": s, "ZIP code": z}
    contra = {"age_dob": lambda e: {**e, "Age": str(age_on(b) + P(rng, [-12, -7, 8, 15, 21]))},
              "dependents": lambda e: {**e, "Any dependents?": "No", "Number of dependents": str(rng.randrange(2, 5))},
              "household": lambda e: {**e, "Household size": "1", "Number of dependents": str(rng.randrange(2, 5)),
                                      "Any dependents?": "Yes"},
              "geo": lambda e: {**e, **dict(zip(("City", "State", "ZIP code"), wrong_geo(rng, c, s, z)))}}
    hard = {"mailing_diff": lambda e: {**e, "Mailing address": f"PO Box {rng.randrange(100, 9999)}, {P(rng, V.CITYSTATEZIP)[0]}"},
            "phone_area": lambda e: {**e, "Phone": f"(415) 555-01{rng.randrange(10, 99)}"}}
    return e, contra, hard


def f_jobapp(rng):
    n = name(rng)
    cur = P(rng, V.ORGS)
    since = rdate(rng, dt.date(2015, 1, 1), dt.date(2026, 1, 1))
    avail = rdate(rng, dt.date(2026, 9, 15), dt.date(2026, 12, 31))
    e = {"Full name": n, "Email": email_for(rng, n), "Position": P(rng, V.TITLES),
         "Currently employed?": "Yes", "Current employer": cur, "At current job since": fmt_date(rng, since),
         "Years of experience": str(max(1, TODAY.year - since.year + rng.randrange(0, 6))),
         "Available start date": fmt_date(rng, avail)}
    if rng.random() < 0.4:
        e.update({"Currently employed?": "No"})
        e.pop("Current employer"); e.pop("At current job since")
    contra = {"employment": lambda e: {**e, "Currently employed?": "No", "Current employer": cur,
                                       "At current job since": fmt_date(rng, since)},
              "experience": lambda e: {**e, "Years of experience": "25", "Date of birth": fmt_date(rng, rdate(rng, dt.date(2004, 1, 1), dt.date(2007, 1, 1)))},
              "date_order": lambda e: {**e, "Available start date": fmt_date(rng, dt.date(2026, 10, 1)),
                                       "Latest start date": fmt_date(rng, dt.date(2026, 9, rng.randrange(2, 28)))}}
    hard = {"email_domain": lambda e: {**e, "Email": email_for(rng, n, P(rng, ["example.com", "example.net"]))},
            "preferred_name": lambda e: {**e, "Preferred name": P(rng, ["Mo", "Kat", "DJ", "Beto", "Sam", "Liz"])}}
    return e, contra, hard


def f_event(rng):
    n = name(rng)
    a = rdate(rng, dt.date(2026, 10, 1), dt.date(2027, 5, 1))
    d = a + dt.timedelta(days=rng.randrange(1, 4))
    g = rng.randrange(1, 4)
    guests = [name(rng) for _ in range(g - 1)]
    e = {"Attendee name": n, "Email": email_for(rng, n), "Organization": P(rng, V.ORGS),
         "Arrival date": fmt_date(rng, a), "Departure date": fmt_date(rng, d), "Number of guests (incl. you)": str(g)}
    if guests:
        e["Guest names"] = ", ".join(guests)
    contra = {"date_order": lambda e: {**e, "Departure date": fmt_date(rng, a - dt.timedelta(days=rng.randrange(2, 9)))},
              "guest_count": lambda e: {**e, "Number of guests (incl. you)": "1",
                                        "Guest names": ", ".join(name(rng) for _ in range(rng.randrange(2, 4)))}}
    hard = {"email_domain": lambda e: {**e, "Email": email_for(rng, n, "example.net")},
            "same_day": lambda e: {**e, "Departure date": e["Arrival date"]}}
    return e, contra, hard


def f_patient(rng):
    n = name(rng)
    b = rdate(rng, dt.date(1940, 1, 1), dt.date(2008, 1, 1))
    ec = name(rng)
    e = {"Patient name": n, "Date of birth": fmt_date(rng, b), "Age": str(age_on(b)), "Phone": V.phone(rng),
         "Current medications": V.vals(V.T["medications"]["pass"], rng),
         "Reason for visit": V.vals(V.T["symptoms"]["pass"], rng),
         "Emergency contact": ec, "Relationship": P(rng, ["Spouse", "Mother", "Friend", "Sister", "Partner"])}
    contra = {"age_dob": lambda e: {**e, "Age": str(age_on(b) + P(rng, [-20, -9, 6, 11, 30]))},
              "self_contact": lambda e: {**e, "Emergency contact": n, "Relationship": "Mother"}}
    hard = {"contact_lastname": lambda e: e,
            "phone_area": lambda e: {**e, "Phone": f"(617) 555-01{rng.randrange(10, 99)}"}}
    return e, contra, hard


def f_expense(rng):
    n = name(rng)
    items, tot = itemize(rng)
    d = rdate(rng, dt.date(2026, 6, 1), dt.date(2026, 8, 30))
    e = {"Employee": n, "Trip dates": f"{fmt_date(rng, d)} to {fmt_date(rng, d + dt.timedelta(days=rng.randrange(1, 4)))}",
         "Itemized expenses": items_text(items), "Total claimed": f"${tot:,.2f}",
         "Business purpose": V.vals(V.T["expense_purpose"]["pass"], rng)}
    contra = {"total": lambda e: {**e, "Total claimed": f"${tot + P(rng, [50, 100, 212.4, -40, 300, 18.75]):,.2f}"},
              "date_order": lambda e: {**e, "Trip dates": f"{fmt_date(rng, d)} to {fmt_date(rng, d - dt.timedelta(days=rng.randrange(3, 10)))}"}}
    hard = {"rounding": lambda e: {**e, "Total claimed": f"${round(tot):,}"},
            "email_domain": lambda e: {**e, "Email": email_for(rng, n, "example.net")}}
    return e, contra, hard


def f_vendor(rng):
    n, (c, s, z) = name(rng), geo(rng)
    org = P(rng, V.ORGS)
    e = {"Legal business name": org, "Primary contact": n, "Contact email": email_for(rng, n, "example.com"),
         "Remit-to address": f"{rng.randrange(10, 9999)} {P(rng, V.STREETS)}", "City": c, "State": s, "ZIP": z,
         "Business phone": V.phone(rng)}
    contra = {"geo": lambda e: {**e, **dict(zip(("City", "State", "ZIP"), wrong_geo(rng, c, s, z)))},
              "entity": lambda e: {**e, "Business type": "Sole proprietorship", "Number of owners": str(rng.randrange(3, 6))}}
    hard = {"email_domain": lambda e: {**e, "Contact email": email_for(rng, n, P(rng, ["example.org", "mail.example.com"]))},
            "mailing_diff": lambda e: {**e, "Physical location": f"{rng.randrange(10, 9999)} {P(rng, V.STREETS)}, {P(rng, V.CITYSTATEZIP)[0]}"}}
    return e, contra, hard


def f_leave(rng):
    n = name(rng)
    st = rdate(rng, dt.date(2026, 9, 1), dt.date(2027, 2, 1))
    days = rng.randrange(1, 10)
    en = st + dt.timedelta(days=days - 1)
    e = {"Employee": n, "Leave type": P(rng, ["Vacation", "Sick", "Bereavement", "Jury duty", "Parental"]),
         "First day of leave": fmt_date(rng, st), "Last day of leave": fmt_date(rng, en),
         "Days requested": str(days), "Supervisor": name(rng)}
    contra = {"date_order": lambda e: {**e, "Last day of leave": fmt_date(rng, st - dt.timedelta(days=rng.randrange(3, 20)))},
              "day_count": lambda e: {**e, "Days requested": str(days + rng.randrange(8, 20))}}
    hard = {"same_day": lambda e: {**e, "Last day of leave": e["First day of leave"], "Days requested": "1"},
            "email_domain": lambda e: {**e, "Email": email_for(rng, n, "example.net")}}
    return e, contra, hard


def f_incident(rng):
    n = name(rng)
    e = {"Reported by": n, "Date": fmt_date(rng, rdate(rng, dt.date(2026, 5, 1), dt.date(2026, 8, 30))),
         "Time": V.time_v(rng), "Location": P(rng, ["Rec center east entrance", "Warehouse aisle 7", "Lot C",
                                                   "Aspen Hall 3rd floor", "Chemistry lab 204"]),
         "Anyone injured?": "No", "Number injured": "0",
         "What happened?": P(rng, ["A forklift clipped a shelving unit, two pallets damaged, no one hurt",
                                   "Window of a fleet vehicle broken overnight", "Smoke alarm from burnt popcorn, building evacuated 20 min",
                                   "Water leak from the ceiling onto the front desk computers"])}
    contra = {"injury": lambda e: {**e, "Anyone injured?": "No", "Number injured": str(rng.randrange(1, 4)),
                                   "What happened?": "Coworker cut his hand on a box cutter and went to urgent care"}}
    hard = {"reporter_not_witness": lambda e: {**e, "Witness": name(rng)}}
    return e, contra, hard


def f_he_admit(rng):
    n = name(rng)
    b = rdate(rng, dt.date(2006, 9, 1), dt.date(2008, 9, 1))
    grad = b.year + 18
    e = {"Legal name": n, "Date of birth": fmt_date(rng, b), "Email": email_for(rng, n),
         "High school": P(rng, V.SCHOOLS[3:]), "High school graduation year": str(grad),
         "Applicant type": "First-year", "Entry term": P(rng, ["Fall 2027", "Fall 2026", "Spring 2027"]),
         "Cumulative GPA": V.gpa(rng), "Intended major": P(rng, V.MAJORS)}
    contra = {"applicant_type": lambda e: {**e, "Applicant type": "First-year",
                                           "College credits completed": f"{rng.randrange(45, 70)} credits at {P(rng, V.SCHOOLS[:3])}, associate degree 2024",
                                           "High school graduation year": "2019"},
              "grad_before_birth": lambda e: {**e, "High school graduation year": str(b.year - rng.randrange(1, 5))},
              "age_dob": lambda e: {**e, "Age": str(age_on(b) + P(rng, [9, 14, -8]))}}
    hard = {"preferred_name": lambda e: {**e, "Preferred first name": P(rng, ["Alex", "Jo", "Sunny", "Mika"])},
            "email_domain": lambda e: {**e, "Email": email_for(rng, n, "students.example.edu")}}
    return e, contra, hard


def f_he_transfer(rng):
    n = name(rng)
    a = rdate(rng, dt.date(2022, 8, 1), dt.date(2024, 8, 1))
    b2 = a + dt.timedelta(days=rng.randrange(300, 800))
    e = {"Student name": n, "Student ID": V.student_id(rng), "Previous institution": P(rng, V.SCHOOLS[:3] + V.SCHOOLS[4:6]),
         "Attended from": fmt_date(rng, a), "Attended to": fmt_date(rng, b2),
         "Course": P(rng, V.COURSES), "Credits": str(P(rng, [3, 3, 4, 5])), "Grade": P(rng, ["A", "B+", "B", "A-", "C+"])}
    contra = {"date_order": lambda e: {**e, "Attended to": fmt_date(rng, a - dt.timedelta(days=rng.randrange(60, 400)))},
              "credits_grade": lambda e: {**e, "Grade": "Withdrawn (W)", "Credits earned": e["Credits"]}}
    hard = {"email_domain": lambda e: {**e, "Email": email_for(rng, n, "example.com")}}
    return e, contra, hard


def f_he_transcript(rng):
    n = name(rng)
    m = P(rng, ["Electronic PDF", "Mail"])
    e = {"Name while enrolled": n, "Student ID": V.student_id(rng),
         "Date of birth": fmt_date(rng, rdate(rng, dt.date(1970, 1, 1), dt.date(2006, 1, 1))),
         "Number of copies": str(P(rng, [1, 1, 2, 3])), "Delivery method": m}
    if m == "Mail":
        c, s, z = geo(rng)
        e["Mailing address"] = f"{rng.randrange(10, 9999)} {P(rng, V.STREETS)}, {c}, {s} {z}"
    else:
        e["Recipient email"] = email_for(rng, name(rng), "example.edu")
    contra = {"copies": lambda e: {**e, "Delivery method": "Electronic PDF", "Recipient email": email_for(rng, name(rng), "example.edu"),
                                   "Number of copies": "0"},
              "enrolled_dates": lambda e: {**e, "Attended": "2019 to 2016"}}
    hard = {"name_change": lambda e: {**e, "Current name (if different)": f"{n.split(' ')[0]} {P(rng, V.LAST)}"}}
    return e, contra, hard


def f_he_adddrop(rng):
    n = name(rng)
    e = {"Student name": n, "Student ID": V.student_id(rng), "Course": P(rng, V.COURSES) + " section 00" + str(rng.randrange(1, 4)),
         "Term": "Fall 2026", "Action requested": P(rng, ["Late withdrawal", "Late drop"]),
         "Last date attended": fmt_date(rng, rdate(rng, dt.date(2026, 9, 1), dt.date(2026, 11, 20))),
         "Reason": V.vals(V.T["withdrawal_reason"]["pass"], rng)}
    contra = {"term_date": lambda e: {**e, "Last date attended": fmt_date(rng, rdate(rng, dt.date(2025, 1, 10), dt.date(2025, 5, 1)))},
              "action": lambda e: {**e, "Action requested": "Late add", "Reason": "I stopped attending after the second week and want the course removed from my record"}}
    hard = {"email_domain": lambda e: {**e, "Email": email_for(rng, n, "example.com")}}
    return e, contra, hard


def f_he_residency(rng):
    n, (c, s, z) = name(rng), geo(rng)
    moved = rdate(rng, dt.date(2022, 1, 1), dt.date(2025, 6, 1))
    months = (TODAY.year - moved.year) * 12 + TODAY.month - moved.month
    e = {"Student name": n, "Student ID": V.student_id(rng), "Date moved to the state": fmt_date(rng, moved),
         "Months lived in state": str(months), "State of residence claimed": V.STATE_NAMES[s],
         "Driver's license state": s, "City": c, "ZIP": z}
    contra = {"months": lambda e: {**e, "Date moved to the state": fmt_date(rng, dt.date(2026, rng.randrange(4, 8), 3)),
                                   "Months lived in state": str(rng.randrange(18, 40))},
              "geo": lambda e: {**e, **dict(zip(("City", "State of residence claimed", "ZIP"),
                                                (lambda g: (g[0], V.STATE_NAMES[g[1]], g[2]))(wrong_geo(rng, c, s, z))))}}
    hard = {"license_other_state": lambda e: {**e, "Driver's license state": P(rng, [x for x in V.STATE_NAMES if x != s]),
                                              "Note": "License from my previous state; new one appointment is next month"},
            "phone_area": lambda e: {**e, "Phone": f"(312) 555-01{rng.randrange(10, 99)}"}}
    return e, contra, hard


def f_he_housing(rng):
    n = name(rng)
    mi = rdate(rng, dt.date(2026, 8, 15), dt.date(2026, 8, 30))
    mo = mi + dt.timedelta(days=rng.randrange(100, 280))
    e = {"Student name": n, "Student ID": V.student_id(rng), "Term": "Fall 2026 - Spring 2027",
         "Move-in date": fmt_date(rng, mi), "Move-out date": fmt_date(rng, mo),
         "Room type": P(rng, ["Single", "Double", "Suite"]), "Roommate request": P(rng, ["None", name(rng)])}
    contra = {"date_order": lambda e: {**e, "Move-out date": fmt_date(rng, mi - dt.timedelta(days=rng.randrange(10, 60)))},
              "single_roommates": lambda e: {**e, "Room type": "Single", "Roommate request": f"{name(rng)} and {name(rng)}"}}
    hard = {"email_domain": lambda e: {**e, "Email": email_for(rng, n, "example.com")}}
    return e, contra, hard


def f_he_sap(rng):
    n = name(rng)
    cr = rng.randrange(12, 18)
    deps = rng.randrange(0, 3)
    e = {"Student name": n, "Student ID": V.student_id(rng), "Enrollment status": "Full-time",
         "Credits this term": str(cr), "Household size": str(1 + deps + rng.randrange(0, 3)), "Dependents": str(deps),
         "2025 household income": f"${rng.randrange(8, 90) * 1000:,}",
         "SAP appeal statement": V.vals(V.T["sap_appeal"]["pass"], rng)}
    contra = {"enrollment": lambda e: {**e, "Enrollment status": "Full-time", "Credits this term": str(rng.randrange(3, 7))},
              "household": lambda e: {**e, "Household size": "1", "Dependents": str(rng.randrange(2, 4))}}
    hard = {"part_time": lambda e: {**e, "Enrollment status": "Half-time", "Credits this term": "6"}}
    return e, contra, hard


def f_he_access(rng):
    n = name(rng)
    e = {"Student name": n, "Student ID": V.student_id(rng), "Campus email": email_for(rng, n, "students.example.edu"),
         "Accommodations requested": V.vals(V.T["accommodation"]["pass"], rng), "Term": "Fall 2026",
         "Documentation provided?": "Yes, letter from provider attached"}
    contra = {"term_dates": lambda e: {**e, "Needed from": "12/01/2026", "Needed until": "09/01/2026"},
              "docs": lambda e: {**e, "Documentation provided?": "No, nothing attached",
                                 "Documents attached": "provider letter (2 pages), audiology report"}}
    hard = {"email_domain": lambda e: {**e, "Personal email": email_for(rng, n, "example.com")}}
    return e, contra, hard


def f_grant(rng):
    org = P(rng, V.ORGS)
    items, tot = itemize(rng, labels=["Personnel", "Supplies", "Travel", "Evaluation", "Equipment", "Outreach",
                                      "Volunteer stipends", "Training"])
    items = [(l, round(v * 40, 0)) for l, v in items]
    tot = sum(v for _, v in items)
    st = rdate(rng, dt.date(2027, 1, 1), dt.date(2027, 6, 1))
    e = {"Applicant organization": org, "Project director": name(rng), "Amount requested": f"${tot:,.0f}",
         "Budget breakdown": items_text(items).replace(".00", ""), "Project start": fmt_date(rng, st),
         "Project end": fmt_date(rng, st + dt.timedelta(days=rng.randrange(180, 720))),
         "Project summary": V.vals(V.T["grant_summary"]["pass"], rng)}
    contra = {"total": lambda e: {**e, "Amount requested": f"${tot + P(rng, [5000, 12000, -3000]):,.0f}"},
              "date_order": lambda e: {**e, "Project end": fmt_date(rng, st - dt.timedelta(days=rng.randrange(30, 300)))}}
    hard = {"email_domain": lambda e: {**e, "Contact email": email_for(rng, name(rng), "example.org")}}
    return e, contra, hard


def f_k12(rng):
    n = name(rng)
    b = rdate(rng, dt.date(2009, 1, 1), dt.date(2021, 1, 1))
    age = age_on(b)
    grade = max(0, min(12, age - 5))
    e = {"Student name": n, "Student date of birth": fmt_date(rng, b),
         "Grade entering": "Kindergarten" if grade == 0 else str(grade),
         "Previous school": P(rng, V.SCHOOLS[3:]), "Parent / guardian": f"{P(rng, V.FIRST)} {n.split(' ', 1)[1]}",
         "Guardian phone": V.phone(rng), "Home address": V.street(rng)}
    contra = {"age_grade": lambda e: {**e, "Grade entering": str(min(12, grade + rng.randrange(5, 9))) if grade < 6
                                      else "Kindergarten"}}
    hard = {"contact_lastname": lambda e: {**e, "Parent / guardian": name(rng), "Relationship": "Stepmother"}}
    return e, contra, hard


FORMS = {
    "311": ("City 311 service request (report a non-emergency problem)", f_311, False),
    "permit": ("Residential building permit application", f_permit, False),
    "benefits": ("Public benefits intake (SNAP / Medicaid screening)", f_benefits, False),
    "jobapp": ("Job application", f_jobapp, False),
    "event": ("Event registration", f_event, False),
    "patient": ("Patient intake form (new patient, synthetic)", f_patient, False),
    "expense": ("Employee expense report", f_expense, False),
    "vendor": ("Vendor onboarding form", f_vendor, False),
    "leave": ("Employee leave request", f_leave, False),
    "incident": ("Workplace / campus incident report", f_incident, False),
    "k12": ("K-12 school enrollment", f_k12, False),
    "grant": ("Community grant application", f_grant, False),
    "he_admit": ("Undergraduate admissions application", f_he_admit, True),
    "he_transfer": ("Transfer credit evaluation request", f_he_transfer, True),
    "he_transcript": ("Official transcript request", f_he_transcript, True),
    "he_adddrop": ("Late add/drop or late-withdrawal petition", f_he_adddrop, True),
    "he_residency": ("In-state tuition residency application", f_he_residency, True),
    "he_housing": ("Student housing application", f_he_housing, True),
    "he_sap": ("Financial aid verification / SAP appeal", f_he_sap, True),
    "he_access": ("Accessibility accommodation request", f_he_access, True),
}
HELDOUT_FORMS = {"leave", "grant", "k12", "he_residency", "he_housing"}


# --------------------------------------------------------------------------------------------------
def terse(rng, e):
    """Drop optional-looking extras and shorten long answers: terse but real."""
    out = {}
    for k, v in e.items():
        if len(v) > 60 and rng.random() < 0.7:
            v = v.split(", ")[0].split("; ")[0].split(". ")[0]
        out[k] = v
    return out


FAKE_NAMES = ["John Doe", "Jane Doe", "Test User", "asdf asdf", "Mickey Mouse", "Batman", "Seymour Butz",
              "Santa Claus", "Mr. Test", "Abc Xyz", "Harry Potter", "Ima Tester", "Foo Bar"]


def fake(rng, e, kind):
    keys = list(e)
    if kind == "test":
        vals = ["test", "asdf", "123", "test test", "aaa", "xxx", "n/a", "testing", "qwerty", "1"]
        out = {}
        for k in keys:
            kl = k.lower()
            if "name" in kl or kl in ("employee", "reported by", "supervisor", "project director", "contractor",
                                      "emergency contact", "primary contact", "applicant organization"):
                out[k] = P(rng, ["John Doe", "Jane Doe", "Test User", "Test Test", "asdf asdf", "Foo Bar", "Mr. Test"])
            elif "email" in kl:
                out[k] = P(rng, ["test@test.example.com", "asdf@example.com", "a@b.example", "test@example.org"])
            elif "address" in kl or "location" in kl:
                out[k] = P(rng, ["123 Fake St", "123 Test Street", "asdf", "1 Main St Anytown"])
            elif "phone" in kl:
                out[k] = P(rng, ["555-555-5555", "123-456-7890", "0000000000", "1234567"])
            elif "date" in kl or "birth" in kl:
                out[k] = P(rng, ["01/01/2000", "1/1/1900", "11/11/1111", "01/01/2026"])
            else:
                out[k] = P(rng, vals)
        return out
    if kind == "joke":
        pools = ["The Batcave", "fighting crime", "my cat did it", "42", "Hogwarts School", "Gotham City",
                 "the Joker stole my trash cans", "I am a potato", "Area 51", "one billion dollars", "yes",
                 "ask my lawyer, Saul", "because YOLO", "Narnia", "under the sea", "a dragon ate my homework"]
        out = {k: P(rng, pools) for k in keys}
        for k in keys:
            if "name" in k.lower() or k.lower() in ("employee", "reported by"):
                out[k] = P(rng, ["Batman", "Mickey Mouse", "Santa Claus", "Harry Potter", "Seymour Butz",
                                 "Darth Vader", "SpongeBob SquarePants", "Ben Dover"])
        return out
    if kind == "spam":
        links = ["http://cheap-meds.example.net", "http://seo-boost.example.com/offer", "http://crypto-x.example.org",
                 "http://casino-bonus.example.com", "http://followers4u.example.net"]
        pitches = ["BEST SEO SERVICES rank #1 on Google", "Buy followers cheap", "Earn $5000/week from home",
                   "CLICK HERE for free crypto", "Casino bonus 500% no deposit", "Cheap essays written for you"]
        out = {}
        for k in keys:
            out[k] = P(rng, [f"{P(rng, pitches)} {P(rng, links)}", P(rng, links), P(rng, pitches),
                             "Dear Sir/Madam, we offer backlinks " + P(rng, links)])
        return out
    if kind == "mash":
        return {k: V.mash(rng) for k in keys}
    if kind == "partial_test":      # the real form fields, but clearly a developer smoke test
        out = dict(e)
        for k in rng.sample(keys, max(2, len(keys) // 2)):
            out[k] = P(rng, ["test", "TEST - please ignore", "asdf", "testing form submission", "dev test 3"])
        return out
    raise ValueError(kind)


def build(seed=SEED):
    rng = random.Random(seed)
    pack = packs.get_pack(PACK)
    qs = pack["questions"]
    out = {"trainside": [], "test": []}
    seen = set()
    for side, target in TARGET.items():
        fks = [k for k in FORMS if (k in HELDOUT_FORMS) == (side == "test")]
        w = [1.6 if FORMS[k][2] else 1.0 for k in fks]
        tries = 0
        while len(out[side]) < target and tries < target * 50:
            tries += 1
            fk = rng.choices(fks, weights=w)[0]
            desc, fn, _ = FORMS[fk]
            e, contra, hard = fn(rng)
            kind = rng.choices(list(KIND_W), weights=list(KIND_W.values()))[0]
            if kind == "clean":
                if rng.random() < 0.35:
                    e, fam = terse(rng, e), "clean_terse"
                else:
                    fam = "clean"
                gold = {"contradiction": False, "genuine": True}
            elif kind == "contra":
                ck = P(rng, sorted(contra))
                e, fam = contra[ck](e), f"contra_{ck}"
                gold = {"contradiction": True, "genuine": True}
            elif kind == "hardneg":
                hk = P(rng, sorted(hard))
                if hk == "contact_lastname" and "Emergency contact" in e:
                    e = {**e, "Emergency contact": name(rng)}
                e, fam = hard[hk](e), f"topic_hardneg_{hk}"
                gold = {"contradiction": False, "genuine": True}
            else:
                fk_kind = rng.choices(["test", "joke", "spam", "mash", "partial_test"], weights=[3, 2, 2, 1, 2])[0]
                e, fam = fake(rng, e, fk_kind), f"fake_{fk_kind}"
                gold = {"contradiction": False, "genuine": False}
            e = {k: v for k, v in e.items() if str(v).strip()}
            entries = json.dumps(e, ensure_ascii=False)
            if (fk, entries) in seen:
                continue
            seen.add((fk, entries))
            state = packs.build_state(pack, form=desc, entries=entries)
            out[side].append({"family": f"fc/{fam}/{fk}", "state": state, "questions": qs, "gold": gold})
    rng.shuffle(out["trainside"])
    nval = int(len(out["trainside"]) * VAL_FRAC)
    splits = {"val": out["trainside"][:nval], "train": out["trainside"][nval:], "test": out["test"]}
    for s, rows in splits.items():
        rng.shuffle(rows)
        for n, r in enumerate(rows):
            r["id"] = f"{PACK}-{s}-{n:04d}"
    return splits


def stats(splits):
    from collections import Counter
    rep = {}
    for s, rows in splits.items():
        kinds = Counter(r["family"].split("/")[1].split("_")[0] if not r["family"].split("/")[1].startswith("topic")
                        else "hardneg" for r in rows)
        rep[s] = {"rows": len(rows), "contradiction_true": sum(r["gold"]["contradiction"] for r in rows),
                  "genuine_false": sum(not r["gold"]["genuine"] for r in rows), "kinds": dict(kinds),
                  "forms": sorted({r["family"].rsplit("/", 1)[1] for r in rows}),
                  "he_rows": sum(FORMS[r["family"].rsplit("/", 1)[1]][2] for r in rows)}
    return rep


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stats", action="store_true")
    ap.add_argument("--out", default=HERE)
    a = ap.parse_args()
    splits = build()
    print(json.dumps(stats(splits), indent=1))
    if a.stats:
        return
    for s, rows in splits.items():
        with open(os.path.join(a.out, f"{s}.jsonl"), "w") as f:
            for r in rows:
                f.write(json.dumps({k: r[k] for k in ("id", "family", "state", "questions", "gold")},
                                   ensure_ascii=False) + "\n")
    print(f"forms: {len(FORMS)}  wrote {', '.join(f'{s}={len(r)}' for s, r in splits.items())}")


if __name__ == "__main__":
    main()
