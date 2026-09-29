"""Generate the he-financial-aid-triage accelerator set (deterministic, stdlib only).

Topic comes from hand-written phrasing families (three per topic, two core templates each). Two
independent modifiers are layered on each row:

  deadline:  a near deadline sentence ("the appeal is due Friday", "classes start Monday") -> true;
             a far or past deadline ("no rush, this is for next year") or nothing -> false.
  sensitive: an actual income figure, tax-return value, bank account number, or SSN -> true;
             look-alikes (student ID, award amounts, bill balance, a 555 phone, "I uploaded my tax
             transcript" without values) or nothing -> false.

Then a channel wrapper (portal form, email, parent writing, chat), optional Spanish-English
code-switching, and a noise pass. TEST holds out one family per topic.

    python datasets/accelerators/he-financial-aid-triage/generate.py
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import _common as C  # noqa: E402

NAME = "he-financial-aid-triage"
PREFIX = "hefa"
PER_FAMILY = 30
SEED = 5202

SCHOOLS = ["Pine Valley State University", "Northfield Community College", "Cedar Ridge University",
           "Lakeshore Technical College", "Mesa Verde State College", "Eastbrook University"]

SLOTS = {
    "term": ["fall", "spring", "this semester", "next semester", "the 2026-27 year", "summer"],
    "award": ["$3,700", "$5,500", "$1,200", "$7,395", "$2,000", "$650"],
    "gpa": ["1.8", "1.9", "1.75", "1.6", "2.1"],
}

# topic -> list of (family, [templates])
TOPICS = {
    "verification": [
        ("verification/documents", [
            "I was selected for verification. What documents do I need to send?",
            "Why was I picked for verification? I didn't do anything wrong on the FAFSA.",
        ]),
        ("verification/tax-transcript", [
            "The portal says I need an IRS tax return transcript but the IRS site won't let me log in. What else can I send?",
            "My parents filed an amended return. Can I use that for the verification requirement?",
        ]),
        ("verification/household-mismatch", [
            "My verification worksheet says 4 people in the household but the FAFSA says 5 and now it's flagged. How do I fix it?",
            "You asked me to correct the number in college on my FAFSA for verification. Where do I do that?",
        ]),
    ],
    "sap_appeal": [
        ("sap/completion-rate", [
            "I got a SAP suspension notice because my completion rate is under 67%. What can I do?",
            "My aid got suspended for not completing enough credits last year. How do I get it back?",
        ]),
        ("sap/appeal-circumstances", [
            "I want to appeal losing my aid. I was in the hospital for most of last semester and failed two classes.",
            "My dad passed away in October and my grades dropped. How do I write a satisfactory academic progress appeal?",
        ]),
        ("sap/gpa-timeframe", [
            "My GPA is {gpa} and the email says I'm on financial aid warning. Does that mean I lose my Pell?",
            "I hit the maximum timeframe for my degree because I changed majors twice. Can I appeal with an academic plan?",
        ]),
    ],
    "dependency_override": [
        ("dep/no-contact", [
            "I haven't lived with my parents since I was 16 and I can't get their information for the FAFSA. What do I do?",
            "I have no contact with my parents at all. Is there a way to file without their info?",
        ]),
        ("dep/unsafe-home", [
            "My parents kicked me out last year and I've been staying with my aunt. Can I be considered independent?",
            "My high school counselor said I might qualify for a dependency override because of abuse at home. What paperwork do you need?",
        ]),
        ("dep/refuses", [
            "My parents refuse to give me their tax info but I still live with them. Can I get an override?",
            "Is there a form for unusual circumstances when you can't provide parent information? My situation is complicated.",
        ]),
    ],
    "award_letter": [
        ("award/decline-loans", [
            "My award letter includes loans I didn't ask for. Can I decline them and keep the grants?",
            "Can I reduce the loan amount on my aid offer? I only need part of it.",
        ]),
        ("award/explain", [
            "I don't understand my financial aid offer. What's the difference between the grant and the loan lines?",
            "My award went down from last year even though nothing changed. Can you explain the {award} difference?",
        ]),
        ("award/special-circumstances", [
            "My mom lost her job after we filed the FAFSA. Can my aid offer be reconsidered?",
            "We had big medical bills this year that aren't on the FAFSA. Can you do a professional judgment review of my award?",
        ]),
    ],
    "disbursement": [
        ("disb/when", [
            "When will my financial aid disburse this semester?",
            "My aid shows accepted but hasn't paid to my account yet. When does it post?",
        ]),
        ("disb/refund-check", [
            "My refund hasn't come yet. When do aid refunds go out?",
            "I got less of a refund than I expected, where did the rest of my {award} go?",
        ]),
        ("disb/not-applied", [
            "My grant shows on the portal but it hasn't been applied to my bill and I have a balance.",
            "The aid paid but my bill still shows I owe money. Is something wrong?",
        ]),
    ],
    "work_study": [
        ("ws/hours", [
            "How many hours a week can I work with my work-study award?",
            "What happens if I earn my whole work-study award before the semester ends?",
        ]),
        ("ws/find-job", [
            "I was offered work-study but I can't find a job. Will I lose the award?",
            "Can I use my federal work-study for an off-campus job at a nonprofit?",
        ]),
        ("ws/paycheck", [
            "My work-study paycheck was less than I expected. Who do I ask about my hours?",
            "I didn't get paid for my work-study hours last pay period. My supervisor said to contact you.",
        ]),
    ],
    "loans": [
        ("loans/accept", [
            "How do I accept my Direct Loans for {term}?",
            "Do I have to do entrance counseling and sign the MPN again this year?",
        ]),
        ("loans/parent-plus", [
            "My parents were denied a Parent PLUS loan. What happens now?",
            "Can my mom apply for a PLUS loan if she has bad credit? What are the options?",
        ]),
        ("loans/limits", [
            "How much can I borrow in unsubsidized loans as an independent student?",
            "I reached my loan limit. Are there any other loans I can get for {term}?",
        ]),
    ],
    "scholarships": [
        ("schol/apply", [
            "When is the general scholarship application for returning students due?",
            "Where do I find the list of department scholarships for nursing majors?",
        ]),
        ("schol/outside", [
            "I got an outside scholarship from my church. How do I report it and will it lower my other aid?",
            "A local foundation is sending me a {award} scholarship check. Does it go to you or to me?",
        ]),
        ("schol/renewal", [
            "Will my merit scholarship renew if my GPA ended at {gpa}?",
            "What are the renewal requirements for the Presidential scholarship? I dropped to part-time.",
        ]),
    ],
    "other": [
        ("other/office", [
            "What are the financial aid office hours? Can I come in without an appointment?",
            "Is there a financial aid counselor who speaks Spanish?",
        ]),
        ("other/1098t-address", [
            "Where do I get my 1098-T for taxes?",
            "How do I update my mailing address with the financial aid office?",
        ]),
        ("other/basic-needs", [
            "Is there a food pantry or emergency grocery help on campus?",
            "Does the school have laptop loans for students who can't afford one?",
        ]),
    ],
}

TEST_FAMILIES = ["verification/household-mismatch", "sap/appeal-circumstances", "dep/refuses", "award/special-circumstances",
                 "disb/refund-check", "ws/paycheck", "loans/parent-plus", "schol/outside", "other/basic-needs"]

DEADLINE_NEAR = [
    "I have to turn this in by Friday.", "Classes start Monday and my bill is due.", "I have to get this done by the 15th, that's in five days.",
    "My payment is due tomorrow.", "The priority deadline is next week.", "They said I'll be dropped for nonpayment this Thursday.",
    "Census date is in 3 days.", "I need this before the term starts next week.", "My rent is due Friday and I was counting on the refund.",
    "The deadline on the letter is this Wednesday.", "Orientation is in two days and I need this sorted out before then.",
]
DEADLINE_FAR = [
    "No rush, this is for next year.", "I know the deadline isn't until next spring.",
    "I missed last year's deadline but that's in the past now.", "This is for planning ahead for 2028.",
    "Just asking for the future, not urgent.",
]

def s_income(rng):
    a, b = rng.randrange(18, 95) * 1000 + rng.randrange(0, 999), rng.randrange(8, 60) * 1000 + rng.randrange(0, 999)
    return C.pick(rng, [f"My dad made ${a:,} last year and my mom made ${b:,}.",
                        f"Our AGI on the 2024 tax return was ${a:,}.",
                        f"I only made ${b:,} last year from my job at the grocery store.",
                        f"The tax return shows wages of ${a:,} and ${rng.randrange(400, 4000):,} in income tax paid.",
                        f"My household income dropped from ${a:,} to ${b:,}."])


def s_ssn(rng):
    return C.pick(rng, [f"My SSN is {C.fake_ssn(rng)} if you need to look me up.",
                        f"SSN {C.fake_ssn(rng)}", f"my social is {C.fake_ssn(rng)}"])


def s_bank(rng):
    acct = f"{rng.randrange(10**9, 10**10)}"
    return C.pick(rng, [f"Please send the refund to my checking account {acct}, routing 0{rng.randrange(10**7, 10**8)}.",
                        f"My bank account number is {acct} for direct deposit."])


SENSITIVE = [s_income, s_income, s_ssn, s_bank]


def s_lookalike(rng):
    return C.pick(rng, [f"My student ID is S{rng.randrange(0, 10**8):08d}.", f"You can call me at {C.phone(rng)}.",
                        f"My Pell grant is {C.pick(rng, SLOTS['award'])}.", f"I owe {C.pick(rng, SLOTS['award'])} on my bill.",
                        "I already uploaded my tax transcript last week.", "My parents filed their taxes in April.",
                        f"My work-study award is {C.pick(rng, SLOTS['award'])}.", "Our income went down a lot this year."])


OPENERS = ["", "", "", "Hi, ", "Hello, ", "Good afternoon, ", "Hi financial aid, ", "Sorry for the long email. ",
           "Quick question. ", "Dear Financial Aid Office, "]
SPANISH = [("Hola, ", " Gracias."), ("Buenas, ", " Muchas gracias por su ayuda."), ("", " Mi mamá no habla mucho inglés, por eso escribo yo.")]


def wrap(rng, text):
    name = C.person(rng)
    k = rng.random()
    if k < 0.25:
        return (f"Financial Aid Inquiry Form\nStudent ID: S{rng.randrange(0, 10**8):08d}\nSchool: {C.pick(rng, SCHOOLS)}\n"
                f"Aid year: 2026-27\nQuestion: {text}")
    if k < 0.5:
        sig = C.pick(rng, [f"\n\n{name}", f"\n\nThank you,\n{name}\nStudent ID S{rng.randrange(0, 10**8):08d}",
                           "\n\nSent from my phone"])
        out = f"Subject: {C.pick(rng, ['Financial aid question', 'FAFSA', 'Help with aid', 'Re: Action required', 'urgent'])}\n\n{text}{sig}"
        if rng.random() < 0.2:
            out = f"---------- Forwarded message ---------\nFrom: {C.email(rng, name, 'example.edu')}\n\n" + out
        return out
    if k < 0.65:
        who = C.pick(rng, ["my daughter", "my son", "our student"])
        return (C.pick(rng, [f"Hi, I'm a parent. {who.capitalize()} asked me to send this for them: ",
                             f"Parent here, forwarding for {who}: "]) + '"' + text + '"')
    if k < 0.85:
        return text.lower()
    return text


def build(rng):
    examples = []
    for topic, fams in TOPICS.items():
        for fam, templates in fams:
            for i in range(PER_FAMILY):
                core = C.fill(rng, templates[i % len(templates)], SLOTS)
                parts = [core]
                deadline = rng.random() < 0.45
                if deadline:
                    parts.append(C.pick(rng, DEADLINE_NEAR))
                elif rng.random() < 0.35:
                    parts.append(C.pick(rng, DEADLINE_FAR))
                sensitive = rng.random() < 0.4
                if sensitive:
                    parts.insert(rng.randrange(0, 2) + 1 if len(parts) > 1 else 1, C.pick(rng, SENSITIVE)(rng))
                elif rng.random() < 0.45:
                    parts.insert(1, s_lookalike(rng))
                text = " ".join(parts)
                opener = C.pick(rng, OPENERS)
                if opener and not text.startswith("I "):
                    text = text[0].lower() + text[1:]
                text = opener + text
                if rng.random() < 0.1:
                    o, c = C.pick(rng, SPANISH)
                    text = o + text + c
                text = C.messy(rng, text, typo_rate=0.035, p_typo=0.35)
                examples.append({
                    "family": fam, "group": topic,
                    "state": {"message": wrap(rng, text)},
                    "gold": {"topic": topic, "deadline_sensitive": deadline, "sensitive_info": sensitive},
                })
    return examples


def main():
    rng = C.rng_for(NAME, SEED)
    splits = C.write_dataset(NAME, build(rng), HERE, PREFIX, seed=SEED, test_families=TEST_FAMILIES)
    C.summary(NAME, splits)
    return splits


if __name__ == "__main__":
    main()
