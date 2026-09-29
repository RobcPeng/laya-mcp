#!/usr/bin/env python3
"""Generate the form-field-validation set: one form text-field entry -> category / needs_review / quality.

    python datasets/form-field-validation/generate.py            # writes train/val/test.jsonl here
    python datasets/form-field-validation/generate.py --stats    # print label balance only

Stdlib only, seeded, deterministic. Every value is synthetic: invented names, 555-01xx phone numbers,
example.com / example.org addresses, invalid SSN patterns (000-xx-xxxx) and published test card numbers.

Row format (the pack's questions come from laya_mcp.packs, verbatim, so a fine-tuned checkpoint is
asked exactly what it learned):
  {"id", "family", "state": {"form", "field", "entry"}, "questions": {...}, "gold":
   {"category": <FIELD_CATEGORIES key>, "needs_review": bool, "quality": 0-3}}

`field` is built exactly like laya_mcp.forms._field_text: "Label: description".

Splits: TEST holds out whole forms (HELDOUT_FORMS) and whole field types (HELDOUT_TYPES). No row in
train/val comes from a held-out form or a held-out field type, so test accuracy measures
generalization to forms and fields the model never saw. VAL is a random slice of the train side.

Labeling decisions (see README.md):
  * number words where a numeric amount/quantity is asked ("twelve hundred") -> wrong_format
  * impossible dates (13/45/2026), email without a TLD, too few phone digits -> wrong_format
  * a structured value of another kind (phone in a name field, a date in an amount field) -> wrong_type
  * a coherent sentence that answers a different question -> off_topic
  * on topic but too vague to act on ("broken", first name only in a full-name field) -> incomplete
  * "n/a" / "none" in a field marked optional, or where "none" is a real answer (medications) -> pass
  * a real description that mentions a password reset or a declined card -> pass
  * mild profanity inside a real complaint -> pass; insults, threats, spam -> abusive
"""
import argparse
import json
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, ROOT)
from laya_mcp import packs  # noqa: E402

SEED = 20260930
PACK = "form-field-validation"
TARGET = {"trainside": 2500, "test": 620}
VAL_FRAC = 0.1

# --------------------------------------------------------------------------------------------------
# value pools (all invented)
FIRST = ["Maria", "James", "Aisha", "Wei", "Diego", "Priya", "Tomasz", "Keiko", "Olusegun", "Hannah",
         "Mateo", "Fatima", "Liam", "Nguyen", "Sofia", "Dmitri", "Amara", "Jonah", "Lucia", "Ravi",
         "Grace", "Hamid", "Elena", "Kwame", "Rosa", "Arjun", "Chloe", "Tariq", "Ingrid", "Marcus",
         "José", "Zoë", "Siobhan", "Björn", "Anh", "Malia", "Ezra", "Yusuf", "Camila", "Declan"]
LAST = ["Garcia", "Okafor", "Chen", "Patel", "Kowalski", "Tanaka", "Adeyemi", "Brennan", "Haddad",
        "Lindqvist", "Morales", "Nakamura", "O'Brien-Nguyen", "Fitzgerald", "Mbeki", "Rossi", "Ivanova",
        "Sandoval", "Whitfield", "Castellanos", "Delacroix", "Yamamoto", "Abernathy", "Quispe",
        "Van der Berg", "McAllister", "St. Clair", "Nwosu", "Holloway", "Petrov", "Da Silva", "Kaur"]
ORGS = ["Front Range Paving LLC", "Blue Mesa Consulting", "Aspen Hollow Dental", "Northside Food Bank",
        "Summit Ridge Elementary PTA", "Canyon Creek Electric", "Harbor & Pine Architects",
        "Tri-County Health Collaborative", "Red Rock Robotics Inc.", "Meadowlark Catering Co.",
        "Juniper Street Books", "Clearwater Analytics Group", "Pinecrest Lawn Care", "Riverbend Credit Union",
        "Silver Spur Events", "Granite Peak Plumbing", "Lantern Youth Theater", "Oakline Freight"]
TITLES = ["Project Manager", "Registered Nurse", "Senior Accountant", "teacher", "Line Cook",
          "Software Engineer II", "Office Manager", "HVAC Technician", "Graduate Research Assistant",
          "Director of Operations", "Paralegal", "Warehouse Associate", "Grant Writer", "sales rep",
          "Payroll Specialist", "Assistant Professor of Biology", "Customer Success Lead", "Electrician (journeyman)"]
STREETS = ["Main St", "Pearl St", "Oak Ave", "E Colfax Ave", "Elm Street", "W 14th Ave", "S Broadway",
           "Juniper Ln", "Mountain View Dr", "N College Ave", "Cedar Ct", "Larimer St", "Maple Rd",
           "Aspen Way", "Sunset Blvd", "Railroad Ave", "County Road 12", "Old Mill Rd"]
CITYSTATEZIP = [("Denver", "CO", "80202"), ("Boulder", "CO", "80302"), ("Fort Collins", "CO", "80521"),
                ("Colorado Springs", "CO", "80903"), ("Albuquerque", "NM", "87102"), ("Santa Fe", "NM", "87501"),
                ("Salt Lake City", "UT", "84101"), ("Provo", "UT", "84601"), ("Boise", "ID", "83702"),
                ("Cheyenne", "WY", "82001"), ("Phoenix", "AZ", "85004"), ("Tucson", "AZ", "85701"),
                ("Austin", "TX", "78701"), ("Madison", "WI", "53703"), ("Columbus", "OH", "43215"),
                ("Raleigh", "NC", "27601"), ("Portland", "OR", "97201"), ("Lincoln", "NE", "68508")]
STATE_NAMES = {"CO": "Colorado", "NM": "New Mexico", "UT": "Utah", "ID": "Idaho", "WY": "Wyoming",
               "AZ": "Arizona", "TX": "Texas", "WI": "Wisconsin", "OH": "Ohio", "NC": "North Carolina",
               "OR": "Oregon", "NE": "Nebraska"}
MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September",
          "October", "November", "December"]
EMAIL_DOM = ["example.com", "example.org", "mail.example.com", "example.net", "students.example.edu"]
COURSES = ["MATH 1410", "ENGL 1020", "CHEM 1113", "PSYC 2100", "HIST 1215", "CS 2270", "BIOL 1500",
           "ECON 2010", "SPAN 1010", "PHYS 2210", "ART 1300", "NURS 3150", "COMM 1500", "STAT 2600"]
SCHOOLS = ["Front Range Community College", "Pikes Peak State College", "University of Northern Plains",
           "Mesa Verde High School", "Clearwater Technical Institute", "Red Butte University",
           "Lakeside Online Academy", "St. Brendan Preparatory School", "Arapahoe Valley College"]
MAJORS = ["Nursing", "Mechanical Engineering", "undeclared", "Psychology", "Computer Science",
          "Elementary Education", "Business Administration", "Biology (pre-med)", "Film Studies",
          "Environmental Science", "Criminal Justice", "Music Performance", "Accounting"]


def P(rng, xs):
    return xs[rng.randrange(len(xs))]


def phone(rng):
    a = P(rng, ["303", "720", "970", "719", "505", "801", "208", "512", "608"])
    n = f"01{rng.randrange(100):02d}"
    return P(rng, [f"({a}) 555-{n}", f"{a}-555-{n}", f"{a}.555.{n}", f"+1 {a} 555 {n}", f"{a}555{n}",
                   f"1-{a}-555-{n}", f"{a} 555 {n}"])


def person(rng):
    f, l = P(rng, FIRST), P(rng, LAST)
    s = P(rng, [f"{f} {l}", f"{f} {l}", f"{f} {l}", f"{l}, {f}", f"{f} {P(rng, 'ABCDEJKMRT')}. {l}",
                f"{f.lower()} {l.lower()}", f"{f.upper()} {l.upper()}", f"Dr. {f} {l}", f"{f} {l} Jr."])
    return s


def email(rng):
    f, l = P(rng, FIRST), P(rng, LAST)
    f = f.lower().replace("é", "e").replace("ë", "e").replace("ö", "o").replace("ó", "o")
    l = l.lower().replace("'", "").replace(" ", "").replace("-", "").replace(".", "")
    u = P(rng, [f"{f}.{l}", f"{f[0]}{l}", f"{f}{rng.randrange(10, 99)}", f"{l}.{f}", f"{f}_{l}"])
    return f"{u}@{P(rng, EMAIL_DOM)}"


def street(rng):
    n = rng.randrange(10, 9999)
    s = f"{n} {P(rng, STREETS)}"
    return P(rng, [s, s, s.lower(), s + f", Apt {rng.randrange(1, 40)}{P(rng, ['', 'B', 'C'])}",
                   s + f" Unit {rng.randrange(100, 400)}", f"PO Box {rng.randrange(100, 9999)}"])


def cityv(rng):
    c = P(rng, CITYSTATEZIP)[0]
    return P(rng, [c, c, c.lower(), c.upper()])


def date(rng, lo=2024, hi=2027):
    y, m, d = rng.randrange(lo, hi), rng.randrange(1, 13), rng.randrange(1, 29)
    return P(rng, [f"{m:02d}/{d:02d}/{y}", f"{m}/{d}/{y}", f"{y}-{m:02d}-{d:02d}", f"{MONTHS[m-1]} {d}, {y}",
                   f"{d} {MONTHS[m-1][:3]} {y}", f"{m}/{d}/{str(y)[2:]}", f"{MONTHS[m-1][:3]} {d} {y}"])


def dob(rng):
    return date(rng, 1940, 2008)


def amount(rng):
    v = rng.choice([rng.randrange(5, 300) + rng.choice([0, 0.5, 0.99, 0.25]), rng.randrange(300, 25000)])
    return P(rng, [f"${v:,.2f}", f"{v:.2f}", f"{int(v)}", f"${int(v):,}", f"USD {v:,.2f}", f"{v:,.2f}"])


def spelled_amount(rng):
    return P(rng, ["twelve hundred", "fifty dollars", "about three hundred", "one thousand five hundred",
                   "ninety-nine and 50 cents", "two grand", "forty five bucks", "seventy-five dollars even"])


def time_v(rng):
    h, m = rng.randrange(1, 13), P(rng, [0, 15, 30, 45, 0])
    return P(rng, [f"{h}:{m:02d} {P(rng, ['AM', 'PM', 'am', 'pm'])}", f"{h}{P(rng, ['am', 'pm'])}",
                   f"{rng.randrange(7, 20):02d}:{m:02d}", "noon", f"{h}:{m:02d}pm"])


def url(rng):
    s = P(rng, ["frontrangepaving", "bluemesa", "northsidefoodbank", "redrockrobotics", "portfolio",
                "janedoe-design", "meadowlarkcatering", "lanternyouth"])
    return P(rng, [f"https://www.{s}.example.com", f"www.{s}.example.org", f"{s}.example.com",
                   f"https://example.org/{s}", f"http://{s}.example.net/about"])


def zipv(rng):
    z = P(rng, CITYSTATEZIP)[2]
    return P(rng, [z, z, z, f"{z}-{rng.randrange(1000, 9999)}"])


def statev(rng):
    s = P(rng, CITYSTATEZIP)[1]
    return P(rng, [s, s, STATE_NAMES[s], s.lower(), STATE_NAMES[s].lower()])


def qty(rng):
    return str(P(rng, [1, 2, 2, 3, 4, 5, 6, 8, 10, 12, 20, 25, 40, 150]))


def case_no(rng):
    return P(rng, [f"SR-2026-{rng.randrange(10000, 99999)}", f"{rng.randrange(1000000, 9999999)}",
                   f"CASE #{rng.randrange(100000, 999999)}", f"PR{rng.randrange(20000, 99999)}",
                   f"26-{rng.randrange(1000, 9999)}", f"TKT-{rng.randrange(1000, 99999)}"])


def student_id(rng):
    return P(rng, [f"S{rng.randrange(10000000, 99999999)}", f"{rng.randrange(800000000, 899999999)}",
                   f"{rng.randrange(1000000, 9999999)}", f"A0{rng.randrange(1000000, 9999999)}"])


def gpa(rng):
    g = round(rng.uniform(2.0, 4.0), 2)
    return P(rng, [f"{g:.2f}", f"{g:.1f}", f"{g:.2f}/4.0", f"{g:.2f} unweighted"])


def term(rng):
    return P(rng, ["Fall 2026", "Spring 2027", "fall 26", "Summer 2026", "Spring semester 2027",
                   "Fall 2026 (full term)", "2027 spring", "Winter session 2026"])


def course(rng):
    c = P(rng, COURSES)
    return P(rng, [c, c.replace(" ", ""), c.lower(), f"{c} section 002", f"{c} - Intro"])


# --------------------------------------------------------------------------------------------------
# generic failure pools
PLACEHOLDER = ["n/a", "N/A", "none", "NONE", "test", "TEST", "asdf", "-", ".", "TBD", "tbd", "see above",
               "lorem ipsum", "Lorem ipsum dolor sit amet", "xxx", "XXXX", "???", "na", "null", "...",
               "same", "idk", "testing 123", "placeholder", "sample", "abc", "--", "?", "test test",
               "same as above", "no", "nil", "fill in later", "will add later", "blah", "aaa", "x",
               "your answer here", "enter text", "0000"]
PLACEHOLDER_NOT_NONE = [p for p in PLACEHOLDER if p.lower() not in ("n/a", "na", "none", "nil", "no", "same",
                                                                     "same as above", "see above")]
PLACEHOLDER_NUMERIC_OK = [p for p in PLACEHOLDER if p not in ("0000",)]

UNICODE_JUNK = ["ꙮ҉ ▓▒░ ¤¤¤", "∆∆∆ ✧✧ ⌘⌘⌘", "¯\\_(ツ)_/¯¯¯ ♒♒", "ʕ•ᴥ•ʔ ♜♜♜ ⍝⍝", "▢▢▢▢ ⊞⊞ ⊠",
                "ᚠᚢᚦᚨ ᚱᚲ ᚷᚹ", "✦✦✦ ☍☍ ⚇⚇", "⺁⺂⺃⺄ ⺅", "ơ̷̢͓ ͍̹ͅẓ̶ ̧̛̞", "§§§ ¶¶ ¤¤ ©©"]
ROWS = ["qwertyuiop", "asdfghjkl", "zxcvbnm", "poiuytrewq", "lkjhgfdsa", "mnbvcxz"]


def mash(rng, digits_ok=True):
    k = rng.random()
    if k < 0.35:
        r = P(rng, ROWS)
        s = "".join(r[rng.randrange(len(r))] for _ in range(rng.randrange(8, 22)))
    elif k < 0.55:
        cons = "bcdfghjklmnpqrstvwxz"
        s = " ".join("".join(P(rng, cons) for _ in range(rng.randrange(4, 9))) for _ in range(rng.randrange(1, 4)))
    elif k < 0.75 and digits_ok:
        pool = "abcdefghijklmnopqrstuvwxyz0123456789;[]"
        s = "".join(P(rng, pool) for _ in range(rng.randrange(10, 20)))
    elif k < 0.88:
        s = P(rng, UNICODE_JUNK)
    else:
        s = "".join(P(rng, "jfkdlsa;") for _ in range(rng.randrange(6, 12))) + " " + \
            "".join(P(rng, "hgjfkd") for _ in range(rng.randrange(6, 12)))
    return s


OFFTOPIC_GENERIC = [
    "What time does the library open?", "Can I pay my water bill on this site?", "Is the pool open on Sundays?",
    "I love the new bike lanes downtown, keep it up.", "My favorite color is blue.",
    "Do you know if the DMV takes walk-ins?", "Where do I park for the football game?",
    "Just wanted to say the staff at the front desk were lovely last week.",
    "How do I sign up for the recycling newsletter?", "The weather has been great this week.",
    "Can someone tell me when trash pickup moves for the holiday?", "I'm looking for a good pizza place nearby.",
    "Who won the game last night?", "Does the rec center have pickleball courts?",
    "Please let me know about summer camp dates for my kids.", "Is there a lost and found at city hall?",
    "My cat just had kittens if anyone wants one.", "When is the next farmers market?",
    "How many credits do I need to graduate?", "Can I bring a guest to the dining hall?",
    "What's the wifi password in the student union?", "I think the website is really slow today.",
]

INCOMPLETE_GENERIC = ["broken", "stuff", "yes", "problem", "help", "it's bad", "the thing", "issue",
                      "please fix", "not working", "fix it", "you know", "same issue as before", "things",
                      "various", "idk, the usual", "important", "urgent", "bad", "other", "ok", "need this"]

SENSITIVE = [
    "my social is zero zero zero, one two, three four five six if you need it",
    "the login is admin / Summer2026! so you can check my account",
    "Card number 4111 1111 1111 1111 exp 09/29 cvv 123, charge the fee to that",
    "SSN 000-12-3456 for verification",
    "you can log in as me, username jgarcia password Tr0ub4dor&3",
    "my pw is BlueHorse!77 in case you need to get into the portal",
    "here is my social security number: 000 45 6789",
    "use my visa 4012 8888 8888 1881 for the deposit",
    "My portal password is Winter#2025 and my username is my student ID",
    "social: triple zero dash two two dash one one one one",
    "the account passcode is 8841, PIN for the card is 0912",
    "I'll just put my SSN here so you have it, 000-98-7654",
    "api key sk-test-9f8e7d6c5b4a for the vendor portal, don't share",
    "Mastercard 5555 5555 5555 4444, security code 321",
    "my banking login is rgarcia88 / Pa55word!",
    "for the background check my social is 000-33-4444",
    "the door code is 4471# and the alarm password is 'bluebird'",
    "Amex 3782 822463 10005 exp 11/28",
    "passport number X00000000, date of issue 2019, if that helps",
    "driver's license 000-000-000, my password for email is sunflower2026",
]


def sensitive_in_context(rng, base):
    s = P(rng, SENSITIVE)
    return P(rng, [s, f"{base} {s}", f"{s}. {base}", s[:1].upper() + s[1:]])


ABUSIVE = [
    "you people are useless idiots, fix it or else", "this city is run by morons and you're one of them",
    "go to hell, nobody ever answers these", "shut up and do your damn job, clowns",
    "BUY CHEAP FOLLOWERS NOW http://cheap-followers.example.com/promo",
    "Earn $5000 a week from home!!! click http://get-rich.example.net", "CRYPTO GIVEAWAY >>> visit bit-deal.example.org",
    "whoever reads this is a pathetic loser", "screw you and your stupid form",
    "f*** this form and f*** everyone who made it", "you're all incompetent garbage",
    "hot singles in your area -> http://dating-spam.example.com", "lol you guys suck so bad",
    "the clerk who helped me is a brainless idiot",
]
THREATS = [
    "if this isn't fixed by friday I'll come down there and make someone pay",
    "I know where the manager lives, remember that",
    "keep ignoring me and see what happens to your office",
    "somebody at that front desk is going to get hurt if I have to come back",
    "I'll burn this place down if my appeal is denied",
    "you'd better watch your back, professor",
]


# --------------------------------------------------------------------------------------------------
# field types. kind: "struct" (a single datum) or "text" (free text).
# pass: callable(rng) -> str or list of str; confusers: field types whose pass values are wrong_type here;
# fmt: wrong_format values (callable or list); inc: incomplete values; none_ok: "none"/"n/a" is a real answer.
T = {}


def ft(key, kind, pass_, confusers=(), fmt=None, inc=None, none_ok=False, sens=None):
    T[key] = {"kind": kind, "pass": pass_, "confusers": list(confusers), "fmt": fmt, "inc": inc,
              "none_ok": none_ok, "sens": sens if sens is not None else (kind == "text")}


def L(xs):
    return lambda rng: P(rng, xs)


ft("full_name", "struct", person, ["phone", "email", "date", "street_address", "amount"],
   inc=lambda rng: P(rng, [P(rng, FIRST), P(rng, FIRST).lower(), P(rng, "ABCDEJKMRT") + ".", "Mr. " + P(rng, LAST)]))
ft("first_name", "struct", lambda rng: P(rng, FIRST + [f.lower() for f in FIRST] + ["Mary-Kate", "Jean-Luc", "D'Andre"]),
   ["phone", "email", "date", "zip"])
ft("last_name", "struct", lambda rng: P(rng, LAST + [l.lower() for l in LAST[:10]]), ["phone", "email", "date", "zip"])
ft("org_name", "struct", lambda rng: P(rng, ORGS + [o.lower() for o in ORGS[:6]] + ["City of Lakewood Parks Dept.", "self-employed"]),
   ["phone", "email", "date", "amount"], inc=L(["LLC", "company", "my business", "Inc.", "a nonprofit"]))
ft("job_title", "struct", L(TITLES), ["phone", "date", "email", "amount"],
   inc=L(["worker", "job", "employee", "staff", "yes", "work"]))
ft("street_address", "struct", street, ["email", "phone", "full_name", "date"],
   fmt=None, inc=lambda rng: P(rng, [P(rng, STREETS), str(rng.randrange(10, 9999)), "near the park", "downtown",
                                     "by the school"]))
ft("apt_unit", "struct", lambda rng: P(rng, ["N/A", "n/a", "none", f"Apt {rng.randrange(1, 40)}", f"#{rng.randrange(100, 600)}",
                                             f"Unit {P(rng, 'ABCD')}", "-", f"Suite {rng.randrange(100, 400)}", "2B", ""]),
   ["email", "phone", "date"], none_ok=True)
ft("city", "struct", cityv, ["zip", "phone", "email", "date"])
ft("state", "struct", statev, ["zip", "phone", "full_name"],
   fmt=L(["C0", "Colorodo", "NMM", "Texs", "U.T.A.H.", "12"]))
ft("zip", "struct", zipv, ["city", "phone", "email", "full_name"],
   fmt=lambda rng: P(rng, [P(rng, CITYSTATEZIP)[2][:4], P(rng, CITYSTATEZIP)[2] + "9", "8O202", "80-202", "ZIP 8020"]))
ft("date_of_birth", "struct", dob, ["full_name", "phone", "amount", "city"],
   fmt=L(["13/45/1990", "02/30/1985", "1990-14-02", "32 March 1978", "00/00/1999", "7/77/77", "1985/2/31", "Feb 30 2001"]))
ft("event_date", "struct", date, ["full_name", "phone", "amount", "city", "email"],
   fmt=L(["13/45/2026", "2026-02-30", "32/01/2026", "Juneteenth 2O26", "9/31/2026", "2026/13/01", "11-31-26", "0/0/2026"]))
ft("start_date", "struct", date, ["full_name", "phone", "amount", "email"],
   fmt=L(["13/45/2026", "2026-02-30", "31/31/26", "Sept 31 2026", "2026-00-10", "14/14/2026"]))
ft("appt_time", "struct", time_v, ["phone", "date", "full_name", "amount"],
   fmt=L(["25:30", "9:75 am", "13pm", "99:00", "12:60 PM", "0:0:0", "7:5 o'clockk"]))
ft("phone", "struct", phone, ["email", "full_name", "date", "street_address"],
   fmt=lambda rng: P(rng, ["303-555", "555-01", "(720) 555-01", "303-555-01423", "3O3-555-0142",
                           "555 555 55", "phone 720555", "+1 (303) 5550", "970-555-014x"]))
ft("email", "struct", email, ["phone", "street_address", "full_name", "website"],
   fmt=lambda rng: P(rng, ["jane.doe@example", "maria.garcia.example.com", "wchen@@example.org", "priya patel@example.com",
                           "tomasz@example,com", "@example.com", "diego@", "k.tanaka@example..org", "hannah.brennan@examplecom",
                           "liam at example dot com"]))
ft("website", "struct", url, ["email", "phone", "full_name"],
   fmt=L(["htp:/bluemesa.example", "www bluemesa example com", "https//example.org/about", "http:\\\\example.com",
          "bluemesa .example. com", "https://"]))
ft("amount", "struct", amount, ["date", "full_name", "phone", "email"], fmt=lambda rng: spelled_amount(rng) if rng.random() < 0.55
   else P(rng, ["$12.34.56", "1,2,3", "12..50", "$$40", "4O0.00", "100-ish$", "3.5.0 USD"]))
ft("quantity", "struct", qty, ["date", "full_name", "email", "phone"],
   fmt=L(["three", "a dozen", "two or three", "10-", "1O", "5.5.5", "twenty"]))
ft("case_number", "struct", case_no, ["email", "full_name", "date", "phone"],
   fmt=L(["SR-", "#", "SR2026", "12", "case no.", "SR-2026-"]))
ft("student_id", "struct", student_id, ["email", "phone", "full_name", "date"],
   fmt=L(["S12", "80012", "S-1234-", "9999", "A0", "ID#"]))
ft("gpa", "struct", gpa, ["date", "full_name", "phone"],
   fmt=L(["3,7", "3.75.2", "4.8/4.0", "37", "A-ish", "3..5", "-2.0"]))
ft("term", "struct", term, ["date", "phone", "full_name", "amount"],
   fmt=L(["Fall 20266", "Semester 13", "Sprung 2027", "F26S27", "2026-2027-2028"]))
ft("course_code", "struct", course, ["full_name", "phone", "email", "date"],
   inc=L(["math", "english", "the chem class", "a science course", "intro"]))
ft("school_name", "struct", L(SCHOOLS + [s.lower() for s in SCHOOLS[:4]]), ["phone", "email", "date", "amount"],
   inc=L(["college", "high school", "a university", "school", "the community college"]))
ft("major", "struct", L(MAJORS), ["phone", "date", "email", "amount"], inc=L(["science", "a major", "something", "degree"]))
ft("country", "struct", L(["United States", "USA", "Mexico", "Canada", "India", "Nigeria", "Vietnam", "Germany",
                           "Brazil", "Philippines", "us", "South Korea"]), ["phone", "date", "full_name", "zip"],
   fmt=L(["Untied Stats", "U$A", "Mexcio", "Kanada"]))
ft("relationship", "struct", L(["Mother", "father", "Spouse", "Sister", "Brother", "Friend", "Partner", "Aunt",
                               "Grandmother", "Legal guardian", "roommate", "Son", "Daughter"]),
   ["phone", "date", "email", "amount"], inc=L(["family", "relative", "person", "someone"]))
ft("hours_per_week", "struct", lambda rng: P(rng, [str(rng.randrange(4, 45)), f"{rng.randrange(10, 40)} hrs",
                                                   f"about {rng.randrange(10, 40)}", "20-25", "40 (full time)"]),
   ["date", "phone", "full_name"], fmt=L(["twenty-ish hours", "40/7/52", "-10", "1O", "8 per day 5 days maybe"]))
ft("years_experience", "struct", lambda rng: P(rng, [str(rng.randrange(0, 30)), f"{rng.randrange(1, 25)} years",
                                                     "less than 1", "6 months", f"{rng.randrange(2, 15)}+"]),
   ["date", "phone", "email", "full_name"], fmt=L(["ten-ish yrs", "5..", "-3", "1O years"]))
ft("insurance_member_id", "struct", lambda rng: P(rng, [f"XJH{rng.randrange(100000000, 999999999)}", f"W{rng.randrange(10000000, 99999999)}",
                                                        f"MBR-{rng.randrange(100000, 999999)}-0{rng.randrange(1, 9)}"]),
   ["full_name", "phone", "email", "date"], fmt=L(["XJH", "MBR-", "12", "W-"]))
ft("invoice_number", "struct", lambda rng: P(rng, [f"INV-{rng.randrange(1000, 99999)}", f"{rng.randrange(10000, 999999)}",
                                                   f"2026-{rng.randrange(100, 999)}", f"PO {rng.randrange(1000, 9999)}"]),
   ["full_name", "email", "date", "phone"], fmt=L(["INV-", "#", "inv no", "0"]))
ft("permit_parcel", "struct", lambda rng: P(rng, [f"{rng.randrange(1000, 9999)}-{rng.randrange(10, 99)}-{rng.randrange(1, 9)}-{rng.randrange(10, 99)}-{rng.randrange(100, 999)}",
                                                  f"BLD2026-{rng.randrange(1000, 9999)}", f"Parcel {rng.randrange(100000, 999999)}"]),
   ["email", "full_name", "phone"], fmt=L(["BLD-", "parcel", "12", "BLD2026-"]))
ft("yes_no", "struct", L(["Yes", "no", "yes, one wheelchair space", "No thanks", "Y", "N", "yes please", "Nope",
                          "Yes - ground floor preferred", "not needed"]), ["phone", "email", "date", "amount"],
   none_ok=True)
ft("how_heard", "struct", L(["Friend", "Instagram", "a coworker told me", "Google search", "flyer at the library",
                             "radio ad", "school counselor", "email newsletter", "LinkedIn", "walked by the office"]),
   ["phone", "email", "date", "amount"], inc=L(["online", "somewhere", "people", "internet I think"]))
ft("dietary", "struct", L(["none", "N/A", "vegetarian", "vegan", "gluten-free", "no pork", "nut allergy (severe)",
                           "lactose intolerant", "halal", "kosher", "shellfish allergy", "no restrictions"]),
   ["phone", "email", "date", "amount"], none_ok=True)
ft("medications", "text", L(["None", "none currently", "lisinopril 10mg daily", "metformin 500 mg twice a day",
                             "Albuterol inhaler as needed", "levothyroxine 50mcg; vitamin D", "birth control pill",
                             "ibuprofen occasionally for back pain", "sertraline 50 mg", "no medications"]),
   ["phone", "email", "date", "amount"], inc=L(["pills", "some meds", "the usual ones", "a few", "stuff for my heart"]),
   none_ok=True)

# free-text fields: pass lists, plus field-specific incomplete answers
TEXT = {
    "issue_311": (["Pothole, 3rd & Main, eastbound lane", "Streetlight out on the corner of Oak and 14th since Monday",
                   "Large pothole in front of 1420 Pearl St, about 2 ft wide, cars swerving into bike lane",
                   "graffiti on the underpass at Cedar Ct and Railroad Ave, spray paint on both walls",
                   "Missed trash pickup on Juniper Ln this week, whole block",
                   "Fallen tree branch blocking sidewalk on W 14th Ave near the bus stop",
                   "Water main leak? water bubbling up from the street at Elm and 5th since last night",
                   "Traffic signal stuck on red at S Broadway & Maple Rd, northbound",
                   "dead deer on shoulder of County Road 12 by mile marker 4",
                   "Abandoned couch and mattress dumped in alley behind 2200 Larimer",
                   "Damn pothole ate my tire on Aspen Way near the school, please patch it",
                   "Crosswalk paint totally faded at N College & Maple, kids cross there every morning"],
                  ["pothole", "light out", "trash", "street", "road problem", "tree"]),
    "permit_work": (["Replace existing 40-gallon water heater with a 50-gallon gas unit, same location in garage",
                     "Build a 12x16 detached shed in the backyard, no electrical",
                     "Kitchen remodel: remove non-load-bearing wall, add two circuits, new sink location",
                     "Re-roof, tear off one layer of asphalt shingles, replace with architectural shingles",
                     "Install 7.2 kW rooftop solar array with battery backup",
                     "fence replacement, 6 ft cedar privacy fence along rear property line, ~120 ft",
                     "Finish basement: framing, drywall, one bathroom with shower, egress window"],
                    ["remodel", "construction", "work on house", "building stuff", "roof"]),
    "records_request": (["All emails between the Parks Director and Front Range Paving LLC from Jan 1 to Mar 31, 2026 about the Oak Ave trail contract",
                         "Police incident report for the traffic collision at S Broadway & Maple Rd on 04/12/2026",
                         "Copies of restaurant health inspection reports for Meadowlark Catering Co. for 2024-2026",
                         "The signed contract and all change orders for the Larimer St streetscape project",
                         "Council meeting minutes and audio recordings from the June 2026 budget sessions",
                         "Body-worn camera footage from the call to 1420 Pearl St on May 3, 2026, 9-10pm",
                         "Building permits issued for parcel 5123-10-2-33-004 since 2015"],
                        ["records", "everything", "all documents", "emails", "info about the city"]),
    "reason": (["I need an official copy for a job application that requires proof of my degree",
                "Moving out of state and my new employer asked for it",
                "Requesting a review because my circumstances changed after a family medical emergency",
                "To verify my enrollment for my health insurance",
                "I was charged twice and would like the duplicate refunded",
                "Needed for a mortgage application, lender asked by the 15th",
                "short-term rental license renewal"],
               ["because", "need it", "personal", "reasons", "just because", "for stuff"]),
    "comments": (["N/A", "none", "Thanks!", "Please call after 3pm, I work nights", "Gate code is at the front office",
                  "I may be 10 minutes late because of the bus schedule", "no comments", "",
                  "Happy to provide more documentation if needed", "My password reset link expired twice, just so you know"],
                 None),
    "incident": (["Slipped on an unmarked wet floor near the east entrance of the rec center around 6pm, bruised my knee",
                  "A forklift clipped a shelving unit in aisle 7, no injuries, two pallets damaged",
                  "Student fainted in the chemistry lab during the afternoon section; EMTs called, she was released",
                  "Someone broke the passenger window of a fleet vehicle parked in Lot C overnight",
                  "Coworker cut his hand on a box cutter while unloading, first aid applied, went to urgent care",
                  "Smoke alarm went off on the 3rd floor of Aspen Hall at 2am, burnt popcorn, building evacuated 20 min"],
                 ["accident", "someone got hurt", "incident happened", "broke", "fell"]),
    "support_issue": (["I can't log in to the portal, I requested a password reset but the email never arrives",
                       "My card was declined when I tried to pay the invoice, but the bank says there is no hold",
                       "The export to CSV button does nothing in Chrome, works in Firefox",
                       "Order #48213 arrived with a cracked screen, need a replacement",
                       "App crashes every time I open the Reports tab after the latest update",
                       "Two-factor codes are coming in late (5+ min) so they expire before I can use them",
                       "I was billed for the Pro plan after downgrading to Basic on the 3rd"],
                      ["doesn't work", "error", "broken", "login", "help me", "account issue"]),
    "expense_purpose": (["Client dinner with Riverbend Credit Union team re: Q3 renewal",
                         "Mileage for site visits to the Boulder and Fort Collins offices",
                         "Conference registration, Rocky Mountain GIS Summit",
                         "Replacement laptop charger, old one failed in the field",
                         "Hotel, 2 nights, state auditors' training in Santa Fe",
                         "Printer toner and paper for the front office"],
                        ["business", "work", "expense", "stuff for work", "misc"]),
    "grant_summary": (["We will expand our free after-school tutoring program from two schools to five, serving about 300 students in grades 3-8 with trained volunteer tutors.",
                       "The project installs 40 low-cost air quality sensors in neighborhoods near the rail yard and publishes readings on an open dashboard.",
                       "Funding will support a mobile food pantry van that visits six rural towns twice a month.",
                       "A two-year pilot training 25 community health workers to do home visits for new parents."],
                      ["helping people", "a program", "community stuff", "education", "we need money"]),
    "feedback": (["The check-in line was long but the staff were friendly and helpful.",
                  "Website was easy to use, though the payment page timed out once.",
                  "Loved the workshop, would like more hands-on time next session",
                  "Parking was confusing, add signs to the east lot",
                  "honestly great experience, fast turnaround on my permit",
                  "Too many steps to upload documents; please allow PDFs over 10MB"],
                 ["good", "fine", "ok", "bad", "meh", "it was"]),
    "symptoms": (["Sore throat and fever of 101 for three days, mild cough",
                  "Lower back pain after lifting boxes last Tuesday, worse in the morning",
                  "Recurring headaches behind the eyes, about 3x a week for a month",
                  "rash on both forearms, itchy, started after a camping trip",
                  "Follow-up for blood pressure, no new symptoms"],
                 ["sick", "pain", "not feeling well", "hurts", "stuff"]),
    "accommodation": (["Extended time (1.5x) on exams and a reduced-distraction testing room",
                       "Note-taking assistance and permission to record lectures due to a documented hearing impairment",
                       "Ground-floor classroom access or elevator access for a temporary mobility injury (broken ankle) through October",
                       "Flexible attendance for flare-ups of a chronic condition, documented by my provider",
                       "Housing: a single room for a medical need, documentation from my physician attached",
                       "Screen reader compatible course materials and captioned videos"],
                      ["accommodations", "help with classes", "extra stuff", "need support", "the usual"]),
    "personal_statement": (["Growing up translating for my parents at clinics made me want to study nursing, and volunteering at a free clinic confirmed it.",
                            "I started coding by fixing my family's old computer; now I want to study computer science and build tools for small farms like ours.",
                            "After four years in the Army as a medic, I want to finish my biology degree and apply to PA school.",
                            "My favorite class was chemistry because our teacher let us design our own experiments, which taught me to ask better questions."],
                           ["I want to go to college", "I am a good student", "please accept me", "college is important"]),
    "grade_appeal": (["My final exam score was recorded as 62 but the graded exam returned to me shows 82; the gradebook was not updated.",
                      "The syllabus says late work loses 10% per day, but my project submitted one day late received a zero.",
                      "I had an approved accommodation for extended time that was not applied on the midterm, which I believe affected my grade.",
                      "Two of my lab reports are missing from the gradebook even though the LMS shows they were submitted on time."],
                     ["unfair grade", "I deserve an A", "wrong grade", "the professor is wrong", "grade"]),
    "withdrawal_reason": (["I was hospitalized for three weeks in October and could not complete the course; documentation attached.",
                           "My work schedule changed to overnight shifts after the drop deadline and I can no longer attend the 8am lab.",
                           "Death in the family required me to travel abroad for most of November.",
                           "I was registered for the wrong section due to an advising error and only found out after the add deadline."],
                          ["personal reasons", "stuff happened", "can't do it", "family", "medical"]),
    "residency": (["I moved to Colorado in June 2024 for a full-time job, have a CO driver's license and voter registration since July 2024, and filed CO taxes for 2025.",
                   "My parents have lived in Albuquerque since 2010; I attended high school in NM and am claimed as their dependent.",
                   "I'm active-duty military stationed at a base in-state, orders attached.",
                   "Lived in Utah for 14 months, lease and utility bills attached, working full time."],
                  ["I live here", "in-state", "resident", "moved here", "yes I qualify"]),
    "sap_appeal": (["My GPA dropped below 2.0 last spring because I was working 35 hours a week to support my family after my mother lost her job. I've reduced my hours to 15 and have a study plan with my advisor.",
                    "I failed two courses in Fall 2025 while caring for my newborn. I now have childcare and completed 12 credits this summer with a 3.2.",
                    "I exceeded the maximum timeframe because I changed majors from engineering to nursing; my academic plan shows I will finish in 3 semesters."],
                   ["please give me aid", "bad semester", "I'll do better", "I need the money", "hard time"]),
    "transfer_course": (["ENGL 1010 Composition I, 3 credits, grade A, taken Fall 2025 at Pikes Peak State College",
                         "Intro to Statistics (STAT 2000), 4 semester hours, B+, syllabus attached",
                         "General Chemistry I with lab, 5 credits, completed Spring 2025 at Arapahoe Valley College"],
                        ["some classes", "english", "credits", "my old classes"]),
    "transcript_delivery": (["Electronic PDF to admissions@example.edu, University of Northern Plains graduate admissions",
                             "Mail two sealed copies to my home address on file",
                             "Send to the State Board of Nursing, 1560 Broadway, Denver CO, attention licensure",
                             "Hold for pickup at the registrar's office, I'll come by Friday"],
                            ["send it", "to school", "mail", "wherever"]),
    "housing_notes": (["Would prefer a quiet floor, I'm an early riser; roommate request: Aisha Okafor (student ID on her form)",
                       "Need a room near an accessible entrance, I use a wheelchair",
                       "Interested in the Outdoor Recreation living-learning community",
                       "No preference, just not a triple if possible"],
                      ["room", "housing", "dorm", "nice room"]),
    "job_experience": (["3 years as a line cook at Meadowlark Catering Co., ran the grill station and trained new hires",
                        "Payroll specialist 2019-2024 at Oakline Freight: biweekly payroll for 400 employees in ADP",
                        "Volunteer tutor, Northside Food Bank homework club, 2 years, grades 3-5 math",
                        "Journeyman electrician, 8 years residential and light commercial, state license current"],
                       ["work", "jobs", "experience", "I worked", "lots"]),
    "event_notes": (["Bringing my 8-year-old, is there a kids' activity?", "Will need an ASL interpreter for the keynote",
                     "Arriving late Friday, first session I can make is Saturday 9am", "none", "Vegetarian lunch please"],
                    None),
}
TEXT_NONE_OK = {"comments", "event_notes"}
OPEN_FIELDS = {"comments", "event_notes"}
for k, (passes, inc) in TEXT.items():
    ft(k, "text", L([p for p in passes if p]), ["phone", "email", "date", "full_name", "amount"],
       inc=L(inc) if inc else None, none_ok=k in TEXT_NONE_OK)
DATE_TYPES = {"date_of_birth", "event_date", "start_date"}
# donor type name aliases used in confusers
ALIAS = {"date": "event_date"}

# hard negatives: realistic pass entries that look like failures
HARD_PASS = {
    "support_issue": ["I need a password reset for my student portal account, the reset link says expired",
                      "my card was declined at checkout even though the balance is fine",
                      "Lost my Social Security card and need to update my employee file, what documents do you accept?"],
    "issue_311": ["The damn streetlight on Oak Ave has been out for two weeks and it's dark as hell at night"],
    "reason": ["I forgot my password and the self-service reset isn't working, need access for the financial aid form"],
    "comments": ["Please don't call my work number, text is best", "My card was declined online so I'll pay in person"],
}

# --------------------------------------------------------------------------------------------------
# forms: (form description, [(type, label, description, optional)])
F = {}


def form(key, desc, fields, he=False):
    F[key] = {"desc": desc, "fields": fields, "he": he}


form("311", "City 311 service request (report a non-emergency problem)", [
    ("full_name", "Full name", "Your first and last name", False),
    ("phone", "Phone", "Best number to reach you", False),
    ("email", "Email", "We'll send status updates here", False),
    ("street_address", "Location / address", "Street address or nearest intersection of the problem", False),
    ("issue_311", "Description", "Describe the problem and where exactly it is", False),
    ("comments", "Additional comments", "Optional; anything else we should know", True)])
form("permit", "Residential building permit application", [
    ("full_name", "Applicant name", "Property owner or contractor name", False),
    ("org_name", "Contractor company", "Licensed contractor business name", False),
    ("street_address", "Project address", "Street address where the work will be done", False),
    ("permit_parcel", "Parcel number", "County parcel / schedule number", False),
    ("permit_work", "Scope of work", "Describe the work to be permitted", False),
    ("amount", "Estimated project valuation", "Total cost of the work in dollars, e.g. 12500", False),
    ("phone", "Daytime phone", "Contact number during business hours", False)])
form("foia", "Public records (open records / FOIA) request", [
    ("full_name", "Requester name", "Name of the person making the request", False),
    ("email", "Email", "Where we should send the records", False),
    ("records_request", "Records requested", "Describe the records as specifically as possible, with dates", False),
    ("reason", "Purpose of request", "Optional; why you are requesting the records", True),
    ("yes_no", "Fee waiver requested?", "Answer yes or no", False)])
form("benefits", "Public benefits intake (SNAP / Medicaid screening)", [
    ("full_name", "Applicant full name", "Legal first and last name", False),
    ("date_of_birth", "Date of birth", "MM/DD/YYYY", False),
    ("street_address", "Home address", "Where you live now", False),
    ("apt_unit", "Apartment / unit", "Optional; leave N/A if none", True),
    ("city", "City", "City of residence", False),
    ("zip", "ZIP code", "5-digit ZIP", False),
    ("quantity", "Household size", "Number of people in your household, in digits", False),
    ("amount", "Monthly household income", "Total monthly income before taxes, in dollars", False)])
form("jobapp", "Job application", [
    ("full_name", "Full name", "Legal name", False),
    ("email", "Email", "Contact email", False),
    ("job_title", "Position applying for", "Title of the job you're applying to", False),
    ("job_experience", "Relevant experience", "Summarize your most relevant work experience", False),
    ("start_date", "Available start date", "Earliest date you could start", False),
    ("years_experience", "Years of experience", "Total years in this field", False),
    ("how_heard", "How did you hear about us?", "Where you saw the posting", False)])
form("contact", "Contact us form", [
    ("first_name", "First name", "", False), ("last_name", "Last name", "", False),
    ("email", "Email", "We'll reply here", False),
    ("support_issue", "Message", "How can we help?", False)])
form("support", "Customer support ticket", [
    ("full_name", "Name", "Your name", False), ("email", "Account email", "Email on your account", False),
    ("case_number", "Order or ticket number", "If you have one", False),
    ("support_issue", "Describe the issue", "What happened, and what did you expect?", False),
    ("comments", "Anything else?", "Optional", True)])
form("event", "Event registration", [
    ("full_name", "Attendee name", "Name for your badge", False), ("email", "Email", "", False),
    ("org_name", "Organization", "Company or organization", False), ("job_title", "Job title", "", False),
    ("quantity", "Number of guests", "Including yourself, in digits", False),
    ("dietary", "Dietary restrictions", "Optional; write none if none", True),
    ("event_notes", "Notes for the organizers", "Optional", True)])
form("patient", "Patient intake form (new patient, synthetic)", [
    ("full_name", "Patient name", "Legal name", False), ("date_of_birth", "Date of birth", "", False),
    ("phone", "Phone", "Mobile preferred", False),
    ("insurance_member_id", "Insurance member ID", "From your insurance card", False),
    ("medications", "Current medications", "List medications and doses, or write none", False),
    ("symptoms", "Reason for visit", "Describe your symptoms or the reason for today's visit", False),
    ("full_name", "Emergency contact name", "Someone we can call in an emergency", False),
    ("relationship", "Relationship to patient", "How the emergency contact is related to you", False)])
form("vendor", "Vendor onboarding form", [
    ("org_name", "Legal business name", "As registered with the state", False),
    ("full_name", "Primary contact", "Name of your account contact", False),
    ("email", "Remittance email", "Where payment notices go", False),
    ("website", "Company website", "", False),
    ("street_address", "Remit-to address", "Mailing address for payments", False),
    ("phone", "Business phone", "", False)])
form("expense", "Employee expense report", [
    ("full_name", "Employee name", "", False), ("event_date", "Date of expense", "Date on the receipt", False),
    ("invoice_number", "Receipt / invoice number", "Number printed on the receipt", False),
    ("amount", "Amount", "Amount in dollars, e.g. 48.20", False),
    ("expense_purpose", "Business purpose", "Why this expense was necessary for work", False)])
form("grant", "Community grant application", [
    ("org_name", "Applicant organization", "Legal name of the nonprofit", False),
    ("full_name", "Project director", "Name of the person leading the project", False),
    ("grant_summary", "Project summary", "In 2-4 sentences, what will the grant fund?", False),
    ("amount", "Amount requested", "Dollar amount requested", False),
    ("website", "Organization website", "Optional", True)])
form("survey", "Customer feedback survey", [
    ("feedback", "What could we improve?", "Tell us about your visit", False),
    ("how_heard", "How did you find us?", "", False),
    ("email", "Email (optional)", "Only if you want a reply", True)])
form("signup", "Account signup", [
    ("first_name", "First name", "", False), ("last_name", "Last name", "", False),
    ("email", "Email address", "Used to sign in", False), ("phone", "Mobile number", "For text alerts", False),
    ("country", "Country", "Country of residence", False)])
form("incident", "Workplace / campus incident report", [
    ("full_name", "Reported by", "Your name", False), ("event_date", "Date of incident", "", False),
    ("appt_time", "Time of incident", "Approximate time", False),
    ("street_address", "Location", "Building and room, or street address", False),
    ("incident", "What happened?", "Describe the incident, injuries, and damage", False)])
form("k12", "K-12 school enrollment", [
    ("full_name", "Student name", "Student's legal name", False), ("date_of_birth", "Student date of birth", "", False),
    ("school_name", "Previous school", "Most recent school attended", False),
    ("full_name", "Parent / guardian name", "", False), ("phone", "Guardian phone", "", False),
    ("relationship", "Relationship to student", "", False), ("street_address", "Home address", "", False)])
form("clinic_appt", "Clinic appointment request", [
    ("full_name", "Patient name", "", False), ("event_date", "Preferred date", "", False),
    ("appt_time", "Preferred time", "Morning or a specific time", False), ("symptoms", "Reason for visit", "", False)])
# higher education
form("he_admit", "Undergraduate admissions application", [
    ("full_name", "Legal name", "First, middle, last", False), ("date_of_birth", "Date of birth", "", False),
    ("email", "Email", "We'll send your decision here", False),
    ("school_name", "High school", "School you graduated from or attend now", False),
    ("gpa", "Cumulative GPA", "Unweighted, on a 4.0 scale", False), ("major", "Intended major", "", False),
    ("term", "Entry term", "Term you plan to start", False),
    ("personal_statement", "Personal statement (short)", "Tell us about something that shaped your goals", False)], he=True)
form("he_transfer", "Transfer credit evaluation request", [
    ("full_name", "Student name", "", False), ("student_id", "Student ID", "Your university ID number", False),
    ("school_name", "Previous institution", "Where you took the course", False),
    ("transfer_course", "Course to evaluate", "Course number, title, credits and grade", False),
    ("course_code", "Requested equivalent", "Our course you think it matches", False)], he=True)
form("he_transcript", "Official transcript request", [
    ("full_name", "Name while enrolled", "Name on your records", False), ("student_id", "Student ID", "", False),
    ("date_of_birth", "Date of birth", "For identity verification", False),
    ("quantity", "Number of copies", "Digits only", False),
    ("transcript_delivery", "Delivery instructions", "Where and how to send the transcript", False),
    ("reason", "Reason (optional)", "", True)], he=True)
form("he_adddrop", "Late add/drop or late-withdrawal petition", [
    ("full_name", "Student name", "", False), ("student_id", "Student ID", "", False),
    ("course_code", "Course", "Course number and section", False), ("term", "Term", "", False),
    ("withdrawal_reason", "Reason for petition", "Explain the circumstances and attach documentation", False)], he=True)
form("he_gradeappeal", "Grade appeal", [
    ("full_name", "Student name", "", False), ("student_id", "Student ID", "", False),
    ("course_code", "Course", "", False), ("full_name", "Instructor name", "Instructor of record", False),
    ("grade_appeal", "Basis for appeal", "Explain the specific error or policy issue", False)], he=True)
form("he_residency", "In-state tuition residency application", [
    ("full_name", "Student name", "", False), ("student_id", "Student ID", "", False),
    ("event_date", "Date you moved to the state", "", False), ("state", "State of residence claimed", "", False),
    ("residency", "Residency explanation", "Describe how you established domicile (job, lease, license, taxes)", False)], he=True)
form("he_housing", "Student housing application", [
    ("full_name", "Student name", "", False), ("student_id", "Student ID", "", False),
    ("term", "Term", "Housing term", False), ("dietary", "Meal plan dietary needs", "Optional", True),
    ("housing_notes", "Roommate and room preferences", "", False),
    ("full_name", "Emergency contact", "", False), ("phone", "Emergency contact phone", "", False)], he=True)
form("he_sap", "Financial aid verification / SAP appeal", [
    ("full_name", "Student name", "", False), ("student_id", "Student ID", "", False),
    ("amount", "2025 household income", "From your tax return, in dollars", False),
    ("quantity", "Household size", "Digits", False),
    ("sap_appeal", "SAP appeal statement", "Explain why you did not meet satisfactory academic progress and your plan", False)], he=True)
form("he_access", "Accessibility accommodation request", [
    ("full_name", "Student name", "", False), ("student_id", "Student ID", "", False),
    ("email", "Campus email", "", False),
    ("accommodation", "Accommodations requested", "What accommodations are you requesting and why?", False),
    ("term", "Term needed", "", False), ("hours_per_week", "Credit or work hours per week", "Optional", True)], he=True)
form("he_studentjob", "Student employment application", [
    ("full_name", "Name", "", False), ("student_id", "Student ID", "", False),
    ("major", "Major", "", False), ("hours_per_week", "Hours available per week", "", False),
    ("job_experience", "Relevant experience", "", False), ("appt_time", "Best time to interview", "", False)], he=True)

HELDOUT_FORMS = {"vendor", "grant", "k12", "he_gradeappeal", "he_residency", "he_access"}
HELDOUT_TYPES = {"website", "appt_time", "insurance_member_id", "hours_per_week", "residency", "grade_appeal",
                 "housing_notes"}

CATS = list(packs.FIELD_CATEGORIES)
CAT_W = {"pass": 0.33, "empty_or_placeholder": 0.075, "gibberish": 0.065, "wrong_type": 0.105,
         "wrong_format": 0.085, "incomplete": 0.09, "off_topic": 0.10, "sensitive_data": 0.075, "abusive": 0.075}
FAMILY_CODE = {"pass": "pass", "empty_or_placeholder": "placeholder", "gibberish": "gibberish",
               "wrong_type": "wrongtype", "wrong_format": "wrongformat", "incomplete": "incomplete",
               "off_topic": "unrelated", "sensitive_data": "sensitive", "abusive": "abusive"}
# never put "topic" in a family name except hard negatives: finetune/evaluate.py reports families whose
# name contains "topic" (and whose gold is negative) as hard_negative_fp_rate.


def field_text(label, desc, optional):
    if optional and "optional" not in desc.lower() and "optional" not in label.lower():
        desc = (desc + "; optional" if desc else "Optional")
    return f"{label}: {desc}" if desc else label


def vals(x, rng):
    return x(rng) if callable(x) else P(rng, x)


def applicable(ftype, optional):
    t = T[ftype]
    cats = ["pass", "empty_or_placeholder", "gibberish", "wrong_type", "off_topic", "abusive"]
    if t["fmt"]:
        cats.append("wrong_format")
    if t["inc"]:
        cats.append("incomplete")
    if t["sens"]:
        cats.append("sensitive_data")
    if ftype in OPEN_FIELDS:            # "anything else?" fields: any real remark answers them
        cats = [c for c in cats if c not in ("off_topic", "wrong_type")]
    return cats


def make_entry(rng, ftype, cat, optional, side):
    """-> (entry, needs_review, quality, family_suffix) or None."""
    t = T[ftype]
    if cat == "pass":
        r = rng.random()
        if ftype in HARD_PASS and r < 0.25:
            return P(rng, HARD_PASS[ftype]), False, 3, "topic_hardneg_lookalike"
        if optional and r < 0.18:
            return P(rng, ["N/A", "n/a", "none", "None", "-", "no"]), False, 2, "topic_hardneg_optional_na"
        e = vals(t["pass"], rng)
        if not e.strip():
            return None
        if t["none_ok"] and e.lower().startswith(("n/a", "none", "no ", "no")) and len(e) < 16:
            return e, False, 2, "topic_hardneg_none_is_answer"
        q = 3 if (t["kind"] == "text" and len(e) > 30) or t["kind"] == "struct" else 2
        if ftype in ("full_name", "first_name", "last_name", "city", "org_name", "school_name") and e.islower():
            q = 2
        return e, False, q, "pass"
    if cat == "empty_or_placeholder":
        pool = PLACEHOLDER_NOT_NONE if (t["none_ok"] or optional) else PLACEHOLDER
        if t["none_ok"] or optional:    # a bare dash in an optional box is a normal "nothing to add"
            pool = [p for p in pool if p not in ("-", "--", ".", "...", "x", "?", "no")]
        if ftype in ("quantity", "hours_per_week", "years_experience", "amount", "student_id", "case_number",
                     "invoice_number", "zip", "insurance_member_id", "permit_parcel"):
            pool = [p for p in pool if p not in ("0000",)]
        if ftype == "yes_no":
            pool = [p for p in pool if p.lower() not in ("no",)]
        return P(rng, pool), False, 0, "placeholder"
    if cat == "gibberish":
        digits_ok = ftype not in ("student_id", "case_number", "invoice_number", "insurance_member_id",
                                  "permit_parcel")
        return mash(rng, digits_ok), False, 0, "gibberish"
    if cat == "wrong_type":
        donor = P(rng, t["confusers"])
        donor = ALIAS.get(donor, donor)
        if donor == ftype:
            return None
        e = vals(T[donor]["pass"], rng)
        if donor in ("street_address",) and ftype in ("full_name",):
            e = street(rng)
        return e, False, 0, f"wrongtype_{donor}"
    if cat == "wrong_format":
        return vals(t["fmt"], rng), False, 1, "wrongformat"
    if cat == "incomplete":
        r = rng.random()
        if t["kind"] == "text" and r < 0.1:
            return P(rng, ["see attached", "see attachment", "attached", "details in the email I sent"]), True, 1, "incomplete_attach"
        if t["kind"] == "text" and r < 0.35:
            return P(rng, INCOMPLETE_GENERIC), False, 1, "incomplete_generic"
        return vals(t["inc"], rng), False, 1, "incomplete"
    if cat == "off_topic":
        # a coherent answer to a DIFFERENT question: either a generic question/remark or another text
        # field's real answer
        donors = [k for k, v in T.items() if v["kind"] == "text" and k != ftype and not v["none_ok"]
                  and (side == "test" or k not in HELDOUT_TYPES) and k not in ("medications",)]
        if rng.random() < (0.8 if t["kind"] == "struct" else 0.45):
            return P(rng, OFFTOPIC_GENERIC), False, 0, "unrelated_generic"
        d = P(rng, donors)
        return vals(T[d]["pass"], rng), False, 0, "unrelated_otherfield"
    if cat == "sensitive_data":
        base = vals(t["pass"], rng) if rng.random() < 0.5 else ""
        return sensitive_in_context(rng, base).strip(), True, 0, "sensitive"
    if cat == "abusive":
        if rng.random() < 0.28:
            return P(rng, THREATS), True, 0, "abusive_threat"
        return P(rng, ABUSIVE), False, 0, "abusive"
    raise ValueError(cat)


def build(seed=SEED):
    rng = random.Random(seed)
    pack = packs.get_pack(PACK)
    qs = pack["questions"]
    slots = []   # (form, field index)
    for fk, f in F.items():
        for i, _ in enumerate(f["fields"]):
            slots.append((fk, i))
    side_of = {}
    for fk, i in slots:
        ftype = F[fk]["fields"][i][0]
        side_of[(fk, i)] = "test" if (fk in HELDOUT_FORMS or ftype in HELDOUT_TYPES) else "trainside"
    by_side = {s: [x for x in slots if side_of[x] == s] for s in ("trainside", "test")}
    weights = {s: [1.6 if F[fk]["he"] else 1.0 for fk, _ in by_side[s]] for s in by_side}
    out = {"trainside": [], "test": []}
    seen = set()
    for side, target in TARGET.items():
        tries = 0
        while len(out[side]) < target and tries < target * 60:
            tries += 1
            # pick the category first (so the label balance is exact), then a field it can occur in
            cat = rng.choices(CATS, weights=[CAT_W[c] for c in CATS])[0]
            cand = [(x, w) for x, w in zip(by_side[side], weights[side])
                    if cat in applicable(F[x[0]]["fields"][x[1]][0], F[x[0]]["fields"][x[1]][3])]
            fk, i = rng.choices([x for x, _ in cand], weights=[w for _, w in cand])[0]
            ftype, label, desc, optional = F[fk]["fields"][i]
            r = make_entry(rng, ftype, cat, optional, side)
            if r is None:
                continue
            entry, review, quality, fam = r
            if not entry.strip():
                continue
            ftext = field_text(label, desc, optional)
            key = (fk, ftext, entry)
            if key in seen:
                continue
            seen.add(key)
            state = packs.build_state(pack, form=F[fk]["desc"], field=ftext, entry=entry)
            out[side].append({"family": f"ffv/{fam}/{fk}", "state": state, "questions": qs,
                              "gold": {"category": cat, "needs_review": review, "quality": quality},
                              "_ftype": ftype})
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
        c = Counter(r["gold"]["category"] for r in rows)
        rep[s] = {"rows": len(rows), "categories": dict(sorted(c.items())),
                  "pass_share": round(c["pass"] / max(1, len(rows)), 3),
                  "needs_review_true": sum(r["gold"]["needs_review"] for r in rows),
                  "quality": dict(sorted(Counter(r["gold"]["quality"] for r in rows).items())),
                  "forms": len({r["family"].rsplit("/", 1)[1] for r in rows}),
                  "field_types": len({r["_ftype"] for r in rows}),
                  "he_rows": sum(F[r["family"].rsplit("/", 1)[1]]["he"] for r in rows)}
    return rep


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stats", action="store_true")
    ap.add_argument("--out", default=HERE)
    a = ap.parse_args()
    splits = build()
    print(json.dumps(stats(splits), indent=1))
    train_types = {r["_ftype"] for r in splits["train"]}
    train_forms = {r["family"].rsplit("/", 1)[1] for r in splits["train"]}
    assert not (train_types & HELDOUT_TYPES) and not (train_forms & HELDOUT_FORMS)
    if a.stats:
        return
    for s, rows in splits.items():
        with open(os.path.join(a.out, f"{s}.jsonl"), "w") as f:
            for r in rows:
                r = {k: r[k] for k in ("id", "family", "state", "questions", "gold")}
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"field types: {len(T)}  forms: {len(F)}  wrote {', '.join(f'{s}={len(r)}' for s, r in splits.items())}")


if __name__ == "__main__":
    main()
