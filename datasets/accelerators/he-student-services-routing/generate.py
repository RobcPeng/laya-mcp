"""Generate the he-student-services-routing accelerator set (deterministic, stdlib only).

Each phrasing family is one hand-written kind of student (or parent) message with fixed gold labels:
the office that handles it, urgency, and whether a staff member must respond personally. Rows add
course codes, dates, and deadlines through slots, then a channel wrapper (student portal form, email
with signature or forwarded cruft, chat/text, parent writing on behalf of a student), optional
Spanish-English code-switching, and a noise pass. TEST holds out whole families.

    python datasets/accelerators/he-student-services-routing/generate.py
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import _common as C  # noqa: E402

NAME = "he-student-services-routing"
PREFIX = "hess"
PER_FAMILY = 17
SEED = 5101

SCHOOLS = ["Pine Valley State University", "Northfield Community College", "Cedar Ridge University",
           "Lakeshore Technical College", "Mesa Verde State College", "Eastbrook University"]

SLOTS = {
    "course": ["BIO 110", "CHEM 121", "MATH 151", "ENG 102", "PSY 200", "HIST 210", "ECON 201", "CS 142",
               "STAT 250", "NURS 301", "SPAN 101", "PHYS 211", "ACCT 210", "COMM 105"],
    "day": ["Friday", "tomorrow", "Monday", "tonight at midnight", "this Thursday", "the 15th", "end of the week"],
    "term": ["fall", "spring", "summer", "next semester", "Fall 2027", "Spring 2027"],
    "amount": ["$150", "$75", "$1,240", "$320", "$2,600", "$45", "$980"],
    "hall": ["Aspen Hall", "Birch Hall", "Summit Towers", "North Quad", "Cedar House", "Maple Commons"],
    "please": ["", "", "Thanks!", "Thank you.", "Please help.", "thx", "Any help is appreciated.",
               "Can someone get back to me?", "Please let me know."],
}

# (office, family, urgency 0-3, needs_human, [templates])
FAMILIES = [
    # ------------------------------------------------------------ registrar
    ("registrar", "reg/transcript-howto", 0, False, [
        "How do I order an official transcript? I need one sent to another school. {please}",
        "where do i request my transcript online and is there a fee",
        "Is it possible to get an electronic transcript instead of a paper one? {please}",
    ]),
    ("registrar", "reg/enroll-verify", 0, False, [
        "I need an enrollment verification letter for my car insurance discount. Where do I get that?",
        "How can I get proof that I'm a full-time student for my parents' health insurance? {please}",
        "My landlord wants a letter showing I'm enrolled for {term}. How do I print one?",
    ]),
    ("registrar", "reg/grade-error", 1, True, [
        "My final grade in {course} shows an F but I finished with a B. My professor said she submitted a grade change two weeks ago and it still isn't fixed. {please}",
        "There's an incomplete on my record for {course} that should have been changed last term. It's messing up my GPA.",
        "{course} is showing up twice on my transcript and one says W. I never withdrew. {please}",
    ]),
    ("registrar", "reg/late-add", 2, True, [
        "The add deadline passed yesterday but my professor approved me joining {course}. The system won't let me add it and I'll lose my full-time status. {please}",
        "I need a late withdrawal from {course} because of a family emergency, the deadline is {day}. Who approves that?",
        "I'm stuck at 9 credits because a class got cancelled and add/drop closes {day}. I need 12 for my scholarship.",
    ]),
    ("registrar", "reg/degree-audit", 1, True, [
        "My degree audit says I'm missing a humanities credit but I took {course} and it counted for my friend. Can someone review it?",
        "I applied to graduate in {term} and the audit says I'm 2 credits short. I think my transfer class didn't get applied.",
    ]),
    # ------------------------------------------------------------ financial aid
    ("financial_aid", "fa/fafsa-howto", 0, False, [
        "Do I have to fill out the FAFSA every year or just once?",
        "what's the school code for the fafsa",
        "When does the FAFSA open for {term}? {please}",
    ]),
    ("financial_aid", "fa/status-docs", 1, True, [
        "I uploaded my verification documents two weeks ago and my aid still says pending. Did you receive them? {please}",
        "My portal says I have an outstanding requirement for financial aid but it doesn't say what. Can someone check?",
        "Why did my Pell grant go down this semester? Nothing changed with my family.",
    ]),
    ("financial_aid", "fa/aid-cancelled", 2, True, [
        "My financial aid was cancelled and I have no idea why. Classes start {day} and I can't pay without it.",
        "I got an email that I lost my aid because of my GPA. I need to appeal before {day} or I get dropped. {please}",
    ]),
    ("financial_aid", "fa/workstudy-howto", 0, False, [
        "How do I find a work-study job on campus?",
        "i'm broke lol how do i get a campus job with my work study award",
    ]),
    # ------------------------------------------------------------ student accounts
    ("student_accounts", "sa/charge-question", 1, True, [
        "Why was I charged a {amount} late fee? I paid on time. {please}",
        "There's a {amount} charge on my bill labeled 'misc fee' and nobody can tell me what it is.",
        "I was billed for a meal plan I cancelled in August. Can you remove the {amount} charge?",
    ]),
    ("student_accounts", "sa/payment-plan-howto", 0, False, [
        "How do payment plans work? Can I split tuition into monthly payments?",
        "What payment methods do you accept for tuition? {please}",
        "Where can I see my bill and add my mom as an authorized payer?",
    ]),
    ("student_accounts", "sa/drop-for-nonpayment", 2, True, [
        "I got a notice that I'll be dropped from all my classes {day} for nonpayment. My aid hasn't paid yet. Please help!",
        "There's a hold on my account for a {amount} balance and I can't register, registration closes {day}.",
    ]),
    ("student_accounts", "sa/refund-when", 0, False, [
        "When do refund checks come out this semester?",
        "How do I set up direct deposit for my refund? {please}",
    ]),
    # ------------------------------------------------------------ admissions
    ("admissions", "adm/transfer-howto", 0, False, [
        "How do I apply as a transfer student from a community college?",
        "What's the application deadline for transfer students for {term}? {please}",
    ]),
    ("admissions", "adm/decision-status", 1, True, [
        "I applied in March and still haven't heard anything. My portal just says 'in review'. {please}",
        "My application says I'm missing my high school transcript but my counselor sent it weeks ago.",
    ]),
    ("admissions", "adm/readmit", 1, True, [
        "I stopped out for two years for work and want to come back in {term}. Do I reapply or is there a readmission form?",
        "I was academically dismissed a while ago and want to return. What do I need to do to be readmitted?",
    ]),
    # ------------------------------------------------------------ housing
    ("housing", "h/roommate", 1, True, [
        "My roommate has people over every night until 3am and won't talk about it. I want to switch rooms. {please}",
        "I don't feel comfortable with my roommate anymore, we had a big fight. Can I move to a different room in {hall}?",
    ]),
    ("housing", "h/maintenance", 1, False, [
        "The heat in my room in {hall} isn't working. How do I put in a maintenance request?",
        "Our shower drain in {hall} is clogged again. Where do I report it?",
    ]),
    ("housing", "h/room-emergency", 3, True, [
        "Water is pouring through the ceiling of my room in {hall} and the outlet by it is sparking. What do I do??",
        "There's a strong burning smell and smoke coming from the vent in my room in {hall}, the alarm isn't going off.",
    ]),
    ("housing", "h/nowhere-to-stay", 2, True, [
        "The halls close for break {day} and I have nowhere to go. I can't go home. Is there any break housing? {please}",
        "My housing got cancelled because of a paperwork thing and I have to move out {day}. I'll be homeless.",
    ]),
    ("housing", "h/meal-plan", 0, False, [
        "Can I change my meal plan to a smaller one next semester?",
        "How many meal swipes carry over to next week? {please}",
    ]),
    # ------------------------------------------------------------ IT
    ("it_help", "it/password", 1, False, [
        "I forgot my campus password and can't log in to anything. How do I reset it?",
        "my student email password expired how do i change it",
        "I got a new phone and my MFA app isn't set up on it. How do I re-enroll?",
    ]),
    ("it_help", "it/locked-before-exam", 2, True, [
        "I'm locked out of the LMS and my {course} exam closes {day}. I already tried the reset link three times.",
        "My account got disabled and I can't submit my final project for {course}, it's due {day}. {please}",
    ]),
    ("it_help", "it/wifi-email-setup", 0, False, [
        "How do I connect my Xbox to the campus wifi?",
        "How do I set up my student email on my phone? {please}",
        "Can I get the Office apps for free as a student?",
    ]),
    # ------------------------------------------------------------ advising
    ("advising", "adv/course-plan", 1, True, [
        "I'm not sure which classes to take next semester for the nursing track. Can I meet with someone? {please}",
        "Should I take {course} or wait until I finish the prerequisite? I don't want to fall behind.",
    ]),
    ("advising", "adv/change-major", 1, True, [
        "I want to switch from biology to computer science. How many credits would transfer over and who do I talk to?",
        "I'm thinking about adding a minor in Spanish. Would I still graduate on time?",
    ]),
    ("advising", "adv/probation", 2, True, [
        "I got a letter saying I'm on academic probation and have to meet with an advisor before registration opens {day}. {please}",
        "I'm failing two classes and don't know if I should withdraw before {day}. I need to talk to someone.",
    ]),
    ("advising", "adv/appointment-howto", 0, False, [
        "How do I find out who my advisor is?",
        "Where do I book an advising appointment online? {please}",
    ]),
    # ------------------------------------------------------------ accessibility
    ("accessibility", "acc/new-accommodation", 1, True, [
        "I was diagnosed with ADHD over the summer and want to ask for extended test time. How do I start?",
        "I have a hearing impairment and need captions for my online lectures in {course}. {please}",
    ]),
    ("accessibility", "acc/letter-not-sent", 2, True, [
        "My accommodation letter never got sent to my {course} professor and the exam is {day}. {please}",
        "The testing center says they don't have my extended time on file and my midterm is {day}.",
    ]),
    ("accessibility", "acc/howto", 0, False, [
        "What documentation do I need to register with disability services?",
        "Do accommodations carry over from high school or do I have to reapply here?",
    ]),
    # ------------------------------------------------------------ counseling
    ("counseling", "c/howto", 0, False, [
        "How do I make an appointment at the counseling center? Is it free?",
        "Does the counseling center do telehealth sessions? {please}",
    ]),
    ("counseling", "c/struggling", 1, True, [
        "I've been really overwhelmed and anxious for weeks and can't focus on anything. Can I talk to someone?",
        "Since my grandma passed I haven't been sleeping and I'm falling apart. Is there someone I can see?",
    ]),
    ("counseling", "c/crisis", 3, True, [
        "I don't want to be here anymore. I've been thinking about ending it and I don't know who else to tell.",
        "I can't do this anymore. I have a plan to hurt myself tonight.",
    ]),
    ("counseling", "c/friend-danger", 3, True, [
        "My roommate took a bunch of pills and now she won't wake up. What do I do??",
        "My friend just texted me goodbye and said he's going to kill himself. He isn't answering. {please}",
    ]),
    # ------------------------------------------------------------ library
    ("library", "lib/hours-rooms", 0, False, [
        "What are the library hours during finals week?",
        "How do I reserve a group study room? {please}",
        "Can I print in color at the library?",
    ]),
    ("library", "lib/fine-dispute", 1, True, [
        "I was charged {amount} for a book I returned in October. I have the receipt. {please}",
        "My library account says I have a lost laptop charger fine but I never checked one out.",
    ]),
    ("library", "lib/research-help", 1, True, [
        "Can a librarian help me find peer-reviewed sources for my {course} research paper? It's a weird topic.",
        "I'm starting my thesis and need help with a literature search. Can I set up a consultation?",
    ]),
    ("library", "lib/ill-howto", 0, False, [
        "How do I request a book through interlibrary loan?",
        "Does the library have {course} textbooks on reserve? {please}",
    ]),
    # ------------------------------------------------------------ other
    ("other", "o/parking-citation", 1, True, [
        "I got a {amount} parking ticket but I had a valid permit on my dash. How do I appeal?",
        "My car got towed from the commuter lot even though I had a permit. {please}",
    ]),
    ("other", "o/parking-permit", 0, False, [
        "How much is a commuter parking permit for {term}?",
        "Where do I buy a parking pass? {please}",
    ]),
    ("other", "o/clubs-dining", 0, False, [
        "How do I start a new student club?",
        "Are there vegan options in the dining hall?",
        "How do I sign up for intramural soccer? {please}",
    ]),
    # ------------------------------------------------------------ near misses: dramatic words, ordinary need
    ("registrar", "nm/killing-me", 1, False, [
        "{course} is literally killing me lol, how do I drop it before the deadline?",
        "this class is going to be the death of me. what's the last day to withdraw from {course}?",
    ]),
    ("registrar", "nm/dying-to-get-in", 1, False, [
        "I'm dying to get into {course} but it's full. Is there a waitlist? {please}",
        "I would literally die for a seat in {course} lol. how does the waitlist work",
    ]),
    ("it_help", "nm/laptop-died", 1, True, [
        "My laptop died completely and all my {course} work is on it. Does IT loan laptops or recover files?",
        "Laptop just crashed and won't turn on. Can IT look at it or give me a loaner?",
    ]),
    ("housing", "nm/fire-alarm", 1, True, [
        "The fire alarm in {hall} went off at 3am again for the third time this week (no fire). Can someone look into it?",
        "Someone keeps burning popcorn and setting off the alarm in {hall}. Nobody is hurt, we're just exhausted.",
    ]),
    ("counseling", "nm/stressed-finals", 1, True, [
        "Finals are crushing me and I'm super stressed. Does the counseling center have walk-in hours this week?",
        "I'm dead tired and stressed about exams, can I get a quick session with someone? not an emergency.",
    ]),
]

TEST_FAMILIES = ["reg/grade-error", "fa/aid-cancelled", "sa/refund-when", "adm/readmit", "h/room-emergency",
                 "it/wifi-email-setup", "adv/probation", "acc/howto", "c/friend-danger", "lib/research-help",
                 "o/parking-citation", "nm/dying-to-get-in", "nm/stressed-finals"]

OPENERS = ["", "", "", "Hi, ", "Hello, ", "Hey, ", "Good morning, ", "Hi there! ", "Quick question: ",
           "Sorry to bother you, ", "To whom it may concern, "]
SPANISH_OPEN = ["Hola, ", "Hola buenas, ", "Buenas tardes, "]
SPANISH_CLOSE = [" Gracias!", " Muchas gracias.", " Gracias de antemano.", " Por favor ayuda."]
FILLERS = ["", "", "", "", " I'm a first-gen student so I don't really know how this works.",
           " I already called and was on hold forever.", " I'm a sophomore.", " I'm a transfer student.",
           " Sorry if this is the wrong office.", " My advisor told me to email you."]


def student_id(rng):
    return f"S{rng.randrange(0, 100000000):08d}"


def wrap(rng, text):
    kind = rng.random()
    name = C.person(rng)
    if kind < 0.25:     # portal form
        topic = C.pick(rng, ["General", "Question", "Help", "Other", "Account"])
        return (f"Topic: {topic}\nStudent ID: {student_id(rng)}\nCampus: {C.pick(rng, SCHOOLS)}\n"
                f"Message: {text}")
    if kind < 0.45:     # email
        sig = C.pick(rng, [f"\n\n{name}\n{student_id(rng)}", f"\n\nThanks,\n{C.first_name(rng)}",
                           "\n\nSent from my iPhone", f"\n\n{name} | Class of 2028"])
        out = f"Subject: {C.pick(rng, ['Question', 'Help', 'urgent', 'Re: your account', '(no subject)'])}\n\n{text}{sig}"
        if rng.random() < 0.25:
            out = (f"---------- Forwarded message ---------\nFrom: {C.email(rng, name, 'example.edu')}\n"
                   f"To: helpdesk@example.edu\n\n" + out)
        return out
    if kind < 0.6:      # parent on behalf
        who = C.pick(rng, ["my daughter", "my son", "my kid", "my stepson"])
        intro = C.pick(rng, [f"Hello, I'm writing on behalf of {who}, who is a student there. {who.capitalize()} wrote this: ",
                             f"Parent here. Forwarding what {who} sent me: ",
                             f"My name is {name}, a parent. {who.capitalize()} asked me to send this: "])
        return intro + '"' + text + '"'
    if kind < 0.85:     # chat / text
        return text.lower().replace(". ", " ").rstrip(".")
    return text


def build(rng):
    examples = []
    for office, fam, urgency, human, templates in FAMILIES:
        for i in range(PER_FAMILY):
            text = C.fill(rng, templates[i % len(templates)], SLOTS)
            if urgency == 3:        # crisis messages: no small-talk openers or filler
                opener, filler = C.pick(rng, ["", "", "", "Hi, "]), ""
            else:
                opener, filler = C.pick(rng, OPENERS), C.pick(rng, FILLERS)
            if opener and not text.startswith("I "):
                text = text[0].lower() + text[1:]
            text = opener + text + filler
            if urgency < 3 and rng.random() < 0.1:
                text = C.pick(rng, SPANISH_OPEN) + text + C.pick(rng, SPANISH_CLOSE)
            text = C.messy(rng, text, typo_rate=0.04, p_typo=0.4)
            examples.append({
                "family": fam, "group": office,
                "state": {"message": wrap(rng, text)},
                "gold": {"office": office, "urgency": urgency, "needs_human": human},
            })
    return examples


def main():
    rng = C.rng_for(NAME, SEED)
    splits = C.write_dataset(NAME, build(rng), HERE, PREFIX, seed=SEED, test_families=TEST_FAMILIES)
    C.summary(NAME, splits)
    return splits


if __name__ == "__main__":
    main()
