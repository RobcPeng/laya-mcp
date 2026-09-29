"""Generate the sales-lead-qualification accelerator set (deterministic, stdlib only).

Six invented products, each with a description (the `product` field) and a bank of pains it solves.
A lead is composed from independent BANT sentences (budget, authority via title or statement, need,
timing) plus a stage sentence, written in one of seven styles (web form, email, SDR call notes, event
badge scan, website chat, partner referral, social DM). `need` is false when the lead's pain belongs
to a different product (a data-platform pain sent to a payroll vendor) or no pain is stated. Not-a-fit
families (student, vendor pitch, job seeker, wrong product) come separately. TEST holds out one style
per stage and one not-a-fit type.

    python datasets/accelerators/sales-lead-qualification/generate.py
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import _common as C  # noqa: E402

NAME = "sales-lead-qualification"
PREFIX = "lead"
SEED = 818
PER_FAMILY = 30
PER_NOFIT = 45

PRODUCTS = {
    "lakepoint": ("Lakepoint: a managed data platform for ingesting, storing, and analyzing large datasets "
                  "with SQL, dashboards, and machine learning.", [
        "Our reporting runs off spreadsheets and a nightly export that breaks every week.",
        "We have data in five systems and nobody can join it together for analysis.",
        "Our on-prem data warehouse can't keep up; queries take hours.",
        "We want to start doing forecasting with ML but our data is scattered.",
    ]),
    "fieldhand": ("FieldHand: a mobile field-service app for scheduling technicians, dispatching jobs, "
                  "tracking work orders, and invoicing on site.", [
        "Our dispatchers schedule 40 HVAC techs on a whiteboard and jobs get double booked.",
        "Techs fill out paper work orders and invoices go out two weeks late.",
        "We can't see where our crews are or which jobs are done until the end of the day.",
        "Customers complain that nobody tells them when the technician is coming.",
    ]),
    "payloom": ("PayLoom: payroll and benefits software for companies with 20 to 2,000 employees, "
                "including tax filing and time tracking.", [
        "We run payroll in spreadsheets and got a penalty for a late tax filing.",
        "HR spends three days every pay period fixing timesheet errors.",
        "We're growing into three new states and our payroll provider can't handle multi-state taxes.",
        "Benefits enrollment is done on paper forms and people get missed.",
    ]),
    "civicdesk": ("CivicDesk: a resident request portal and case management system for local governments.", [
        "Resident requests come in by phone, email, and paper and we lose track of them.",
        "Our council wants reports on how fast we close service requests and we can't produce them.",
        "Each department tracks cases in its own spreadsheet.",
        "Residents have no way to check the status of what they reported.",
    ]),
    "shieldworks": ("ShieldWorks: endpoint security and managed threat detection for mid-size IT teams.", [
        "We had a ransomware scare and our antivirus didn't catch it.",
        "Our two-person IT team can't watch security alerts at night.",
        "Our cyber insurance renewal requires endpoint detection and response.",
        "We have no idea which laptops are unpatched.",
    ]),
    "skilltrail": ("SkillTrail: a learning management system for employee training and compliance courses.", [
        "We track mandatory safety training in a binder and failed an audit.",
        "Onboarding new hires takes weeks because training is all in-person.",
        "We can't prove who completed harassment prevention training.",
        "Our training videos are spread over shared drives and nobody finishes them.",
    ]),
}

COMPANIES = ["Example Logistics", "Placeholder Health Partners", "City of Anytown", "Sample Manufacturing Co.",
             "Demo Mechanical Services", "Pine County", "Fixture Foods", "Mockford Credit Union",
             "Lorem Property Group", "Testwell Engineering", "Nullman Retail", "Specimen Labs",
             "Stubbs Plumbing & Heating", "Ipsum School District", "Templeton Hotels"]
SIZES = ["45 employees", "120 employees", "300 staff", "800 people", "1,500 employees", "60 staff", "about 200 of us"]

AUTH_TITLES = ["VP of Operations", "Director of IT", "Owner", "CFO", "Head of Data", "COO", "IT Manager",
               "HR Director", "Chief Information Officer", "Operations Director", "Deputy City Manager",
               "Controller"]
NONAUTH_TITLES = ["Marketing Intern", "Junior Analyst", "Research Assistant", "Administrative Assistant (just collecting info)",
                  "Consultant (no purchasing role)", "Staff Accountant", "Help Desk Technician"]
AUTH_STMT = ["I'll be making the final call on this.", "I own the budget for this area.",
             "I lead the selection committee.", "I pick our tools and sign the contracts.",
             "It's my decision, with the CEO's okay."]
NONAUTH_STMT = ["I don't have any say in purchasing, just gathering info.",
                "My manager makes the decision; I'm just asked to look around.",
                "I'm not involved in buying, just curious.",
                "Honestly not my call."]

BUDGET_T = ["We have about ${k}k approved for this.", "Budget is already in this year's plan.",
            "A grant covers software like this.", "Finance signed off on up to ${k}k.",
            "We set aside money for this in the current budget.", "Funding is approved."]
BUDGET_F = ["There's no budget for this yet.", "We'd have to find money next fiscal year.",
            "We can't spend anything right now.", "No money set aside, just exploring.", "", "", ""]
TIME_T = ["We want this live within 90 days.", "We need to decide this quarter.",
          "Our current contract ends in four months.", "Target go-live is about five months out.",
          "We need something in place in the next few weeks.", "Hoping to roll out by next month."]
TIME_F = ["Maybe next year or the year after.", "No timeline yet.", "We just renewed our current vendor for three years.",
          "Probably at least nine months before we'd start.", "Nothing planned for the next year.", "", "", ""]

STAGE = {
    "research": ["Just starting to learn what's out there.", "Reading up for background, no active project yet.",
                 "Downloaded your guide; trying to understand the space.", "Early days - mostly curious how others handle this."],
    "evaluating": ["Could we set up a demo next week?", "We're comparing you with two other vendors.",
                   "Can we get a trial account for the team?", "Please send pricing tiers so we can compare.",
                   "We're shortlisting options and would like a technical deep dive."],
    "ready_to_buy": ["Please send a formal quote and your standard contract.",
                     "Procurement needs your W-9 and security questionnaire to issue a PO.",
                     "We've picked you; what do we need to sign?",
                     "Send the order form, we want to get this signed."],
}

STYLES = ["web_form", "email", "call_notes", "event_scan", "chat", "partner", "social_dm"]
TEST_FAMILIES = ["research/social_dm", "evaluating/call_notes", "ready_to_buy/partner", "not_a_fit/vendor"]


def compose(rng, style, name, title, company, sentences):
    body = " ".join(s for s in sentences if s)
    if style == "web_form":
        return (f"Name: {name}\nCompany: {company} ({C.pick(rng, SIZES)})\nTitle: {title}\n"
                f"Email: {C.email(rng, name)}\nMessage: {body}")
    if style == "email":
        return (f"{C.pick(rng, ['Hi team,', 'Hello,', 'Hi there -', 'Good afternoon,'])}\n\n{body}\n\n"
                f"{name}\n{title}, {company}")
    if style == "call_notes":
        return (f"SDR call notes: spoke with {name} ({title}) at {company}, {C.pick(rng, SIZES)}. "
                f"In their words: \"{body}\"")
    if style == "event_scan":
        ev = C.pick(rng, ["State Gov IT Summit", "Midwest Ops Expo", "HR Tech Day", "Data Innovators Meetup",
                          "Regional Security Forum"])
        return f"Badge scan - {ev}. {name}, {title}, {company}. Booth notes: {body}"
    if style == "chat":
        lines = [s for s in sentences if s]
        return "\n".join(f"visitor: {s}" for s in lines) + f"\nvisitor: I'm {name}, {title} at {company}"
    if style == "partner":
        return (f"Forwarding a lead from our reseller partner.\n> Contact: {name}, {title}, {company}\n> {body}\n"
                f"Partner rep: {C.person(rng)}")
    return f"hey! {name} here, {title} at {company}. {body}"


def build(rng):
    out = []
    names = list(PRODUCTS)
    for stage in ("research", "evaluating", "ready_to_buy"):
        for style in STYLES:
            for i in range(PER_FAMILY):
                pk = names[(i + rng.randrange(6)) % 6]
                desc, pains = PRODUCTS[pk]
                need = rng.random() < (0.85 if stage == "ready_to_buy" else 0.68)
                if need:
                    pain = C.pick(rng, pains)
                else:
                    other = C.pick(rng, [n for n in names if n != pk])
                    pain = C.pick(rng, PRODUCTS[other][1]) if rng.random() < 0.75 else ""
                if stage == "ready_to_buy":
                    budget, timing = rng.random() < 0.85, True      # asking to sign implies near-term
                elif stage == "research":
                    budget, timing = rng.random() < 0.15, False     # no active project -> no timeline
                else:
                    budget, timing = rng.random() < 0.5, rng.random() < 0.5
                auth = rng.random() < 0.55
                title = C.pick(rng, AUTH_TITLES if auth else NONAUTH_TITLES)
                auth_stmt = C.pick(rng, AUTH_STMT if auth else NONAUTH_STMT) if rng.random() < 0.4 else ""
                k = rng.randrange(20, 400)
                sents = [pain,
                         C.pick(rng, BUDGET_T if budget else BUDGET_F).replace("{k}", str(k)),
                         C.pick(rng, TIME_T if timing else TIME_F),
                         auth_stmt, C.pick(rng, STAGE[stage])]
                first, rest = sents[0], sents[1:]
                rng.shuffle(rest)
                sents = [first] + rest if rng.random() < 0.7 else rest + [first]
                name = C.person(rng)
                text = compose(rng, style, name, title, C.pick(rng, COMPANIES), sents)
                text = C.messy(rng, text, typo_rate=0.03, p_typo=0.35)
                cnt = int(budget) + int(auth) + int(timing)
                fit = 1 if not need else (3 if cnt == 3 else 2 if cnt >= 1 else 1)
                out.append({"family": f"{stage}/{style}", "group": stage,
                            "state": {"product": desc, "lead": text},
                            "gold": {"budget": budget, "authority": auth, "need": need, "timing": timing,
                                     "stage": stage, "fit": fit}})
    # not-a-fit families: all BANT false except where noted
    nofit = {
        "student": ["I'm a {school} student writing a paper on {topic}. Could someone answer a few questions for my class project?",
                    "hi, doing a capstone project about {topic}, is there a free student version I can play with?"],
        "vendor": ["We help companies like yours with SEO and paid ads. Would love 15 minutes to show you what we did for similar vendors.",
                   "Our offshore dev team can extend your engineering capacity at half the cost. Open to a partnership call?"],
        "jobseeker": ["I'm interested in open roles on your customer success team. Attached is my resume.",
                      "Are you hiring solutions engineers? I have five years of experience and would love to chat."],
        "wrong_product": ["Do you sell {thing}? We need {thing} for our new office.",
                          "Looking for a vendor to handle {thing}. Is that something you do?"],
    }
    things = ["printers and copiers", "office furniture", "a phone system", "janitorial services", "catering",
              "company swag", "a website redesign", "commercial insurance"]
    topics = {"lakepoint": "data platforms", "fieldhand": "field service apps", "payloom": "payroll software",
              "civicdesk": "government technology", "shieldworks": "cybersecurity", "skilltrail": "e-learning"}
    for sub, tpls in nofit.items():
        for i in range(PER_NOFIT):
            pk = names[rng.randrange(6)]
            desc = PRODUCTS[pk][0]
            msg = tpls[i % len(tpls)].format(school=C.pick(rng, ["university", "community college", "high school", "MBA"]),
                                             topic=topics[pk], thing=C.pick(rng, things))
            if sub == "wrong_product" and rng.random() < 0.5:
                msg += " " + C.pick(rng, ["Budget is approved.", "We need it within 60 days."])
            budget = "Budget is approved." in msg
            timing = "within 60 days" in msg
            title = {"student": "Student", "vendor": C.pick(rng, ["Business Development Rep", "Partnerships Manager"]),
                     "jobseeker": "Candidate", "wrong_product": C.pick(rng, ["Office Manager", "Facilities Coordinator"])}[sub]
            # wrong_product buyers may have buying power, but not for this product; authority is
            # judged on the person, so an office manager who buys office supplies counts as involved
            auth = sub == "wrong_product"
            style = C.pick(rng, STYLES)
            text = compose(rng, style, C.person(rng), title, C.pick(rng, COMPANIES), [msg])
            text = C.messy(rng, text, 0.03, 0.35)
            out.append({"family": f"not_a_fit/{sub}", "group": "not_a_fit",
                        "state": {"product": desc, "lead": text},
                        "gold": {"budget": budget, "authority": auth, "need": False, "timing": timing,
                                 "stage": "not_a_fit", "fit": 0}})
    return out


def main():
    rng = C.rng_for(NAME, SEED)
    splits = C.write_dataset(NAME, build(rng), HERE, PREFIX, seed=SEED, test_families=TEST_FAMILIES)
    C.summary(NAME, splits)
    return splits


if __name__ == "__main__":
    main()
