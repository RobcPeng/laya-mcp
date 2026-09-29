"""Generate the benefits-eligibility-intake accelerator set (deterministic, stdlib only).

A message is composed from: a program need (hand-written core families per program, some mentioning a
second benefit the household already gets or a secondary need), a hardship line (urgent, non-urgent
context, or a near-miss such as an eviction that happened last year), and three intake facts —
household size, monthly income, county — each independently present or absent (absent means left out
or said vaguely: "me and my kids", "I don't make much", a city with no county). Voices: first person,
caseworker note, web chat, voicemail transcript, helper writing for a relative, occasional
Spanish-English code-switching. TEST holds out one core family per program.

    python datasets/accelerators/benefits-eligibility-intake/generate.py
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import _common as C  # noqa: E402

NAME = "benefits-eligibility-intake"
PREFIX = "ben"
SEED = 2027
PER_FAMILY = 30
P_FACT = 0.77            # each fact present with this probability -> all three present ~46%

COUNTIES = ["Pine County", "Cedar County", "Mesa County", "Juniper County", "Aspen County",
            "Clearwater County", "Red Rock County", "Silver Lake County"]
TOWNS = ["Anytown", "Springdale", "Fort Example", "Lakeside", "Millbrook", "North Placeholder"]

# (program, family, [core need templates]). The core states the ask; it must not itself say a
# household size, a monthly income amount, or a county (facts are added separately).
CORES = [
    ("snap", "snap/groceries", [
        "I need help buying groceries. Can I get food stamps?",
        "How do I apply for SNAP? We can't keep up with food costs.",
        "I want to sign up for EBT food benefits.",
    ]),
    ("snap", "snap/renewal-cut", [
        "My food stamps got cut off and I don't know why. I need to reapply.",
        "Our SNAP benefits went down to almost nothing this month. Can someone review it?",
    ]),
    ("snap", "snap/student-senior", [
        "I'm a college student working part time, am I able to get food assistance?",
        "My grandma is 78 and only eats what the church pantry gives her. She needs food benefits.",
    ]),
    ("snap", "snap/spanish", [
        "Hola, necesito ayuda con la comida. Quiero aplicar para food stamps.",
        "Buenas, my English is not so good. Necesitamos ayuda para comprar comida, EBT card.",
    ]),
    ("medicaid", "medicaid/coverage", [
        "I lost my health insurance and need coverage. Do I qualify for Medicaid?",
        "How do I get health insurance for my kids? We can't afford the plan at my job.",
        "Need to apply for medical assistance, no insurance right now.",
    ]),
    ("medicaid", "medicaid/bills", [
        "I have hospital bills from last month and no insurance. Is there a program that can cover them?",
        "My prescriptions cost more than I can pay. I need medical coverage.",
    ]),
    ("medicaid", "medicaid/pregnancy", [
        "I just found out I'm pregnant and I don't have insurance for prenatal care.",
        "My daughter is pregnant, 19, no coverage. She needs to see a doctor.",
    ]),
    ("medicaid", "medicaid/already-snap", [
        "We already get SNAP, that part is fine. What I need now is health coverage for my husband.",
        "I have EBT already. The problem is doctor visits, I need Medicaid.",
    ]),
    ("unemployment", "unemployment/laid-off", [
        "I got laid off last week. How do I file for unemployment?",
        "The warehouse closed and everyone lost their jobs. I need to apply for unemployment benefits.",
        "Fired after 6 years, not for misconduct, they said budget cuts. Want to file a claim.",
    ]),
    ("unemployment", "unemployment/hours-cut", [
        "My hours got cut from 40 to 15. Can I get partial unemployment?",
        "Restaurant cut my shifts in half. Is there unemployment for reduced hours?",
    ]),
    ("unemployment", "unemployment/claim-issue", [
        "My unemployment claim has been pending for five weeks. I need someone to look at it.",
        "They denied my unemployment claim saying I quit but I was let go. I want to appeal.",
    ]),
    ("unemployment", "unemployment/spanish", [
        "Perdí mi trabajo en la construcción. How do I apply for desempleo?",
        "Me despidieron del hotel, necesito unemployment. No sé cómo aplicar.",
    ]),
    ("housing", "housing/rent", [
        "I'm behind on rent and need help paying it.",
        "Is there rental assistance? I owe two months.",
        "Can the county help with rent? The landlord raised it and I can't cover it.",
    ]),
    ("housing", "housing/voucher", [
        "How do I get on the waiting list for a housing voucher?",
        "I'd like to apply for Section 8 or any affordable housing program.",
    ]),
    ("housing", "housing/shelter", [   # homelessness is stated in the core: always urgent
        "I'm homeless as of this week and need a place to stay. Is there shelter or housing help?",
        "My ex kicked me out last night and I have nowhere to sleep.",
    ]),
    ("housing", "housing/repairs-deposit", [
        "I found a cheaper apartment but can't afford the deposit. Is there help with move-in costs?",
        "I need help with a security deposit to move closer to my job.",
    ]),
    ("childcare", "childcare/work", [
        "I just got a job but can't start until I find daycare I can afford. Is there help paying for child care?",
        "Daycare costs more than my rent. Is there a child care subsidy?",
        "I need child care assistance so I can keep working.",
    ]),
    ("childcare", "childcare/school", [
        "I'm going back to school for nursing and need help paying for my son's daycare.",
        "Can I get child care help while I'm in a job training program?",
    ]),
    ("childcare", "childcare/afterschool", [
        "Is there help paying for after-school care? I work until 6.",
        "My kids need summer care while I work. Is there a program that pays for it?",
    ]),
    ("childcare", "childcare/already-medicaid", [
        "The kids already have Medicaid. What I'm asking about is help with the daycare bill.",
        "We're on SNAP already. I need childcare assistance so I can take a second shift.",
    ]),
    ("energy_assistance", "energy/heat", [
        "Our heating bill is way too high this winter. Is there help paying it?",
        "I need help with my gas bill for heat.",
        "Can I apply for energy assistance? The electric bill doubled.",
    ]),
    ("energy_assistance", "energy/cooling", [
        "It's over 100 degrees and I can't afford to run the AC. Any help with the electric bill?",
        "My mom has asthma and we need the AC. The power bill is behind.",
    ]),
    ("energy_assistance", "energy/propane", [
        "We heat with propane and prices went up a lot. Is there assistance for fuel?",
        "Need help buying heating oil / propane for the winter.",
    ]),
    ("energy_assistance", "energy/spanish", [
        "Hola, la factura de la luz está muy alta. Is there help with the electric bill?",
        "Necesito ayuda con el gas, the heating bill, por favor.",
    ]),
    ("cash_assistance", "cash/monthly", [
        "Is there a program that gives monthly cash help to families? We have nothing coming in for basics.",
        "I need cash assistance for diapers, gas, and bills. Do I qualify for TANF?",
        "How do I apply for the family cash assistance program?",
    ]),
    ("cash_assistance", "cash/single-parent", [
        "I'm a single mom and can't cover the basics. Is there monthly assistance for families?",
        "My husband left and I have no money for bills. I heard there's cash help for families with kids.",
    ]),
    ("cash_assistance", "cash/relative-caregiver", [
        "I'm raising my two grandkids now. Is there financial help for relatives taking care of kids?",
        "My niece is living with me since her mom passed. Can I get cash assistance for her?",
    ]),
    ("cash_assistance", "cash/already-snap", [
        "We have food stamps already but no cash for anything else. What about TANF?",
        "SNAP covers food but I can't pay for school clothes or bus fare. Is there cash assistance?",
    ]),
]

URGENT = {
    "snap": ["There is no food in the house and my kids haven't eaten since yesterday.",
             "We ran out of food two days ago.", "No tenemos comida, the fridge is empty."],
    "medicaid": ["My son has a high fever and trouble breathing and we have no insurance. It's an emergency.",
                 "I'm out of insulin and can't afford a refill.", "I was just discharged from the ER and need my meds today."],
    "unemployment": ["We got an eviction notice because I lost the job, we have to be out by Friday.",
                     "I have $12 in the bank and no food left.", "The power company says they'll shut us off on Monday."],
    "housing": ["The landlord gave us a 3-day eviction notice.", "We have been sleeping in my car since last week.",
                "We have to be out by Friday or the sheriff comes.", "We're homeless right now, staying at a gas station."],
    "childcare": ["If I don't find care by Monday I lose the job and we'll be evicted.",
                  "I got a shutoff notice and daycare is due the same day."],
    "energy_assistance": ["We got a shutoff notice for the 15th.", "The gas was already shut off and it's 20 degrees out.",
                          "The electric company is disconnecting us tomorrow and my mom uses oxygen."],
    "cash_assistance": ["We're about to be evicted and have no money at all.", "We have no food and no money until next month.",
                        "Our lights get shut off Thursday."],
}
CONTEXT = ["Things have been tight lately.", "Just trying to plan ahead.", "We're getting by for now.",
           "Money has been tight since my hours changed.", "Not an emergency, just want to know my options.",
           "I have a job but it doesn't stretch far.", "", "", ""]
NEAR_MISS = ["We had an eviction last year but we're stable in our place now.",
             "I'm worried we might fall behind on rent someday.",
             "No shutoff notice yet, the bill is just high.",
             "My son was in the hospital last spring, he's fine now.",
             "We were homeless a few years ago, we're doing okay now.",
             "Food is tight at the end of the month but we always have something."]


def household(rng, present):
    if present:
        n = rng.randrange(1, 7)
        opts = {1: ["I live alone.", "It's just me.", "household of 1"],
                2: ["It's me and my daughter.", "Two of us in the house.", "me and my husband"],
                3: ["Me and my 2 kids.", "Household of 3.", "me, my wife and our baby"],
                4: ["We're a family of four.", "4 people in the home.", "me, my partner and 2 kids"],
                5: ["There are 5 of us.", "somos 5 en la casa", "household size 5"],
                6: ["Family of six.", "6 people live here.", "me, my mom, and my 4 kids"]}
        return C.pick(rng, opts[n])
    return C.pick(rng, ["", "", "Me and my kids.", "My family.", "It's us and some relatives.", "Full house here."])


def income(rng, present):
    if present:
        amt = rng.randrange(4, 45) * 100
        return C.pick(rng, [f"I make about ${amt:,} a month.", f"Monthly income is ${amt:,}.",
                            f"Our only income is ${min(amt, 1100):,}/mo from SSI.", "We have no income right now, zero.",
                            f"Income: ${amt:,} per month.", f"gano como ${amt:,} al mes",
                            f"take-home is around ${amt:,} monthly"])
    return C.pick(rng, ["", "", "I don't make much.", "Money is tight.", "I work part time.",
                        "My check isn't enough.", "Income varies."])


def county(rng, present):
    if present:
        c = C.pick(rng, COUNTIES)
        return C.pick(rng, [f"I live in {c}.", f"We're in {c}.", f"{C.pick(rng, TOWNS)}, {c}.",
                            f"County: {c}.", f"vivo en {c}"])
    return C.pick(rng, ["", "", f"I live in {C.pick(rng, TOWNS)}.", "We're out in the country.",
                        "I just moved here.", "near the county line"])


def voice(rng, core, facts, hardship):
    """Assemble in one of several voices. Returns text."""
    parts = [p for p in facts if p]
    rng.shuffle(parts)
    body = " ".join([core] + ([hardship] if hardship else []) + parts)
    v = rng.randrange(10)
    name = C.person(rng)
    if v == 0:   # caseworker note
        facts_note = "; ".join(p.rstrip(".") for p in parts) or "no details given"
        return (f"Intake note: client {name} called asking for help. Client states: \"{core}\" "
                f"{('Reports: ' + hardship + ' ') if hardship else ''}Details: {facts_note}.")
    if v == 1:   # voicemail
        return f"Voicemail transcript: hi um this is {C.first_name(rng)}, {body.lower()} please call me back"
    if v == 2:   # helper
        rel, pro = C.pick(rng, [("mom", "she"), ("dad", "he"), ("sister", "she"), ("neighbor", "they"),
                                ("grandfather", "he"), ("aunt", "she")])
        return f"I'm writing for my {rel}, {pro} {'don' if pro == 'they' else 'doesn'}'t use email. " + body
    if v == 3:   # web chat
        return "chat: " + body.replace(". ", "\nchat: ", 2)
    if v == 4:
        return body + " " + C.pick(rng, ["Please help.", "Thank you so much.", "What do I do?", "Gracias.", "pls call back"])
    return C.pick(rng, ["", "Hi, ", "Hello. ", "Good morning, "]) + body


TEST_FAMILIES = ["snap/renewal-cut", "medicaid/pregnancy", "unemployment/claim-issue", "housing/voucher",
                 "childcare/already-medicaid", "energy/propane", "cash/relative-caregiver"]


def build(rng):
    out = []
    for program, fam, templates in CORES:
        for i in range(PER_FAMILY):
            core = templates[i % len(templates)]
            r = rng.random()
            if fam == "housing/shelter":
                hardship, urgent = C.pick(rng, CONTEXT + NEAR_MISS[:2]), True
            elif r < 0.42:
                hardship, urgent = C.pick(rng, URGENT[program]), True
            elif r < 0.62:
                hardship, urgent = C.pick(rng, NEAR_MISS), False
            else:
                hardship, urgent = C.pick(rng, CONTEXT), False
            has = [rng.random() < P_FACT for _ in range(3)]
            facts = [household(rng, has[0]), income(rng, has[1]), county(rng, has[2])]
            text = voice(rng, core, facts, hardship)
            text = C.messy(rng, text, typo_rate=0.04, p_typo=0.45)
            out.append({"family": fam, "group": program, "state": {"message": text},
                        "gold": {"program": program, "urgent_hardship": urgent,
                                 "missing_info": not all(has)}})
    return out


def main():
    rng = C.rng_for(NAME, SEED)
    splits = C.write_dataset(NAME, build(rng), HERE, PREFIX, seed=SEED, test_families=TEST_FAMILIES)
    C.summary(NAME, splits)
    return splits


if __name__ == "__main__":
    main()
