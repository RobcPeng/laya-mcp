"""Generate the he-early-alert accelerator set (deterministic, stdlib only).

Compositional: each row is an early-alert note in one of seven styles (LMS flag, advisor case note,
faculty email, coach note, residence life note, tutoring center note, kudos note). The four signals
(academic, attendance, financial, wellbeing) are drawn independently; each drawn signal adds one snippet,
and every note also gets zero to two neutral snippets that reuse signal vocabulary without the signal
(an excused absence with work caught up, a scholarship that covers costs, a strong midterm).

Signal snippets come in two banks. Train/val rows use bank A in five styles; TEST rows use bank B in two
held-out styles (faculty email, residence life), so test wording is new at both levels.

    python datasets/accelerators/he-early-alert/generate.py
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import _common as C  # noqa: E402

NAME = "he-early-alert"
PREFIX = "heea"
SEED = 2718
PER_STYLE = 125

COURSES = ["CHEM 101", "MATH 112", "BIO 210", "ECON 201", "ENGL 101", "PSYC 100", "STAT 250", "PHYS 121",
           "HIST 110", "CS 150", "NURS 210", "ACCT 205", "SPAN 102"]
SLOTS = {
    "n": lambda r: str(r.randrange(3, 7)), "m": lambda r: str(r.randrange(7, 12)),
    "pct": lambda r: str(r.randrange(28, 59)), "good": lambda r: str(r.randrange(85, 99)),
    "wk": lambda r: str(r.randrange(3, 8)), "date": lambda r: f"{r.randrange(9, 12)}/{r.randrange(1, 29)}",
    "course": COURSES,
}

# bank A (train/val) and bank B (test), per signal
SIGNALS = {
    "academic": (
        ["Missing {n} of the last {m} assignments.", "Current grade is {pct}%.", "Failed the first two quizzes.",
         "Has not turned in a lab report since week {wk}.", "Midterm score {pct}/100, well below passing.",
         "Falling behind on readings and did not submit the essay draft.", "Currently holding a D- in the course."],
        ["Zero on the last {n} homework sets.", "Projected final grade: F.", "Did not submit the research proposal.",
         "Exam average is {pct}%, not on track to pass.", "Hasn't completed any of the online modules since week {wk}."],
    ),
    "attendance": (
        ["Absent {n} of the last {m} class meetings.", "Has not attended lab since {date}.",
         "Missed {n} sessions in a row without contacting me.", "Attendance has dropped to about half of classes.",
         "No-show at the last {n} recitations."],
        ["Hasn't been in class since {date}.", "Skipped {n} of {m} lectures this month.",
         "Stopped coming to the Friday discussion section.", "Absent from every class this week and last."],
    ),
    "financial": (
        ["Mentioned picking up extra shifts to cover rent.", "Said they can't afford the textbook or the lab kit.",
         "Has a registration hold for an unpaid balance.", "Asked me where the campus food pantry is.",
         "Car broke down and they can't pay for the repair to get to campus."],
        ["Working 35 hours a week to pay tuition.", "Told me the family can't cover next semester's bill.",
         "Skipping meals to save money, per the student.", "Worried about losing housing because rent is late."],
    ),
    "wellbeing": (
        ["Seemed withdrawn and tearful during office hours.", "Says they are barely sleeping and very anxious.",
         "Has been sick for two weeks and seems run down.", "Says they have no friends on campus and feel isolated.",
         "Recently lost a grandparent and is struggling."],
        ["Noticeably flat and quiet compared with earlier in the term.", "Mentioned panic attacks before exams.",
         "Going through a hard breakup and seems distracted and upset.", "Looks exhausted and said they feel overwhelmed."],
    ),
}
# crisis-adjacent wellbeing language: forces risk 3 (and should also go to the safety process)
SEVERE = (
    ["Said they feel hopeless and don't see the point of trying anymore.",
     "Roommate reports the student has not left their room in a week."],
    ["Told me they feel like giving up on everything, not just school.",
     "Friends say the student has stopped eating and won't answer messages."],
)
NEUTRAL = (
    ["Scored {good} on the midterm.", "Excused absence for athletics travel; all work is caught up.",
     "Received a full-tuition scholarship this term, so costs are covered.", "Participates in every discussion.",
     "Works part-time at the library and says the hours are manageable.", "Was a little tired after the away game but fine.",
     "Asked about study abroad options for next year."],
    ["Turned in every assignment on time.", "Missed one class for a documented family wedding and made up the work.",
     "Mentioned the new work-study job is going well.", "Came to office hours to get ahead on the final project.",
     "Upbeat and engaged in lab."],
)
STYLES = ["lms_flag", "advisor_note", "coach_note", "tutoring_note", "kudos_note", "faculty_email", "reslife_note"]
TEST_STYLES = {"faculty_email", "reslife_note"}


def risk(signals, severe):
    if severe:
        return 3
    k = len(signals)
    if k == 0:
        return 0
    if k >= 3 or ("wellbeing" in signals and k >= 2):
        return 3
    if k == 2 or signals == {"wellbeing"}:
        return 2
    return 1


def render(rng, style, snippets, course, has_signal):
    name = C.person(rng)
    body = " ".join(snippets) if snippets else ""
    if style == "lms_flag":
        flag = C.pick(rng, ["Academic concern", "Attendance concern", "General concern", "Referral"]) if has_signal \
            else C.pick(rng, ["Kudos", "General note", "Check-in"])
        return f"[Early Alert] Course: {course} | Student: {name} | Flag: {flag} | Instructor comment: {body}"
    if style == "advisor_note":
        return f"Advising note {C.pick(rng, ['10/02', '10/14', '11/03', '9/28'])} - met with {name}. {body} " \
               f"{C.pick(rng, ['Follow up in 2 weeks.', 'Will check in after midterms.', '', 'Referred to tutoring.'])}"
    if style == "coach_note":
        return f"Coach report ({C.pick(rng, ['soccer', 'track', 'swim', 'volleyball', 'baseball'])}): {name}. {body}"
    if style == "tutoring_note":
        return f"Tutoring center visit log - {name}, {course}. {body}"
    if style == "kudos_note":
        return f"{C.pick(rng, ['Progress report', 'Midterm check', 'Faculty feedback'])} for {name} in {course}: {body}"
    if style == "faculty_email":
        lead = C.pick(rng, ["I wanted to flag", "I'm writing about", "Quick note on"]) if has_signal else \
            C.pick(rng, ["Quick update on", "Sharing a note about", "Just an FYI on"])
        return (f"Hi advising team,\n\n{lead} {name} in my {course} section. {body}\n\n"
                f"{C.pick(rng, ['Thanks,', 'Best,', '-'])}\n{C.pick(rng, ['Prof. Example', 'Dr. Placeholder', 'Instructor Sample'])}")
    return f"ResLife note (RA, {C.pick(rng, ['Aspen Hall', 'Birch Hall', 'North Tower'])}): resident {name}. {body}"


def build(rng):
    exs = []
    for style in STYLES:
        bank = 1 if style in TEST_STYLES else 0
        for i in range(PER_STYLE):
            if rng.random() < 0.18:
                signals = set()
            else:
                signals = {s for s in SIGNALS if rng.random() < 0.38}
            severe = "wellbeing" in signals and rng.random() < 0.2
            snips = []
            for s in sorted(signals):
                if s == "wellbeing" and severe:
                    snips.append(C.pick(rng, SEVERE[bank]))
                else:
                    snips.append(C.pick(rng, SIGNALS[s][bank]))
            for _ in range(rng.choice([0, 0, 1, 1, 2]) if signals else rng.choice([1, 2, 2])):
                snips.append(C.pick(rng, NEUTRAL[bank]))
            snips = list(dict.fromkeys(C.fill(rng, x, SLOTS) for x in snips))
            rng.shuffle(snips)
            text = render(rng, style, snips, C.pick(rng, COURSES), bool(signals))
            text = C.messy(rng, text, typo_rate=0.03, p_typo=0.3)
            exs.append({"family": f"{style}/bank{'B' if bank else 'A'}", "group": style,
                        "state": {"note": text},
                        "gold": {"academic_risk": "academic" in signals, "attendance": "attendance" in signals,
                                 "financial_stress": "financial" in signals,
                                 "wellbeing_concern": "wellbeing" in signals, "risk": risk(signals, severe)}})
    return exs


def main():
    rng = C.rng_for(NAME, SEED)
    exs = build(rng)
    test = sorted({e["family"] for e in exs if e["family"].split("/")[0] in TEST_STYLES})
    splits = C.write_dataset(NAME, exs, HERE, PREFIX, seed=SEED, test_families=test)
    C.summary(NAME, splits)
    return splits


if __name__ == "__main__":
    main()
