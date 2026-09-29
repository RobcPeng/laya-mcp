"""Generate the public-records-foia-routing accelerator set (deterministic, stdlib only).

Records requests are composed from a writing style (statute letter, casual email, portal form, attorney,
journalist, researcher, one-liner, forwarded portal notice, worried resident) and a record object drawn
from a department x complexity bank. Complaints, service requests, and general questions come from
their own hand-written families, including near-misses that borrow open-records language ("pursuant to
the open records act, fix the swing") or ask *about* records without requesting them. A contact line
decides contains_pii. TEST holds out whole families (two request styles plus complaint, service, and
question families).

    python datasets/accelerators/public-records-foia-routing/generate.py
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import _common as C  # noqa: E402

NAME = "public-records-foia-routing"
PREFIX = "foia"
SEED = 4417
PER_NONRECORD_FAMILY = 12

MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September",
          "October", "November", "December"]
BUSINESSES = ["Sunrise Daycare", "the Blue Heron Apartments", "Mesa Vista Senior Living", "Ridge Auto Body",
              "the Maple Street Warehouse", "Canyon Self Storage", "Pinecrest Plaza", "the Old Mill Lofts"]
RESTAURANTS = ["Lucky Noodle House", "Taqueria El Sol", "the Corner Diner", "Golden Crust Pizza",
               "Bayou Kitchen", "Green Bowl Cafe", "Sakura Sushi Bar", "Main Street Grill"]
VENDORS = ["Acme Paving Co.", "Summit Janitorial LLC", "Brightline IT Services", "Peak Fleet Supply",
           "Northstar Consulting Group", "Clearwater Engineering", "Keystone Uniforms"]
PROJECTS = ["Riverfront Commons", "the Elm Street Lofts", "Foothill Station", "the Harvest Ridge subdivision",
            "the 5th Street mixed-use project", "Cottonwood Crossing"]
TOPICS = ["the new stadium proposal", "short-term rentals", "the police oversight board", "the water rate increase",
          "the library closure", "the downtown parking plan", "the camping ban"]
JOBS = ["Assistant Planner", "Police Records Clerk", "Parks Maintenance Worker II", "Deputy Finance Director",
        "Building Inspector"]
STATUTES = ["the state Open Records Act", "the state Public Records Act", "the Anytown Open Records Ordinance",
            "the Freedom of Information Act", "the state open records law", "the state Sunshine Law",
            "the open records act"]
OUTLETS = ["the Anytown Ledger", "Pine County Public Radio", "the Valley Examiner", "KXMP News",
           "the Foothills Weekly", "an independent newsletter"]
FIRMS = ["Sample & Roe LLP", "Demo Law Group", "Placeholder Legal PC", "Fixture Stubbs Attorneys",
         "Mockford Legal Services"]
AREAS = ["Northside", "Old Town", "the East Ward", "Riverside", "the Mesa neighborhood"]


def ctx(rng):
    y = rng.randrange(2019, 2026)
    m1 = rng.randrange(0, 10)
    return {
        "year": str(y), "year0": str(y - rng.randrange(2, 6)),
        "month1": MONTHS[m1], "month2": MONTHS[m1 + rng.randrange(1, 3)],
        "date": C.pick(rng, [f"{C.pick(rng, MONTHS)} {rng.randrange(1, 29)}, {y}",
                             f"{rng.randrange(1, 13)}/{rng.randrange(1, 29)}/{y}",
                             f"{rng.randrange(1, 13)}/{rng.randrange(1, 29)}/{str(y)[2:]}"]),
        "case": C.pick(rng, [f"{str(y)[2:]}-{rng.randrange(1000, 99999):05d}", f"PD{y}-{rng.randrange(100, 9999)}",
                             f"#{rng.randrange(100000, 999999)}"]),
        "block": f"the {rng.randrange(1, 60) * 100} block of {C.pick(rng, C.STREETS)}",
        "inter": C.intersection(rng), "street": C.pick(rng, C.STREETS),
        "biz": C.pick(rng, BUSINESSES), "rest": C.pick(rng, RESTAURANTS), "vendor": C.pick(rng, VENDORS),
        "project": C.pick(rng, PROJECTS), "topic": C.pick(rng, TOPICS), "job": C.pick(rng, JOBS),
        "area": C.pick(rng, AREAS),
        "zcase": f"Z-{str(y)[2:]}-{rng.randrange(10, 400):03d}", "rfp": f"{y}-{rng.randrange(1, 90):03d}",
        "ord": f"{str(y)[2:]}-{rng.randrange(1, 60)}", "permit": f"BP{y}-{rng.randrange(1000, 9999)}",
    }


# department -> complexity level -> record objects (no private-person data in these)
OBJECTS = {
    "police": [
        ["the incident report for case number {case}", "a copy of police report {case}",
         "the crash report for the accident at {inter} on {date}"],
        ["all incident reports for calls to {block} between {month1} and {month2} {year}",
         "the 911 call audio and CAD log for the incident at {inter} on {date}",
         "the department's current use-of-force policy and the training slides that go with it"],
        ["all use-of-force reports filed from {year0} through {year}",
         "body camera and dashcam video from every officer who responded to {inter} on {date}, plus the CAD log and incident report",
         "arrest data by charge, race, and district for {year0} through {year}"],
        ["all body-worn camera footage recorded by patrol officers during the demonstrations from {month1} to {month2} {year}",
         "every internal affairs complaint file, including investigator notes and interview recordings, from {year0} to the present",
         "all emails and texts of command staff mentioning drones or facial recognition since {year0}"],
    ],
    "fire_ems": [
        ["the fire incident report for the structure fire on {block} on {date}",
         "the most recent fire inspection report for {biz}", "the fire marshal's report for the fire at {biz}"],
        ["fire code violation notices issued to {biz} in the last two years",
         "EMS response times for calls on {block} in {year}, no patient information",
         "the fire inspection and re-inspection reports for {biz} and {rest}"],
        ["all fire inspection reports for apartment buildings citywide from {year0} to {year}",
         "response-time data for every EMS call since {year0}, by station",
         "all fire code variances granted since {year0} with the supporting documents"],
        ["all EMS patient care reports for overdose calls from {year0} to {year}, redacted as needed",
         "every fire investigation file, including photos and witness statements, for all structure fires since {year0}",
         "all emails between the fire chief and the union about staffing since {year0}"],
    ],
    "public_works": [
        ["the as-built drawings for the water main on {street}", "the traffic count study for {inter} done last year",
         "the signed change order for the {street} repaving job"],
        ["the paving schedule and contract change orders for the {street} reconstruction",
         "water quality test results for our pressure zone for {year}",
         "pothole complaints and repair work orders for {street} in {year}"],
        ["all traffic studies and crash data used to decide against a signal at {inter}, {year0} to {year}",
         "every water main break record and repair work order citywide since {year0}",
         "snow plow GPS logs and route maps for the {year0}-{year} winters"],
        ["all correspondence, work orders, and consultant reports about the lead service line program since it began",
         "every email between the public works director and outside contractors from {year0} to the present",
         "all inspection photos, logs, and reports for every bridge the city maintains since {year0}"],
    ],
    "planning_zoning": [
        ["building permit {permit}", "the certificate of occupancy for {biz}",
         "the approved site plan for {project}"],
        ["the staff report, site plan, and approval letter for rezoning case {zcase}",
         "code enforcement complaints and violation notices for {biz} in the last three years",
         "the inspection records for building permit {permit}"],
        ["all permits, plan reviews, and inspection records for {project} from application to final",
         "every short-term rental license issued and all related code violations from {year0} to {year}",
         "all variance requests and decisions for {area} since {year0}"],
        ["all zoning variance applications, staff reports, and board correspondence for the last ten years",
         "every document, email, and text message related to the {project} development agreement",
         "all code enforcement case files citywide since {year0}, with photos"],
    ],
    "finance": [
        ["the signed contract with {vendor}", "the adopted {year} city budget",
         "the award memo for RFP {rfp}"],
        ["all invoices paid to {vendor} in fiscal year {year}",
         "the bid tabulation, proposals, and award memo for RFP {rfp}",
         "the city's investment reports for the four quarters of {year}"],
        ["every purchasing card transaction by city employees from {year0} through {year}",
         "all contracts over $50,000 awarded in the last three fiscal years, with bid documents",
         "all payments to {vendor} and {vendor} since {year0} with the matching contracts"],
        ["the complete general ledger with vendor detail for fiscal years {year0} through {year}",
         "all audit workpapers, management letters, and auditor correspondence for the past five years",
         "every email from finance staff mentioning {vendor} since {year0}"],
    ],
    "human_resources": [
        ["the current job description for the {job} position", "the city's current pay plan and salary schedule",
         "the job posting for the {job} opening"],
        ["salary and overtime paid to police sergeants in {year}",
         "the job posting, number of applicants, and interview scoring rubric for the {job} opening",
         "the employee handbook and the remote-work policy in effect in {year}"],
        ["name, title, base salary, overtime, and total compensation for every city employee from {year0} to {year}",
         "all disciplinary actions taken against Parks Department employees since {year0}",
         "all separation agreements and settlement payments to former employees since {year0}"],
        ["complete personnel files, including reviews and discipline, for every employee terminated in the last five years",
         "all harassment complaints and investigation files filed with HR since {year0}",
         "every email of HR staff mentioning the {job} hiring process since {year0}"],
    ],
    "clerk": [
        ["the minutes of the city council meeting on {date}", "Ordinance {ord} as adopted",
         "the video of the {date} council work session"],
        ["council agendas, minutes, and packets for every meeting in {month1} and {month2} {year}",
         "all resolutions the council passed about {topic} in {year}",
         "the sign-in sheets and written public comments from the {date} council meeting"],
        ["every council member's official calendar since {year0}",
         "all campaign finance reports for council candidates from {year0} to {year}",
         "all agendas, minutes, and recordings of the planning commission and council about {topic} since {year0}"],
        ["all emails and text messages between council members and the mayor mentioning {topic} for the past four years",
         "every executive session recording and handout since {year0}",
         "all records retention schedules and destruction logs for every department since {year0}"],
    ],
    "parks": [
        ["the rental agreement for the Riverside Park pavilion on {date}", "the {year} summer rec program fee schedule",
         "the pool opening schedule memo for {year}"],
        ["trail maintenance logs for the Cottonwood Trail in {year}",
         "playground safety inspection reports for Riverside Park and Elm Park",
         "the tree removal list and arborist report for Lincoln Park from {year}"],
        ["all pesticide and herbicide application records for city parks from {year0} to {year}",
         "fee waivers and scholarships granted for every youth program since {year0}",
         "all facility rental records for the rec center from {year0} to {year}"],
        ["every document related to the parks master plan update, including consultant drafts, public comments, and staff emails",
         "all incident and injury reports at every city pool and park since {year0}",
         "all emails of parks staff mentioning the golf course sale since {year0}"],
    ],
    "health": [
        ["the latest food inspection report for {rest}", "the food truck permit for {rest}",
         "the pool inspection report for {biz}"],
        ["all food inspection reports for {rest} in the past three years",
         "the septic permit and inspection history for {project}",
         "complaints and inspections for {rest} and {rest} in {year}"],
        ["all food establishment inspections with critical violations countywide from {year0} to {year}",
         "environmental health complaints for {area} since {year0}",
         "every mold and indoor air complaint investigated in {year0}-{year}"],
        ["all communicable disease investigation files and correspondence with the state for the past five years",
         "every inspection, complaint, and enforcement record for all food establishments in the county since {year0}",
         "all emails of the health director about the {year} outbreak response"],
    ],
}

# ------------------------------------------------------------------ contact lines (decide contains_pii)


def contact(rng, records=True):
    """Returns (text, has_pii). PII = personal data about a private individual (home address, phone,
    date of birth, government ID). A name alone, a firm signature, or a newsroom are not PII here."""
    name = C.person(rng)
    if rng.random() < 0.38:
        k = rng.randrange(6)
        if k == 0:
            return f"You can reach me at {C.phone(rng)}.\n{name}", True
        if k == 1:
            if records:
                return f"Please mail copies to {name}, {C.address(rng)}, Anytown.", True
            return f"I live at {C.address(rng)}. {name}", True
        if k == 2:
            return f"{name}\n{C.address(rng)}\nAnytown\ncell {C.phone(rng)}", True
        if k == 3:
            return f"Requester: {name}, DOB {C.dob(rng)}, phone {C.phone(rng)}", True
        if k == 4:
            return f"{name}, driver's license no. D{rng.randrange(1000000, 9999999)}, {C.address(rng)}", True
        return f"Contact: {C.phone(rng)} (home). {name}", True
    k = rng.randrange(6)
    return ["", "Thank you.", f"- {name}", f"Thanks,\n{C.first_name(rng)}",
            f"{name}\nParalegal, {C.pick(rng, FIRMS)}", "Please respond through the portal."][k], False


OWN_RECORD = [  # requests about the requester's own records: always carry personal identifiers
    ("police", 0, "I need a copy of the police report from when my car was broken into. My name is {name}, date of birth {dob}, and I live at {home}."),
    ("police", 1, "Requesting any records about me held by the department. Full name {name}, DOB {dob}, SSN {ssn}."),
    ("fire_ems", 0, "I was transported by your ambulance on {date}. I need the run report for my insurance. {name}, born {dob}, phone {phone}."),
    ("human_resources", 1, "I'm a former employee requesting my own personnel file and final pay records. {name}, employee ID and SSN {ssn}, current address {home}."),
    ("planning_zoning", 0, "I own the house at {home} and need the permit history for my property. {name}, {phone}."),
]

STYLES = {
    "statute": [
        "Pursuant to {statute}, I request copies of {obj}. {fmt} {fee}\n\n{contact}",
        "Under {statute}, please provide {obj}. {fmt} Please let me know if any portion is withheld and the legal basis. {fee}\n\n{contact}",
        "Dear Records Custodian,\n\nThis is a request under {statute} for {obj}. {fee} {fmt}\n\nSincerely,\n{contact}",
    ],
    "casual": [
        "hi, could I get {obj}? {why} thanks\n{contact}",
        "Hello - looking for {obj}. {why} Is that something you can send? {contact}",
        "Hey there, how do I get a copy of {obj}? Actually just consider this my request. {contact}",
    ],
    "portal": [
        "Request type: Public records\nRecords requested: {obj}\nPreferred format: {fmtshort}\nFee waiver requested: {waiver}\nAdditional details: {why}\n{contact}",
        "Description of records sought: {obj}.\nDelivery: {fmtshort}\nPurpose (optional): {why}\n{contact}",
    ],
    "attorney": [
        "This office represents a client in a pending matter. Pursuant to {statute}, please produce {obj}. {fmt} Please preserve all responsive records.\n\n{contact}",
        "RE: Records request\n\nOn behalf of our client, we request {obj} under {statute}. We agree to pay reasonable copying costs. {fmt}\n\n{contact}",
    ],
    "journalist": [
        "I'm a reporter with {outlet}. Under {statute}, I'm requesting {obj}. I ask that fees be waived because disclosure is in the public interest and this is for news reporting. {fmt}\n\n{contact}",
        "Media request ({outlet}): {obj}. Rolling production is fine - please send records as they are ready. Fee waiver requested. {contact}",
    ],
    "researcher": [
        "I'm a graduate student studying local government and would like {obj}. It's for a thesis, not commercial use. {fmt} {fee}\n{contact}",
        "Our nonprofit is compiling data on city services. We request {obj}. {fee} {fmt}\n{contact}",
    ],
    "oneliner": [
        "{obj} please. {contact}",
        "Requesting: {obj}. {contact}",
        "need {obj} asap {contact}",
    ],
    "forwarded": [
        "---------- Forwarded message ---------\nFrom: Records Portal <noreply@anytown.example.gov>\nSubject: New request #{n}\n\nA new public records request was submitted.\nRequest: {obj}.\n{contact}",
        "FW: records request\n\n> {obj_cap}.\n> {fee}\n> {contact}\n\nForwarding to the right department - not sure who owns this. -Front desk",
    ],
    "resident": [
        "I'm not sure this is the right place. I think the city approved something without telling anyone, and I'd like to see {obj}. {why} {contact}",
        "Good afternoon. My neighbors and I want {obj}. We just want to understand what happened. {fee} {contact}",
    ],
}

WHY = ["", "", "It's for an insurance claim.", "I'm writing an article.", "Our HOA is asking.",
       "Just want to understand what happened.", "Need it for a court date.", "For a school project.",
       "We're considering buying nearby.", "Curious how my tax dollars are spent."]
FMT = ["", "Electronic copies by email are preferred.", "PDF is fine.", "Please provide spreadsheets in native Excel format.",
       "I can pick up paper copies.", "A download link is fine for large files."]
FMTSHORT = ["Electronic", "PDF", "Paper - pick up", "Native format", "Email"]
FEE = ["", "", "I am willing to pay up to $50; please contact me before exceeding that.",
       "Please waive any fees, as this is in the public interest.",
       "If the estimated cost is over $25, let me know first.", "Please send a cost estimate before starting."]

# ------------------------------------------------------------------ non-records families
# (family, department, request_type, templates). Complexity is 0 for all of these: no records to produce.
NONRECORD = [
    ("complaint/officer", "police", "complaint", [
        "I want to file a complaint about the officer who pulled me over on {date}. He was rude, yelled at my kids, and never told me why I was stopped.",
        "The officer who took my report last week was dismissive and refused to write down what I said. I want this documented as a complaint.",
    ]),
    ("complaint/ems-response", "fire_ems", "complaint", [
        "It took the ambulance 40 minutes to reach {block} on {date}. My father waited on the floor the whole time. This is unacceptable.",
        "The fire crew that came to our building left a mess and broke the lobby door. Nobody has called us back about it.",
    ]),
    ("complaint/street-crew", "public_works", "complaint", [
        "Your road crew has left {street} torn up for six weeks with no work happening. Businesses are losing customers. Who is responsible?",
        "The snow plow driver buried our driveway three times this week and flipped us off. I'm filing a complaint.",
    ]),
    ("complaint/permit-delay", "planning_zoning", "complaint", [
        "My building permit {permit} has been sitting in review for four months. Nobody answers the phone. This process is broken.",
        "The inspector failed our deck for a reason that isn't in the code, and now he won't return calls. I want to complain about how this was handled.",
    ]),
    ("complaint/billing", "finance", "complaint", [
        "I was charged a late fee on my utility bill even though I paid on time. This is the second time. I want it fixed and I want an explanation.",
        "The city charged my business license fee twice and refuses to refund it. Very frustrated with the finance office.",
    ]),
    ("complaint/hiring", "human_resources", "complaint", [
        "I applied for the {job} job, interviewed, and never heard anything. The hiring process is unfair and nobody follows up.",
        "A supervisor in the streets division has been treating his crew terribly. As a city employee I am filing a complaint.",
    ]),
    ("complaint/council", "clerk", "complaint", [
        "The council cut off public comment on {topic} after ten minutes. That is not how a public meeting should run.",
        "The agenda for the {date} meeting was posted late, so nobody could prepare. This keeps happening.",
    ]),
    ("complaint/records-slow", "clerk", "complaint", [
        "I submitted a records request 45 days ago and have heard nothing. The law gives you a deadline and you've blown past it.",
        "Your records office said my request was 'too broad' and closed it without talking to me. I'm complaining about that decision.",
    ]),
    ("complaint/park-staff", "parks", "complaint", [
        "The lifeguards at the city pool were on their phones while kids were in the deep end. Somebody is going to drown.",
        "The rec center staff canceled my son's soccer program with one day of notice and won't refund us.",
    ]),
    ("complaint/restaurant", "health", "complaint", [
        "I got food poisoning after eating at {rest} on {date}. The kitchen was filthy. They should be shut down.",
        "There are cockroaches all over {rest}, I saw them on the counter. Why is this place still open?",
    ]),
    ("complaint/disguised", "planning_zoning", "complaint", [
        "Pursuant to {statute}, I demand to know why my fence permit was denied and I demand that decision be reversed. The denial is unfair.",
        "Records request: the city's decision to deny my variance was wrong and I object to how the board treated me.",
    ]),
    ("service/street", "public_works", "service_request", [
        "Please fix the pothole at {inter}. It's been there for weeks.",
        "The streetlight on {block} is out. Can you send a crew?",
    ]),
    ("service/patrol", "police", "service_request", [
        "Can you send officers to patrol {block} in the evenings? People speed through every night.",
        "Please have an officer check on the abandoned house on {block}, kids have been going in.",
    ]),
    ("service/inspection", "planning_zoning", "service_request", [
        "Please send an inspector to look at the apartment building on {block}. The landlord built an addition without a permit.",
        "Can the city inspect the vacant lot on {block}? The fence is falling down and there's junk everywhere.",
    ]),
    ("service/fire", "fire_ems", "service_request", [
        "I'd like to schedule a fire safety inspection for my new business before we open.",
        "Can the fire department install a free smoke detector for my elderly mother?",
    ]),
    ("service/agenda", "clerk", "service_request", [
        "Please put {topic} on the next council agenda. Residents want a vote.",
        "I'd like to sign up to speak at the next council meeting about {topic}.",
    ]),
    ("service/restaurant-check", "health", "service_request", [
        "Please send an inspector to check {rest}. The walk-in cooler was broken when I was there.",
        "Can environmental health test the water at the splash pad in Riverside Park? It looks cloudy.",
    ]),
    ("service/disguised-parks", "parks", "service_request", [
        "Open records request: please fix the broken swing at Elm Park before someone gets hurt.",
        "Pursuant to {statute}, I request that the city trim the dead tree over the trail in Lincoln Park.",
    ]),
    ("service/hr-update", "human_resources", "service_request", [
        "I'm a city employee and need my W-2 mailing address updated in the payroll system.",
        "Please remove me from the lifeguard applicant list, I took another job.",
    ]),
    ("question/fees", "clerk", "question", [
        "How much does the city charge per page for records, and do you take cards?",
        "How long does a typical records request take to process?",
    ]),
    ("question/meeting", "clerk", "question", [
        "When is the next city council meeting and is it streamed online?",
        "Is the council meeting on {date} still happening at City Hall?",
    ]),
    ("question/report-cost", "police", "question", [
        "Do I need to come in person to get a police report, or can it be done online?",
        "What's the difference between an incident report and a crash report?",
    ]),
    ("question/permit", "planning_zoning", "question", [
        "Do I need a permit to replace my backyard fence if it's under six feet?",
        "What zoning district allows home daycares?",
    ]),
    ("question/jobs", "human_resources", "question", [
        "Is the city hiring seasonal lifeguards this summer?",
        "Do city jobs require a residency requirement?",
    ]),
    ("question/parks", "parks", "question", [
        "What are the pool hours this summer and are dogs allowed at Riverside Park?",
        "Can I reserve the pavilion for a birthday party, and how far ahead?",
    ]),
    ("question/about-records", "finance", "question", [
        "Does the city keep records of vendor payments, and how would someone go about requesting them?",
        "Is the city budget public? Where would I find it?",
    ]),
    ("question/health", "health", "question", [
        "Where can I look up restaurant inspection scores?",
        "Do I need a permit to sell baked goods at the farmers market?",
    ]),
    ("question/trash", "public_works", "question", [
        "Which day is bulk trash pickup on the north side?",
        "Is water service affected by the construction on {street}?",
    ]),
]

TEST_FAMILIES = ["rr/journalist", "rr/forwarded", "rr/own-record-b",
                 "complaint/records-slow", "complaint/ems-response", "complaint/disguised",
                 "service/disguised-parks", "service/patrol",
                 "question/about-records", "question/permit"]


def cap(s):
    return s[:1].upper() + s[1:]


def make_records(rng):
    out = []
    for style, templates in STYLES.items():
        for dept, levels in OBJECTS.items():
            for lvl, objs in enumerate(levels):
                for rep in range(2 if lvl and rng.random() < 0.7 else 1):
                    c = ctx(rng)
                    obj = C.pick(rng, objs).format(**c)
                    tpl = C.pick(rng, templates)
                    contact_txt, pii = contact(rng)
                    text = tpl.format(
                        statute=C.pick(rng, STATUTES), obj=obj, obj_cap=cap(obj), fmt=C.pick(rng, FMT),
                        fee=C.pick(rng, FEE), why=C.pick(rng, WHY), contact=contact_txt,
                        fmtshort=C.pick(rng, FMTSHORT), waiver=C.pick(rng, ["Yes", "No", "No"]),
                        outlet=C.pick(rng, OUTLETS), n=rng.randrange(10000, 99999))
                    text = C.messy(rng, text, typo_rate=0.03, p_typo=0.35 if style in ("casual", "oneliner") else 0.12)
                    out.append({"family": f"rr/{style}", "group": dept, "state": {"request": text},
                                "gold": {"department": dept, "request_type": "records_request",
                                         "contains_pii": pii, "complexity": lvl}})
    # requester's own records (always PII); two families so one can be held out
    for i in range(36):
        dept, lvl, tpl = OWN_RECORD[i % len(OWN_RECORD)]
        c = ctx(rng)
        text = tpl.format(name=C.person(rng), dob=C.dob(rng), home=C.address(rng), ssn=C.fake_ssn(rng),
                          phone=C.phone(rng), date=c["date"])
        text = C.pick(rng, ["", "Hi, ", "Pursuant to the open records act: ", "Hello. "]) + text
        text = C.messy(rng, text, 0.03, 0.3)
        out.append({"family": "rr/own-record-" + ("a" if i % 3 else "b"), "group": dept,
                    "state": {"request": text},
                    "gold": {"department": dept, "request_type": "records_request", "contains_pii": True,
                             "complexity": lvl}})
    return out


def make_nonrecords(rng):
    out = []
    openers = ["", "", "Hi, ", "Hello, ", "To whom it may concern: ", "Good morning. ", "URGENT: ", "Not sure who handles this. "]
    for fam, dept, rtype, templates in NONRECORD:
        for i in range(PER_NONRECORD_FAMILY):
            c = ctx(rng)
            c["statute"] = C.pick(rng, STATUTES)
            text = C.pick(rng, openers) + templates[i % len(templates)].format(**c)
            contact_txt, pii = contact(rng, records=False)
            text = (text + "\n\n" + contact_txt).strip()
            text = C.messy(rng, text, 0.04, 0.4)
            out.append({"family": fam, "group": dept, "state": {"request": text},
                        "gold": {"department": dept, "request_type": rtype, "contains_pii": pii,
                                 "complexity": 0}})
    return out


def main():
    rng = C.rng_for(NAME, SEED)
    examples = make_records(rng) + make_nonrecords(rng)
    splits = C.write_dataset(NAME, examples, HERE, PREFIX, seed=SEED, test_families=TEST_FAMILIES)
    C.summary(NAME, splits)
    return splits


if __name__ == "__main__":
    main()
