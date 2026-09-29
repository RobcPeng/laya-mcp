"""Generate the he-accommodation-request-routing accelerator set (deterministic, stdlib only).

Each phrasing family is a hand-written core request for one accommodation type. The two flags are
composed on top, independently of the type:

  documentation_mentioned  a documentation sentence (doctor's letter, IEP/504 plan, existing
                           accommodation letter, provider sending paperwork) is added, or a near miss
                           that mentions a doctor or condition but no document, or nothing.
  time_sensitive           a timing sentence that puts an exam, move-in, or deadline inside two weeks
                           (with explicit dates or "Thursday"), or a near miss that is far off or in the
                           past, or nothing.

Some families pin a flag (a faculty member implementing an existing accommodation letter always has
documentation). Rows are wrapped as a portal form, a student email, a faculty forward, or a parent email.
TEST holds out whole families.

    python datasets/accelerators/he-accommodation-request-routing/generate.py
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import _common as C  # noqa: E402

NAME = "he-accommodation-request-routing"
PREFIX = "heacc"
PER_FAMILY = 40
SEED = 4504

SCHOOLS = ["Westbrook State University", "Pine Valley Community College", "Lakeshore College",
           "North Ridge University", "Cedar Plains Technical College"]
COURSES = ["CHEM 101", "BIO 210", "STAT 250", "ENGL 102", "HIST 115", "PSYC 100", "MATH 221", "ECON 201",
           "CS 161", "NURS 230", "ART 105", "PHYS 131"]
CONDITIONS = ["a chronic health condition", "a disability", "a medical condition", "ADHD", "a learning disability",
              "a mobility impairment", "low vision", "a hearing impairment", "anxiety", "a chronic illness",
              "a condition that flares up", "an injury from this summer"]

SLOTS = {
    "course": COURSES, "cond": CONDITIONS,
    "hall": ["Aspen Hall", "Birch Hall", "the north residence hall", "Maple Commons", "the freshman dorms"],
}

# (type, family, pinned_doc or None, pinned_time or None, templates)
FAMILIES = [
    # ------------------------------------------------------------ testing
    ("testing", "testing/extended-time", None, None, [
        "I have {cond} and I'm requesting extended time on exams in {course}.",
        "Hi, I'd like to set up time-and-a-half for my tests this term because of {cond}.",
        "Requesting extra time on quizzes and exams. I have {cond} and I run out of time every test.",
    ]),
    ("testing", "testing/separate-room", None, None, [
        "Can I take my exams in a separate, low-distraction room? I have {cond}.",
        "I need a quiet testing location for {course} exams because of {cond}.",
        "Requesting a reduced-distraction testing room and breaks during exams.",
    ]),
    ("testing", "testing/reschedule-flare", None, None, [
        "Because of {cond} I may need to reschedule an exam if I have a flare-up. How do I set that up?",
        "I need the option to move an exam when my symptoms flare. Is that an accommodation you offer?",
    ]),
    ("testing", "testing/faculty-implement", True, None, [
        "Faculty question: a student in my {course} section gave me an accommodation letter for extended time. "
        "How do I set that up for the online quizzes?",
        "I received an accommodation letter for a student who needs a separate room for exams. Do I book the room "
        "or does your testing center handle it?",
    ]),
    # ------------------------------------------------------------ housing
    ("housing", "housing/single-room", None, None, [
        "I'm requesting a single room as a housing accommodation because of {cond}.",
        "Can I get a private room? I have {cond} and sharing a room makes it hard to manage.",
        "Housing accommodation request: single room with a private bathroom if possible.",
    ]),
    ("housing", "housing/accessible-room", None, None, [
        "I use a wheelchair and need an accessible room in {hall} near an elevator.",
        "Requesting a ground-floor room because of {cond}; stairs are not possible for me.",
        "Need a room with an accessible shower and grab bars.",
    ]),
    ("housing", "housing/air-conditioning", None, None, [
        "My doctor says heat makes my condition worse. Can I be placed in a building with air conditioning?",
        "Requesting a room with AC because of {cond}.",
    ]),
    ("housing", "housing/pet-policy", False, None, [
        "Can I bring my cat to live with me in {hall}? She's just my pet but I really miss her.",
        "What's the pet policy in the dorms? I want to bring my dog from home.",
        "Is it OK to keep a small fish tank or a hamster in my room?",
    ]),
    # ------------------------------------------------------------ course materials
    ("course_materials", "materials/alt-format", None, None, [
        "I need my textbooks in an accessible digital format for my screen reader. I have low vision.",
        "Requesting alternative format (large print) course materials for {course}.",
        "Can I get e-text versions of the required readings? I have {cond}.",
    ]),
    ("course_materials", "materials/captions", None, None, [
        "I'm hard of hearing and the {course} lecture videos have no captions. Can they be captioned?",
        "Requesting transcripts for the recorded lectures and captioned videos in {course}.",
        "I need a sign language interpreter or live captioning for my lectures.",
    ]),
    ("course_materials", "materials/faculty-captions", True, None, [
        "Faculty here: a student's accommodation letter says captioned media. Several of my {course} videos are "
        "from YouTube with auto captions only. What should I do?",
        "I have a student with an approved alternative-format accommodation. Where do I send my course packet to be "
        "converted?",
    ]),
    # ------------------------------------------------------------ attendance
    ("attendance", "attendance/flex", None, None, [
        "I have {cond} that sometimes keeps me from attending class. I'm requesting attendance flexibility.",
        "Can I get flexibility on attendance for {course}? My condition flares unpredictably.",
        "Requesting a disability-related attendance modification because of {cond}.",
    ]),
    ("attendance", "attendance/deadline-flex", None, None, [
        "I need some flexibility on assignment deadlines when my {cond} flares up.",
        "Is it possible to get short extensions on assignments as an accommodation? I have {cond}.",
    ]),
    ("attendance", "attendance/treatment", None, None, [
        "I'll be missing class for regular medical treatments this term. Can I get attendance flexibility?",
        "I have ongoing appointments throughout the semester for {cond} and will miss some {course} labs. What can be done?",
    ]),
    # ------------------------------------------------------------ animal
    ("animal", "animal/esa", None, None, [
        "I'd like to request an emotional support animal in {hall}. He's a small dog and helps with {cond}.",
        "Requesting approval to have my emotional support cat live with me in on-campus housing.",
        "How do I get my ESA approved for the dorms?",
    ]),
    ("animal", "animal/service-dog", None, None, [
        "I have a trained service dog and wanted to let your office know he'll be with me in classes and housing.",
        "My service animal will be accompanying me on campus. Is there anything I need to register?",
        "Do I need to tell anyone that I use a guide dog?",
    ]),
    # ------------------------------------------------------------ other
    ("other", "other/note-taking", None, None, [
        "Requesting a note-taker or access to class notes because of {cond}.",
        "Can I record lectures as an accommodation? Writing notes is hard for me because of {cond}.",
    ]),
    ("other", "other/parking-mobility", None, None, [
        "I have a mobility impairment and need accessible parking closer to the science building.",
        "Is there a way to get a temporary disability parking permit after my knee surgery?",
    ]),
    ("other", "other/dining", None, None, [
        "I have severe food allergies and need an accommodation for the required meal plan.",
        "Requesting a meal plan exemption because of a medical diet.",
    ]),
    ("other", "other/lab-access", None, None, [
        "I use a wheelchair and the lab benches in {course} are too high. I need an accessible lab station.",
        "Requesting an adjustable-height workstation for my chemistry lab.",
    ]),
]

DOC_YES = [
    "I have a letter from my doctor I can upload.", "My doctor's letter is attached.",
    "I had an IEP in high school and can send it.", "I had a 504 plan in high school.",
    "My provider will send the paperwork this week.", "Attached is my diagnosis documentation.",
    "I already have an accommodation letter from last semester.", "My psychologist wrote an evaluation I can share.",
    "I can get medical records from my specialist if you need them.", "I uploaded my documentation to the portal.",
]
DOC_NEAR = [  # mention a doctor or condition, but no document
    "My doctor suggested I ask about this.", "I've been dealing with this since high school.",
    "My counselor told me to reach out.", "I'm not sure what you need from me.",
    "My mom said your office could help.", "I see a specialist for this.",
]
TIME_YES = {
    "testing": ["My midterm is this Thursday.", "The exam is tomorrow at 9am.", "My first quiz is next Monday.",
                "Our final is in 10 days.", "The test is on Oct 14 and today is Oct 8."],
    "housing": ["Move-in is Aug 20 and today is Aug 12.", "I move in this Saturday.",
                "Room selection closes on Friday.", "The housing deadline is in one week."],
    "course_materials": ["Classes start Monday.", "The first reading is due Wednesday.",
                         "We have a video quiz due in 5 days."],
    "attendance": ["I already missed two classes this week and the lab is Thursday.", "My next treatment is Monday.",
                   "I have a required lab session next Tuesday."],
    "animal": ["Move-in is this weekend.", "I arrive on campus in 4 days.", "Classes start next week."],
    "other": ["I need this before classes start Monday.", "This needs to be in place by next Tuesday.",
              "Can this be set up this week? Term starts in 6 days."],
}
TIME_NEAR = [  # far off or in the past
    "This is for next semester.", "Planning ahead for spring term.", "Finals aren't until December (it's September now).",
    "I had a hard time with exams last year.", "Move-in isn't until next August.", "No rush, this is for next year.",
]


def wrap(rng, text, faculty):
    sid = f"S00{rng.randrange(100000, 999999)}"
    name = C.person(rng)
    school = C.pick(rng, SCHOOLS)
    r = rng.random()
    if faculty:
        return f"From: {C.email(rng, name, 'example.edu')}\nSubject: Accommodation question\n\n{text}\n\n{name}, {school}"
    if r < 0.3:
        return (f"[Accommodation Request Form - {school}]\nStudent ID: {sid}\n"
                f"Request details: {text}")
    if r < 0.55:
        return (f"Subject: {C.pick(rng, ['Accommodations', 'Request', 'Help please', 'Disability services question'])}\n\n"
                f"{C.pick(rng, ['Hi,', 'Hello,', 'To whom it may concern,', 'Hi there,', ''])} {text}\n\n"
                f"{C.pick(rng, ['Thanks,', 'Best,', 'Thank you,'])}\n{name} ({sid})")
    if r < 0.7:
        return (f"Hello, I'm writing on behalf of my {C.pick(rng, ['son', 'daughter', 'child'])}, a first-year at "
                f"{school}. {text} Please let us know the next steps. - {name}")
    if r < 0.8:
        return (f"---------- Forwarded message ---------\nFrom: {C.email(rng, name, 'example.edu')}\n"
                f"Student asked me to forward this: {text}")
    return text


def build(rng):
    examples = []
    for typ, fam, pin_doc, pin_time, templates in FAMILIES:
        for i in range(PER_FAMILY):
            core = C.fill(rng, templates[i % len(templates)], SLOTS)
            parts = [core]
            if pin_doc is None:
                r = rng.random()
                doc = r < 0.45
                if doc:
                    parts.append(C.pick(rng, DOC_YES))
                elif r < 0.7:
                    parts.append(C.pick(rng, DOC_NEAR))
            else:
                doc = pin_doc
            if pin_time is None:
                r = rng.random()
                tsens = r < 0.4
                if tsens:
                    parts.append(C.pick(rng, TIME_YES[typ]))
                elif r < 0.7:
                    parts.append(C.pick(rng, TIME_NEAR))
            else:
                tsens = pin_time
            head, extra = parts[0], parts[1:]
            rng.shuffle(extra)
            text = " ".join([head] + extra)
            text = C.messy(rng, text, typo_rate=0.03, p_typo=0.35)
            examples.append({
                "family": fam, "group": typ,
                "state": {"request": wrap(rng, text, "faculty" in fam)},
                "gold": {"type": typ, "documentation_mentioned": doc, "time_sensitive": tsens},
            })
    return examples


TEST_FAMILIES = ["testing/faculty-implement", "housing/pet-policy", "materials/captions", "attendance/treatment",
                 "animal/service-dog", "other/dining"]


def main():
    rng = C.rng_for(NAME, SEED)
    splits = C.write_dataset(NAME, build(rng), HERE, PREFIX, seed=SEED, test_families=TEST_FAMILIES)
    C.summary(NAME, splits)
    return splits


if __name__ == "__main__":
    main()
