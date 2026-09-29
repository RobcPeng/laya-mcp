"""Generate the he-research-admin accelerator set (deterministic, stdlib only).

Each phrasing family is one kind of sponsored-research email (proposal routing, a rate question, a
subaward invoice, an IRB amendment, effort certification, a new award notice, closeout) with a fixed
topic label. Every template has a {dl} slot that the generator fills with either an upcoming deadline
(deadline = true) or with nothing, "no rush", or a date that has already passed (deadline = false), so
the deadline label is independent of the topic. "Main topic" families mix two topics in one email; the
label is the thing the sender asks the recipient to act on. Emails get headers, signatures, and
sometimes a forwarded or quoted earlier message. TEST holds out whole families.

    python datasets/accelerators/he-research-admin/generate.py
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import _common as C  # noqa: E402

NAME = "he-research-admin"
PREFIX = "hera"
PER_FAMILY = 26
SEED = 5150

SPONSORS = ["a federal science agency", "the Aldercrest Foundation", "the Office of Regional Research",
            "the Halvorsen Foundation", "a state department of transportation", "the Ridgeline Health Trust",
            "a federal health research agency", "the Brightwater Energy Institute"]
PARTNERS = ["Northridge State University", "Lakeshore College", "Pinecrest Institute of Technology",
            "Eastvale Medical Center", "Coronado University", "Summit Tribal College"]
DEPTS = ["Biology", "Civil Engineering", "Psychology", "Chemistry", "Public Health", "Education",
         "Computer Science", "Anthropology", "Nursing", "Physics"]

FUTURE = ["this Friday", "next Tuesday", "November 14", "the 15th of next month", "end of next week",
          "tomorrow at 5pm", "Monday", "in ten days", "December 1", "the 30th"]
PAST = ["last Friday", "on March 3", "last month", "two weeks ago", "back in June"]

DL_TRUE = [
    "The sponsor deadline is {fut}.",
    "Our internal routing deadline is {fut}, five business days before the sponsor's due date.",
    "We need this back by {fut}.",
    "This is due to the sponsor {fut}.",
    "Please respond by {fut} so we don't miss the sponsor's due date.",
    "Hard deadline: {fut}.",
    "Can you get this to me before {fut}? That's the cutoff.",
]
DL_FALSE = [
    "", "", "", "No rush on this.", "Whenever you get a chance.", "Not time-sensitive.",
    "The last deadline on this passed {past}; nothing is due right now.",
    "We missed the {past} cutoff, so there's no deadline pressure on this anymore.",
    "There's no sponsor deadline attached to this one.",
]

SLOTS = {
    "sponsor": SPONSORS, "partner": PARTNERS, "dept": DEPTS,
    "award": lambda r: f"{C.pick(r, ['AWD', 'GR', 'SP'])}-{r.randrange(10000, 99999)}",
    "amt": lambda r: f"${r.randrange(20, 900) * 1000:,}",
    "small": lambda r: f"${r.randrange(80, 9000):,}",
    "pct": lambda r: f"{r.randrange(5, 50)}%",
    "rate": ["52%", "55.5%", "48%", "10% de minimis", "26% off-campus"],
    "protocol": lambda r: f"{C.pick(r, ['IRB', 'Protocol'])} #{r.randrange(2024, 2027)}-{r.randrange(100, 999)}",
    "item": ["a laptop", "conference registration", "participant gift cards", "a lab freezer", "catering for a "
             "workshop", "cloud computing credits", "a field vehicle rental", "journal publication fees"],
    "fut": FUTURE, "past": PAST,
}

# (topic, family, [templates]); every template contains {dl}
FAMILIES = [
    # ---------------------------------------------------------------- proposal
    ("proposal", "proposal/new-submission", [
        "Hi, I'm planning to submit a proposal to {sponsor} for about {amt} over three years. What do you need from me to get it routed? {dl}",
        "Attached is my draft narrative and biosketch for the {sponsor} solicitation. Can you start the proposal package? {dl}",
        "First time applying to {sponsor}. Who in the sponsored programs office helps with the application package? {dl}",
    ]),
    ("proposal", "proposal/routing-signatures", [
        "The proposal is in the routing system but the department chair hasn't signed off yet. Can you nudge them? {dl}",
        "Co-PI from {dept} still needs to certify in the routing form before you can submit. {dl}",
    ]),
    ("proposal", "proposal/limited-submission", [
        "Is the {sponsor} program a limited submission? Two of us in {dept} want to apply. {dl}",
        "We got an internal notice about a limited-submission competition for {sponsor}. How do I submit a pre-proposal? {dl}",
    ]),
    ("proposal", "proposal/resubmission", [
        "Our proposal to {sponsor} was declined but reviewers encouraged resubmission. What's the process to resubmit? {dl}",
        "Revising last cycle's application for {sponsor}; do I need to reroute the whole thing? {dl}",
    ]),
    ("proposal", "proposal/with-budget-question", [
        "Getting my {sponsor} proposal ready to submit. Quick side question on the budget: should I use {rate} F&A? Mainly I need you to submit it. {dl}",
        "Please submit the attached application to {sponsor}. I also wasn't sure if {item} is allowed in the budget, but the submission is the priority. {dl}",
    ]),
    # ---------------------------------------------------------------- budget
    ("budget", "budget/rate-question", [
        "What F&A rate should I use for an off-campus project funded by {sponsor}? Is it {rate}? {dl}",
        "Does {sponsor} cap indirect costs? I've been told {rate} but can't find it. {dl}",
        "What fringe rate applies to a summer salary for faculty? Building my budget now. {dl}",
    ]),
    ("budget", "budget/allowability", [
        "Is {item} an allowable cost on my {sponsor} award {award}? {dl}",
        "Can I charge {item} to the grant? It's for the project but the PI isn't sure it's allowable. {dl}",
    ]),
    ("budget", "budget/rebudget", [
        "I need to move {small} from travel to participant support on {award}. Does that need sponsor approval? {dl}",
        "We underspent on equipment for {award}; can we rebudget into a postdoc's salary? {dl}",
    ]),
    ("budget", "budget/cost-transfer", [
        "A {small} charge for {item} hit the wrong grant. How do I do a cost transfer to {award}? {dl}",
        "The department accidentally charged my postdoc to the wrong account for three months. Need a cost transfer. {dl}",
    ]),
    # ---------------------------------------------------------------- subaward
    ("subaward", "subaward/outgoing-new", [
        "We're sending part of the work to {partner}. Can you issue the subaward agreement under {award}? {dl}",
        "Please start a subcontract to {partner} for {amt}; their scope of work and budget are attached. {dl}",
    ]),
    ("subaward", "subaward/invoice-monitoring", [
        "{partner} sent their quarterly invoice for the subaward on {award}. PI needs to approve it; who reviews? {dl}",
        "The subrecipient's invoice is missing backup documentation. Should we hold payment? {dl}",
        "Annual subrecipient monitoring questionnaire for {partner} came back incomplete. {dl}",
    ]),
    ("subaward", "subaward/incoming", [
        "{partner} is the prime on a {sponsor} award and wants to send us a subaward. Who signs on our side? {dl}",
        "We received a draft subaward from {partner}. The terms include a clause on IP we don't normally accept. {dl}",
    ]),
    # ---------------------------------------------------------------- compliance
    ("compliance", "compliance/irb", [
        "My study needs an IRB amendment to add a new survey. Protocol {protocol}. {dl}",
        "Does a secondary analysis of de-identified data need IRB review? {dl}",
        "How do I submit the IRB continuing review for {protocol}? {dl}",
    ]),
    ("compliance", "compliance/iacuc", [
        "We need to add two personnel to our animal use protocol with the IACUC. {dl}",
        "Our IACUC protocol for the mouse colony needs a renewal; paperwork question. {dl}",
    ]),
    ("compliance", "compliance/coi", [
        "I started consulting for a startup in my field. Do I need to update my conflict of interest disclosure? {dl}",
        "Annual COI disclosure: my spouse holds equity in a company related to my {sponsor} project. {dl}",
    ]),
    ("compliance", "compliance/export-security", [
        "A visiting researcher from abroad wants access to our lab's equipment. Is there an export control review? {dl}",
        "We're shipping a sensor prototype to a collaborator overseas. Does that need an export license check? {dl}",
        "The sponsor added new research security training requirements. Who tracks completion? {dl}",
    ]),
    # ---------------------------------------------------------------- effort
    ("effort", "effort/certification", [
        "Reminder: your effort certification for the spring period is open in the effort system. {dl}",
        "I have three effort reports waiting for my certification and I'm not sure the percentages are right. {dl}",
    ]),
    ("effort", "effort/correction", [
        "My effort report shows {pct} on {award}, but I actually spent about half that. How do I correct it? {dl}",
        "The postdoc's effort was split wrong between two grants last period. Need to fix the certification. {dl}",
    ]),
    ("effort", "effort/commitment", [
        "I committed {pct} effort in the proposal but now I'm teaching more. Does reducing effort need sponsor approval? {dl}",
        "Key personnel effort is dropping below the committed level on {award}. What do we report? {dl}",
    ]),
    # ---------------------------------------------------------------- award setup
    ("award_setup", "award_setup/noa", [
        "We received the notice of award from {sponsor} for {amt}! What happens next to get an account set up? {dl}",
        "Forwarding the award notice for {award}. Please set up the project account so we can hire. {dl}",
    ]),
    ("award_setup", "award_setup/advance-account", [
        "Award is expected but not signed yet; can we get an advance account to start charging? {dl}",
        "Can you set up an at-risk account for the {sponsor} project while the agreement is finalized? {dl}",
    ]),
    ("award_setup", "award_setup/terms", [
        "The award terms from {sponsor} include a publication review clause. Is that acceptable? {dl}",
        "Our new award has a reporting schedule I don't understand. Can someone walk me through the terms? {dl}",
    ]),
    # ---------------------------------------------------------------- closeout
    ("closeout", "closeout/final-reports", [
        "{award} is wrapping up. What final reports do I owe {sponsor}? {dl}",
        "Final technical report for {award}: do I submit it or does your office? {dl}",
    ]),
    ("closeout", "closeout/final-invoice", [
        "We need to reconcile all charges on {award} before the final invoice goes to {sponsor}. {dl}",
        "Please don't post any more charges to {award}; we're preparing the final financial report. {dl}",
    ]),
    ("closeout", "closeout/residual", [
        "There's a {small} residual balance on a fixed-price agreement that ended. What happens to it at closeout? {dl}",
        "Closing out {award} and there's an overdraft of {small}. Where does that go? {dl}",
    ]),
    ("closeout", "closeout/effort-mentioned", [
        "Closing out {award}: final reports are drafted; the only thing left is my last effort certification, then please close it. {dl}",
        "For the closeout of {award}, everything is reconciled except one effort report. Can you finish the closeout package? {dl}",
    ]),
    # ---------------------------------------------------------------- other
    ("other", "other/training", [
        "Is there a workshop for new PIs on grant management this semester? {dl}",
        "Can your office present to our {dept} faculty meeting about funding opportunities? {dl}",
    ]),
    ("other", "other/misc", [
        "Who should I talk to about office space for a visiting scholar in {dept}? {dl}",
        "Do you have a template for a letter of collaboration? Not for a specific proposal yet. {dl}",
        "Please update my mailing address in the research administration directory. {dl}",
    ]),
    ("other", "other/newsletter", [
        "Sponsored programs monthly update: new staff, office hours, and a reminder that our office moves to {dept} building next month. {dl}",
        "FYI - the research office holiday closure schedule is posted on the intranet. {dl}",
    ]),
]

TEST_FAMILIES = ["proposal/resubmission", "budget/cost-transfer", "subaward/incoming", "compliance/iacuc",
                 "effort/commitment", "award_setup/terms", "closeout/effort-mentioned", "other/newsletter"]

ROLES = [("PI", lambda r, n: f"Dr. {n}\nAssociate Professor, {C.pick(r, DEPTS)}"),
         ("department admin", lambda r, n: f"{n}\nGrants Administrator, {C.pick(r, DEPTS)}"),
         ("grant officer", lambda r, n: f"{n}\nOffice of Sponsored Programs"),
         ("subrecipient", lambda r, n: f"{n}\nResearch Office, {C.pick(r, PARTNERS)}"),
         ("postdoc", lambda r, n: f"{n}\nPostdoctoral Fellow")]


def wrap(rng, body):
    name = C.person(rng)
    _, sig = C.pick(rng, ROLES)
    subj = C.pick(rng, ["Question", "Re: grant", "help needed", "Award question", "FW: request", "quick q",
                        "Sponsored research", "Re: Re: follow up"])
    signature = C.pick(rng, [f"\n\n{sig(rng, name)}", f"\n\nThanks,\n{name.split()[0]}", "\n\nSent from my phone",
                             f"\n\nBest,\n{name}"])
    text = f"From: {C.email(rng, name, 'example.edu')}\nSubject: {subj}\n\n{body}{signature}"
    r = rng.random()
    if r < 0.15:
        other = C.person(rng)
        text = (f"---------- Forwarded message ----------\nFrom: {C.email(rng, other, 'example.edu')}\n\n"
                + text + "\n\nCan you take a look? -" + other.split()[0])
    elif r < 0.25:
        text += "\n\n> On " + C.pick(rng, ["Mon", "Tue", "Wed", "Thu"]) + ", the research office wrote:\n> Thanks for reaching out, can you send more details?"
    return text


def build(rng):
    examples = []
    for topic, fam, tpls in FAMILIES:
        for i in range(PER_FAMILY):
            has_dl = rng.random() < 0.5
            dl = C.fill(rng, C.pick(rng, DL_TRUE if has_dl else DL_FALSE), SLOTS)
            body = C.fill(rng, tpls[i % len(tpls)].replace("{dl}", "\x00"), SLOTS).replace("\x00", dl)
            body = C.messy(rng, body, typo_rate=0.03, p_typo=0.35)
            examples.append({"family": fam, "group": topic, "state": {"email": wrap(rng, body)},
                             "gold": {"topic": topic, "deadline": has_dl}})
    return examples


def main():
    rng = C.rng_for(NAME, SEED)
    splits = C.write_dataset(NAME, build(rng), HERE, PREFIX, seed=SEED, test_families=TEST_FAMILIES)
    C.summary(NAME, splits)
    return splits


if __name__ == "__main__":
    main()
