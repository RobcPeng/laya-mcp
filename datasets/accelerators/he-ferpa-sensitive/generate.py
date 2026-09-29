"""Generate the he-ferpa-sensitive accelerator set (deterministic, stdlib only).

Text snippets campus staff might paste into an LLM, a ticket, a shared doc, or a public channel: emails,
spreadsheet rows, meeting notes, chat messages, letters. Each family is one kind of snippet with a fixed
record_type; protected_record = record_type in PROTECTED. Hard negatives use the same vocabulary without
an identifiable student: aggregate statistics, FERPA policy text, course descriptions, blank forms,
directory-only lists. TEST holds out whole families.

    python datasets/accelerators/he-ferpa-sensitive/generate.py
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import _common as C  # noqa: E402

NAME = "he-ferpa-sensitive"
PREFIX = "ferpa"
SEED = 1974
PER_FAMILY = 40
PROTECTED = {"grades", "discipline", "financial", "health_disability", "identifiers"}

MAJORS = ["Biology", "Mechanical Engineering", "History", "Nursing", "Computer Science", "Psychology",
          "Accounting", "Music", "Political Science", "Chemistry", "Elementary Education", "Art History"]
COURSES = ["CHEM 101", "MATH 221", "BIO 210", "ECON 201", "HIST 340", "PSYC 100", "STAT 250", "PHYS 121",
           "ENGL 102", "CS 150", "NURS 310", "ACCT 205"]


def sid(rng):
    return f"S{rng.randrange(10000000, 99999999):08d}"


def gpa(rng):
    return f"{rng.uniform(0.8, 4.0):.2f}"


SLOTS = {
    "name": C.person, "fn": C.first_name, "major": MAJORS, "course": COURSES, "sid": sid, "ssn": C.fake_ssn,
    "gpa": gpa, "gpa_low": lambda r: f"{r.uniform(0.8, 1.99):.2f}", "gpa_hi": lambda r: f"{r.uniform(2.5, 4.0):.2f}", "grade": ["A", "A-", "B+", "B", "C+", "C", "D", "F", "W", "I"],
    "score": lambda r: str(r.randrange(31, 99)), "amt": lambda r: f"${r.randrange(150, 14000):,}",
    "term": ["Fall 2026", "Spring 2026", "Summer 2026", "Fall 2025"],
    "year": ["first-year", "sophomore", "junior", "senior", "graduate"],
    "status": ["full-time", "part-time", "enrolled", "on leave", "graduated May 2026"],
    "email": lambda r: C.email(r, domain="example.edu"),
    "n": lambda r: str(r.randrange(12, 480)), "avg": lambda r: str(r.randrange(61, 89)),
    "staff": ["Dean Placeholder", "Dr. Sample", "Prof. Example", "the registrar", "Advising"],
    "hi": ["Hi all,", "Team -", "Hello,", "Quick note:", "FYI", ""],
}

# (record_type, family, [templates])
FAMILIES = [
    # ------------------------------------------------------------ grades (protected)
    ("grades", "grades/email-faculty", [
        "{hi} {name} is failing {course} with a {score}% and has missed the last two exams. Can advising reach out?",
        "Following up on {name}: final grade in {course} is {grade}. Please post the change by Friday.",
        "{name} ({major}) is currently on academic probation with a {gpa_low} cumulative GPA.",
    ]),
    ("grades", "grades/spreadsheet", [
        "name,course,midterm,final_grade\n{name},{course},{score},{grade}\n{name},{course},{score},{grade}",
        "student | term GPA | standing\n{name} | {gpa_low} | probation\n{name} | {gpa_hi} | good standing",
        "Row 14: {name}, {course}, grade {grade}, notes: asked about incomplete",
    ]),
    ("grades", "grades/chat", [
        "lol did you see {fn} {last} got a {score} on the {course} final",
        "can someone check why {name}'s {course} grade still shows {grade} in the portal? they're emailing me daily",
        "heads up {name} is sitting at a {gpa} and might lose the scholarship GPA requirement",
    ]),
    ("grades", "grades/own-question", [
        "Hi Professor, this is {name}. I got a {score} on the {course} midterm. Is there any way to still pass?",
        "Hello, my name is {name} and my {term} GPA dropped to {gpa}. Will I be put on probation?",
    ]),
    ("grades", "grades/letter", [
        "Dear {name}, this letter confirms that your cumulative GPA of {gpa_low} places you on academic suspension for {term}.",
        "To whom it may concern: {name} completed {course} in {term} with a final grade of {grade}.",
    ]),
    # ------------------------------------------------------------ discipline (protected)
    ("discipline", "discipline/conduct-notes", [
        "Conduct meeting notes: {name} found responsible for alcohol policy violation in residence hall; sanction: probation through {term}.",
        "{name} has an open academic integrity case for plagiarism in {course}. Hearing scheduled next week.",
        "Per student conduct, {name} is on disciplinary probation and cannot hold a club officer role.",
    ]),
    ("discipline", "discipline/chat", [
        "did you hear {name} got caught cheating on the {course} exam? integrity office has it now",
        "fyi {fn} {last} was suspended for the fight in the dorm last week, don't let them into the lab",
    ]),
    # ------------------------------------------------------------ financial (protected)
    ("financial", "financial/aid", [
        "{name} received a Pell Grant of {amt} for {term} and still owes {amt} on their account.",
        "Aid summary for {name}: subsidized loan {amt}, work-study {amt}, EFC/SAI 0.",
        "{hi} {name} lost aid eligibility after the SAP review. Parent income on the FAFSA was {amt}.",
    ]),
    ("financial", "financial/balance", [
        "Student accounts: {name} has a past-due balance of {amt}; registration hold placed.",
        "{name} | balance {amt} | payment plan: yes | last payment 09/15",
        "can we waive the late fee for {name}? they owe {amt} and their dad lost his job",
    ]),
    # ------------------------------------------------------------ health / disability (protected)
    ("health_disability", "health/accommodation", [
        "{name} has an accommodation letter for extended time (1.5x) on exams in {course} due to ADHD.",
        "Please make sure {name} gets a reduced-distraction testing room; accessibility services approved it.",
        "{hi} {name} is registered with disability services for a hearing impairment; captions needed for all videos.",
    ]),
    ("health_disability", "health/counseling", [
        "{name} has been seeing counseling services weekly since the start of {term}.",
        "Case note: {name} was hospitalized last week and is returning to classes Monday with a medical withdrawal pending.",
        "{fn} {last} told me they have depression and are on new medication, can we extend deadlines?",
    ]),
    # ------------------------------------------------------------ identifiers (protected)
    ("identifiers", "identifiers/id-with-name", [
        "Please reset the portal account for {name}, student ID {sid}.",
        "{name} {sid} {email}",
        "Student: {name}  ID: {sid}  SSN: {ssn}",
        "Can you look up {name}? SSN {ssn}, they forgot their ID number.",
    ]),
    ("identifiers", "identifiers/roster-ids", [
        "roster export\n{sid}, {name}\n{sid}, {name}\n{sid}, {name}",
        "Attendees with ID numbers: {name} ({sid}), {name} ({sid})",
    ]),
    # ------------------------------------------------------------ directory only (not protected)
    ("directory_only", "directory/commencement", [
        "Congratulations to {name}, {major}, who graduated in May with a B.S. and will speak at commencement.",
        "Commencement program: {name}, Bachelor of Arts in {major}; {name}, Bachelor of Science in {major}.",
        "Please welcome our new student employee {name}, a {year} majoring in {major}.",
    ]),
    ("directory_only", "directory/enrollment", [
        "Enrollment verification: {name} is enrolled {status} for {term}.",
        "{name} | {major} | {year} | {status}",
        "Yes, {name} attended the university from 2022 to 2026 and earned a degree in {major}.",
    ]),
    ("directory_only", "directory/club-roster", [
        "Chess club officers for {term}: {name} (president), {name} (treasurer). Contact: {email}",
        "Intramural soccer roster: {name}, {name}, {name}, {name}. Games on Thursdays.",
        "Dean's List honorees in {major} (published): {name}, {name}.",
    ]),
    # ------------------------------------------------------------ none (not protected)
    ("none", "none/aggregate", [
        "The average on the {course} midterm was {avg}% across {n} students; the median was a B-.",
        "Retention for first-year {major} students rose to {avg}% this year. {n} students were on probation college-wide.",
        "Section 3 of {course} had a {avg}% pass rate; section 4 had {avg}%.",
    ]),
    ("none", "none/policy", [
        "FERPA gives students the right to inspect their education records and limits disclosure without consent.",
        "Reminder: do not share grades by email with parents unless the student has signed a FERPA release.",
        "Directory information includes name, major, dates of attendance, and degrees awarded. Students may opt out.",
        "{hi} per FERPA, faculty may not post grades by name or {sid}-style ID. Use the LMS gradebook for {course}.",
        "Training slide {n}: education records include grades, transcripts, class schedules, and disciplinary files.",
        "{staff}: parents of dependent students may request records only with a signed release on file.",
        "Q: Can I confirm to an employer that a student attended in {term}? A: Yes, dates of attendance are directory information unless the student opted out.",
    ]),
    ("none", "none/course-and-ops", [
        "{course} covers {major} fundamentals. Grading: 40% exams, 30% labs, 30% homework. Late work loses 10% per day.",
        "The registrar's office will be closed Friday. Grade submission deadline for {term} is December 18.",
        "Student IDs are 9 characters: an S followed by 8 digits. Never put SSNs in tickets.",
        "Room change: {course} will meet in Science Hall 204 starting next week.",
    ]),
    ("none", "none/blank-form", [
        "Grade change form. Student name: ________  Student ID: ________  Course: ________  Old grade: __  New grade: __",
        "Accommodation request template: [student name] requests [accommodation] for [course]. Documentation attached: Y/N",
        "Aid appeal form fields: name, ID, term, reason for appeal, supporting documents.",
        "Template for {course} instructors: Dear [Student], your current grade is [grade]. Please see me in office hours.",
        "Conduct hearing notice (blank): Student: [name] Case #: [ ] Alleged violation: [ ] Hearing date: [ ]",
        "Mail merge fields for {term} probation letters: <<FirstName>>, <<GPA>>, <<AdvisorName>>.",
    ]),
]

TEST_FAMILIES = ["grades/own-question", "discipline/chat", "financial/balance", "health/counseling",
                 "identifiers/roster-ids", "directory/club-roster", "none/blank-form"]

WRAP = ["{t}", "{t}", "Email: {t}", "[Slack #advising] {t}", "Meeting notes - {t}", "{t}\n\n-- sent from my phone",
        "Pasted into chat assistant: {t}", "Ticket comment: {t}"]


def build(rng):
    exs = []
    for rtype, fam, tpls in FAMILIES:
        for i in range(PER_FAMILY):
            slots = dict(SLOTS, last=C.LAST)
            t = C.fill(rng, tpls[i % len(tpls)], slots)
            if rng.random() < 0.3:
                t = C.typo(rng, t, 0.03)
            t = C.pick(rng, WRAP).replace("{t}", t)
            exs.append({"family": fam, "group": rtype, "state": {"text": t.strip()},
                        "gold": {"protected_record": rtype in PROTECTED, "record_type": rtype}})
    return exs


def main():
    rng = C.rng_for(NAME, SEED)
    splits = C.write_dataset(NAME, build(rng), HERE, PREFIX, seed=SEED, test_families=TEST_FAMILIES)
    C.summary(NAME, splits)
    return splits


if __name__ == "__main__":
    main()
