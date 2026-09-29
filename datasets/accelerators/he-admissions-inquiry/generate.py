"""Generate the he-admissions-inquiry accelerator set (deterministic, stdlib only).

Compositional: each row = a stage cue (who is writing and where they are in the funnel) + a topic
question written for that stage + an optional intent cue, then a channel wrapper (inquiry form,
email, text/chat, parent writing) and noise.

  stage   comes from the stage cue (prospect, applicant, admitted, deposited, other).
  topic   comes from the topic question.
  hot_lead is true only when an intent cue is present: a specific term to apply or start, a request
          to book a visit or a dated visit, or asking for next steps to apply or commit. Deposited
          students are already committed and third parties (counselors, current students, alumni,
          vendors) are not leads, so both are always false. Browsing hedges ("maybe someday") are
          added as hard negatives.

Family = topic/stage. TEST holds out one topic/stage combination per topic, and test rows may also
draw stage cues from a held-out pool that train never sees.

    python datasets/accelerators/he-admissions-inquiry/generate.py
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import _common as C  # noqa: E402

NAME = "he-admissions-inquiry"
PREFIX = "headm"
PER_FAMILY = 28
SEED = 5303

SCHOOLS = ["Pine Valley State University", "Northfield Community College", "Cedar Ridge University",
           "Lakeshore Technical College", "Mesa Verde State College", "Eastbrook University"]

# stage -> (train cues, extra cues used only in held-out test rows)
STAGE_CUES = {
    "prospect": ([
        "I'm a junior in high school and just starting to look at colleges.",
        "I'm a high school senior thinking about applying.",
        "I'm at Northfield Community College right now and thinking about transferring.",
        "I'm an adult learner and thinking about going back to school.",
        "I'm in grade 12 abroad and looking at universities in the US.",
    ], [
        "My daughter is a sophomore in high school and we're starting our college search.",
        "I haven't applied yet but your school is on my list.",
    ]),
    "applicant": ([
        "I submitted my application on November 1.",
        "I applied early action last month.",
        "My application went in two weeks ago.",
        "I applied as a transfer student in February.",
    ], [
        "My son applied in December and we're waiting to hear back.",
        "Just hit submit on my app last week!",
    ]),
    "admitted": ([
        "I was just admitted and I'm so excited!",
        "I got my acceptance letter yesterday.",
        "I was admitted for fall but haven't decided where I'm going yet.",
        "I got into the nursing program.",
    ], [
        "My daughter was accepted last week and is comparing offers.",
        "My congrats letter came today!",
    ]),
    "deposited": ([
        "I already paid my enrollment deposit.",
        "I committed last week and paid the deposit.",
        "I'm an incoming first-year and my deposit is paid.",
    ], [
        "We paid our son's enrollment deposit in April.",
        "I accepted my spot and paid the $200 deposit.",
    ]),
    "other": ([
        "I'm a school counselor at Ridgeview High.",
        "I'm a current junior at the university.",
        "I graduated from here in 2015.",
        "I work for a test prep company.",
    ], [
        "I'm a transfer advisor at a community college.",
        "I'm an alum and my niece is looking at schools.",
    ]),
}

# topic -> bucket -> templates. Buckets: pre (prospect/applicant), app (applicant only),
# post (admitted/deposited), third (other).
TOPIC_Q = {
    "application_status": {
        "app": ["Can you tell me if my application is complete?", "When will I get a decision?",
                "The portal says my transcript is missing but my school sent it. Can you check?",
                "Is there any way to see where my application is in the review?"],
        "third": ["Can you confirm whether my student's application is complete? She's worried.",
                  "Several of our seniors are still waiting on decisions. When are they going out?"],
    },
    "requirements": {
        "pre": ["What GPA do I need to get in?", "How many letters of recommendation do you require?",
                "Is there an essay for the honors college?", "Do I need two years of a foreign language to be admitted?"],
        "post": ["Do I need to send my final high school transcript, and by when?",
                 "What documents do I still need to submit now that I'm in?"],
        "third": ["What are your minimum course requirements for first-year applicants? I'm updating our guide.",
                  "Do you accept homeschool transcripts, and what do they need to include?"],
    },
    "transfer_credit": {
        "pre": ["Will my credits from community college transfer?", "Do you take AP credit for a 3 on Calculus AB?",
                "How do I know which of my 45 credits will count toward a business degree?"],
        "post": ["When will I see my transfer credit evaluation?", "My English 101 from my old school didn't transfer. Who can review it?"],
        "third": ["I'm a current student taking a summer class at another college. Will it transfer back?",
                  "Is there an articulation agreement for our associate degree students?"],
    },
    "international": {
        "pre": ["What TOEFL or IELTS score do international applicants need?", "Do international students need to show proof of funds to apply?",
                "Can international students apply test-optional?"],
        "post": ["When will my I-20 be issued? I need it for my visa appointment.",
                 "My visa interview is scheduled. What documents from you do I need to bring?"],
        "third": ["Do you partner with international recruitment agencies? We'd like to work with you."],
    },
    "test_policy": {
        "pre": ["Are you test-optional this year?", "Should I send my SAT score if it's below your average?",
                "Do you superscore the ACT?", "Is the SAT required for the engineering program?"],
        "third": ["Our school is test-optional-heavy. Do you still recommend students submit scores?",
                  "Do you accept self-reported test scores from our students?"],
    },
    "campus_visit": {
        "pre": ["Do you offer virtual tours?", "Are campus tours available on weekends?", "Where do visitors park for tours?",
                "Can I sit in on a class when I visit?"],
        "post": ["Is Admitted Student Day in person this year?", "Can I stay overnight in a residence hall before I decide?"],
        "third": ["Can I bring a group of 30 juniors for a tour this fall?", "Do you host counselor fly-in programs?"],
    },
    "cost_aid": {
        "pre": ["How much is tuition for out-of-state students?", "Do you give merit scholarships automatically?",
                "What's the total cost of attendance with housing?", "Is there a net price calculator?"],
        "post": ["My aid package seems low. Can it be reviewed before I decide?",
                 "When is the tuition bill due for fall and are there payment plans?"],
        "third": ["Our families ask about average aid packages. Do you publish that?", "Do you offer scholarships for dual-enrollment students?"],
    },
}
STAGE_BUCKETS = {"prospect": ["pre"], "applicant": ["pre", "app"], "admitted": ["post"], "deposited": ["post"],
                 "other": ["third"]}

INTENT = {
    "prospect": ["I'm planning to apply for Fall 2027.", "I'd like to schedule a campus visit on October 12.",
                 "I'm ready to apply this week. What are the next steps?", "I want to start in January 2027 if I can.",
                 "Can I book a tour for next Saturday?"],
    "applicant": ["I really want to start this fall.", "Can I come for a tour on Saturday the 18th?",
                  "You're my first choice and I'm ready to enroll as soon as I hear back.",
                  "I'd like to set up a visit next week."],
    "admitted": ["What are the next steps to accept my offer?", "How do I pay my deposit? I've decided!",
                 "I want to register for Admitted Student Day on April 5.", "I'm ready to commit. What do I sign?",
                 "Can I book a tour for the week of March 9 before I sign?"],
}
HEDGES = ["Maybe someday I'll apply, just curious.", "I'm not sure I'll apply, just browsing.",
          "Not ready to commit to anything yet.", "Honestly you're not my first choice, just gathering info.",
          "My cousin might visit sometime, no plans yet."]

TEST_FAMILIES = ["application_status/other", "requirements/admitted", "transfer_credit/prospect",
                 "international/deposited", "test_policy/applicant", "campus_visit/admitted", "cost_aid/deposited"]

OPENERS = ["", "", "", "Hi! ", "Hello, ", "Good morning. ", "Hey there, ", "Hi Admissions, ", "Dear Admissions Office, "]
SPANISH = [("Hola! ", " Gracias!"), ("", " Mis papás hablan español, ¿tienen información en español?"),
           ("Buenos días. ", " Muchas gracias.")]


def wrap(rng, text):
    name = C.person(rng)
    k = rng.random()
    if k < 0.3:
        return (f"Request for Information form\nName: {name}\nEmail: {C.email(rng, name)}\n"
                f"Intended major: {C.pick(rng, ['Nursing', 'Undecided', 'Business', 'Computer Science', 'Biology', 'Education'])}\n"
                f"School: {C.pick(rng, SCHOOLS)}\nComments: {text}")
    if k < 0.55:
        sig = C.pick(rng, [f"\n\n{name}", f"\n\nBest,\n{name}", "\n\nSent from my iPhone", f"\n\n{name}\n{C.phone(rng)}"])
        out = f"Subject: {C.pick(rng, ['Question', 'Admissions question', 'Hi!', 'Inquiry', 'application'])}\n\n{text}{sig}"
        if rng.random() < 0.2:
            out = "---------- Forwarded message ---------\nFrom: " + C.email(rng, name) + "\n\n" + out
        return out
    if k < 0.8:
        return text.lower().replace(". ", " ").rstrip(".")
    return text


def build(rng):
    examples = []
    for topic, buckets in TOPIC_Q.items():
        for stage, allowed in STAGE_BUCKETS.items():
            templates = [t for b in allowed for t in buckets.get(b, [])]
            if not templates:
                continue
            fam = f"{topic}/{stage}"
            held = fam in TEST_FAMILIES
            train_cues, test_cues = STAGE_CUES[stage]
            cues = train_cues + test_cues if held else train_cues
            n = PER_FAMILY * (2 if topic in ("application_status", "test_policy") else 1)
            for i in range(n):
                parts = [C.pick(rng, cues), templates[i % len(templates)]]
                if rng.random() < 0.15:
                    parts.reverse()            # question first, context second
                hot = False
                if stage in INTENT and rng.random() < 0.5:
                    # visit-request cues only on visit questions, so the topic stays unambiguous
                    pool = [c for c in INTENT[stage] if (("visit" in c.lower() or "tour" in c.lower()
                            or "student day" in c.lower()) == (topic == "campus_visit"))] or INTENT[stage]
                    parts.append(C.pick(rng, pool))
                    hot = True
                elif stage in ("prospect", "applicant", "admitted") and rng.random() < 0.3:
                    parts.append(C.pick(rng, HEDGES))
                text = " ".join(parts)
                opener = C.pick(rng, OPENERS)
                if opener and not text.startswith("I "):
                    text = text[0].lower() + text[1:]
                text = opener + text
                if rng.random() < 0.08:
                    o, c = C.pick(rng, SPANISH)
                    text = o + text + c
                text = C.messy(rng, text, typo_rate=0.035, p_typo=0.35)
                examples.append({
                    "family": fam, "group": topic,
                    "state": {"message": wrap(rng, text)},
                    "gold": {"stage": stage, "topic": topic, "hot_lead": hot},
                })
    return examples


def main():
    rng = C.rng_for(NAME, SEED)
    splits = C.write_dataset(NAME, build(rng), HERE, PREFIX, seed=SEED, test_families=TEST_FAMILIES)
    C.summary(NAME, splits)
    return splits


if __name__ == "__main__":
    main()
