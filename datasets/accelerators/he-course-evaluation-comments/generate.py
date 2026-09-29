"""Generate the he-course-evaluation-comments accelerator set (deterministic, stdlib only).

Each phrasing family is one kind of end-of-term course evaluation comment with fixed gold labels
(theme, sentiment 0-4, actionable, inappropriate). Templates have slots for the course, the instructor
reference, and concrete details. Rows then get an optional eval-form prompt prefix, and a noise pass
(typos, all-lowercase, occasional ALL CAPS for rants). TEST holds out whole families.

    python datasets/accelerators/he-course-evaluation-comments/generate.py
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import _common as C  # noqa: E402

NAME = "he-course-evaluation-comments"
PREFIX = "hece"
PER_FAMILY = 26
SEED = 5150


def prof(rng):
    return C.pick(rng, [f"Prof. {C.pick(rng, C.LAST)}", f"Dr. {C.pick(rng, C.LAST)}", f"Professor {C.pick(rng, C.LAST)}",
                        "the professor", "the instructor", "our prof", f"{C.pick(rng, C.LAST)}"])


SLOTS = {
    "prof": prof,
    "course": ["this class", "this course", "CHEM 101", "BIO 210", "STAT 250", "ENGL 102", "HIST 115", "PSYC 100",
               "MATH 221", "ECON 201", "the lab", "this seminar", "CS 161", "SOC 110", "PHYS 131"],
    "wow": ["", "!", "!!", " :)", " 10/10", " honestly", ""],
    "pset": ["problem sets", "lab reports", "reading responses", "discussion posts", "quizzes", "essays"],
    "lms": ["Canvas", "the LMS", "Blackboard", "Moodle", "the course site"],
    "n": ["three", "four", "five", "2", "6"],
    "weeks": ["3 weeks", "a month", "six weeks", "until the end of the term", "over a month"],
}

# (theme, family, sentiment 0-4, actionable, inappropriate, templates)
FAMILIES = [
    # ------------------------------------------------------------ instruction
    ("instruction", "instr/praise-vague", 4, False, False, [
        "Best professor I've ever had{wow}",
        "{prof} is amazing. Loved every lecture of {course}{wow}",
        "Incredible teacher, made {course} actually fun{wow}",
        "Would take any class {prof} teaches. Just fantastic.",
    ]),
    ("instruction", "instr/positive-suggestion", 3, True, False, [
        "{prof} explains things clearly. It would be even better with one more worked example before each problem set.",
        "Good lectures overall. Suggest recording them so we can review before exams.",
        "Really liked the clicker questions in {course}; please keep them and add a short recap at the start of class.",
    ]),
    ("instruction", "instr/confusing-specific", 1, True, False, [
        "Lectures went way too fast through the derivations. Slowing down or posting the worked steps would help a lot.",
        "{prof} mostly read off the slides and skipped questions. More examples and pausing for questions would make a big difference.",
        "The lectures didn't match the homework at all; we learned the theory but never saw how to set up the problems.",
    ]),
    ("instruction", "instr/rant-vague", 0, False, False, [
        "Worst class ever. Learned nothing.",
        "i taught myself everything from youtube. what was the point of lecture",
        "Terrible. Just terrible. Do not take {course}.",
        "absolute waste of a semester",
    ]),
    ("instruction", "instr/harsh-fair", 2, True, False, [
        "{prof} was brutal but fair. Exams were hard, but everything on them was covered in lecture. More practice exams would help.",
        "Tough class and I struggled, but {prof} knows the material. Wish there were more office hours before exams.",
        "Not easy, but I learned a ton. The pace in the second half was too fast though.",
    ]),
    ("instruction", "instr/attack", 0, False, True, [
        "{prof} is a clueless idiot who shouldn't be allowed to teach.",
        "Honestly the prof is a joke of a human being.",
        "This guy is so stupid it hurts. How is he a professor?",
    ]),
    ("instruction", "instr/attack-specific", 0, True, True, [
        "{prof} is an arrogant jerk. He never posted the slides and refused to answer questions in class.",
        "What a pompous clown. Lectures were 20 minutes late every day and nothing was explained.",
    ]),
    # ------------------------------------------------------------ workload
    ("workload", "workload/heavy-specific", 1, True, False, [
        "{n} {pset} a week plus labs was too much for a 3-credit course. Cut one assignment per week.",
        "Workload was unreasonable: 15+ hours a week on {pset} alone. Please spread the big project across more weeks.",
        "Having the final project and two {pset} due the same week was brutal; stagger the deadlines.",
    ]),
    ("workload", "workload/vague-heavy", 1, False, False, [
        "way too much work",
        "This class took over my whole life.",
        "SO MUCH HOMEWORK",
        "the workload was insane for a gen ed",
    ]),
    ("workload", "workload/sarcasm", 1, False, False, [
        "Loved spending every weekend on {course}. Really. Best use of my time.",
        "Oh sure, a 'light' intro course. Totally.",
        "Nothing says gen ed like 30 hours a week, am I right",
    ]),
    ("workload", "workload/manageable", 3, False, False, [
        "Workload was reasonable and the {pset} actually helped.",
        "Manageable amount of work, never felt overwhelmed.",
        "The {pset} were fair and kept me on track{wow}",
    ]),
    ("workload", "workload/insult", 0, False, True, [
        "{prof} is a sadist who gets off on drowning us in homework.",
        "Only a heartless freak would assign this much work.",
    ]),
    # ------------------------------------------------------------ grading
    ("grading", "grading/unfair-specific", 1, True, False, [
        "The rubric for essays was never shared, so we had no idea how we were being graded.",
        "Grades took {weeks} to come back, so we couldn't learn from mistakes before the next exam.",
        "Two TAs graded the same lab completely differently. There needs to be one rubric.",
    ]),
    ("grading", "grading/mixed", 2, True, False, [
        "Great lectures but the exams were unfair: half the questions covered things we never did in class.",
        "Loved the discussions, but the participation grade was never explained.",
        "Interesting content, but grading on the {pset} felt random and the feedback was one word.",
    ]),
    ("grading", "grading/fair-praise", 3, False, False, [
        "Grading was fair and consistent.",
        "Tests were fair, graded quickly{wow}",
        "Always knew where I stood grade-wise. Appreciated that.",
    ]),
    ("grading", "grading/rant-attack", 0, False, True, [
        "The grading was a joke and the prof is a lazy clown who doesn't read our work.",
        "Whoever grades these exams is an incompetent moron.",
    ]),
    ("grading", "grading/vague-neg", 1, False, False, [
        "Grading was harsh.",
        "unfair grading, not happy",
        "I worked hard and still got a bad grade. Not cool.",
    ]),
    # ------------------------------------------------------------ materials
    ("materials", "materials/textbook-specific", 1, True, False, [
        "We had to buy a $200 textbook and used it twice. Use free readings or put it on reserve.",
        "The required textbook edition was out of print and cost a fortune. An older edition would work fine.",
        "Half the assigned readings were broken links on {lms}.",
    ]),
    ("materials", "materials/slides-request", 2, True, False, [
        "Please post the slides before lecture so we can take notes on them.",
        "Would be helpful to have the lecture recordings posted within a day.",
        "Could the practice problems come with answer keys?",
    ]),
    ("materials", "materials/praise", 4, False, False, [
        "The course materials were excellent, best readings I've had in college{wow}",
        "Loved the videos and the lecture notes. So well made.",
        "Amazing slides and handouts, super clear{wow}",
    ]),
    ("materials", "materials/vague-neg", 1, False, False, [
        "Readings were boring.",
        "the textbook was bad",
        "Didn't like the materials much.",
    ]),
    # ------------------------------------------------------------ accessibility
    ("accessibility", "access/captions", 1, True, False, [
        "None of the lecture videos had captions. As a hard-of-hearing student I could not follow them.",
        "The PDFs on {lms} were scanned images, so my screen reader couldn't read any of them.",
        "Captions on the recorded lectures were auto-generated and mostly wrong. Please correct them.",
    ]),
    ("accessibility", "access/accommodation-missed", 0, True, False, [
        "My extended-time accommodation wasn't set up on the online quizzes, twice. I lost points because of it.",
        "I had an approved separate testing room but it was never arranged for the midterm.",
    ]),
    ("accessibility", "access/praise", 3, False, False, [
        "{prof} was great about accommodations. Never made it awkward.",
        "Really accessible course, everything had captions and alt text.",
    ]),
    # ------------------------------------------------------------ organization
    ("organization", "org/lms-mess", 1, True, False, [
        "{lms} site was a maze. Due dates were listed in three different places and didn't match.",
        "Assignments were hidden in random modules on {lms}. One page with all deadlines would fix this.",
        "The syllabus schedule stopped matching the actual class after week 5.",
    ]),
    ("organization", "org/schedule-changes", 1, True, False, [
        "Deadlines changed without notice several times; announce changes at least a week ahead.",
        "The exam date moved twice with two days' notice. Please fix dates at the start of term.",
    ]),
    ("organization", "org/well-organized", 4, False, False, [
        "Super organized class, always knew what was due{wow}",
        "Best organized course I've taken. Everything was where it should be.",
    ]),
    ("organization", "org/mixed", 2, True, False, [
        "Well organized at first but fell apart after the midterm: modules stopped being posted on time.",
        "Good structure overall, though the group project instructions came out too late.",
    ]),
    # ------------------------------------------------------------ instructor conduct
    ("instructor_conduct", "conduct/unavailable", 1, True, False, [
        "Never answered emails. Office hours were cancelled {n} times.",
        "{prof} took weeks to reply to anything and was never at posted office hours.",
        "Couldn't get a meeting with the instructor all semester.",
    ]),
    ("instructor_conduct", "conduct/disrespectful", 0, True, False, [
        "The professor made fun of students' questions in front of the class. People stopped asking anything.",
        "{prof} rolled their eyes and said 'that's a dumb question' more than once. That needs to stop.",
    ]),
    ("instructor_conduct", "conduct/praise", 4, False, False, [
        "{prof} was always kind and respectful, remembered everyone's name{wow}",
        "Genuinely cared about students. So approachable.",
        "Always available and so patient{wow}",
    ]),
    # ------------------------------------------------------------ other
    ("other", "other/looks", 3, False, True, [
        "{prof} is super hot lol{wow}",
        "Nice to look at for 75 minutes, if you know what I mean",
        "prof has great legs, that's all I'll say",
    ]),
    ("other", "other/appearance-insult", 0, False, True, [
        "{prof} dresses like a slob and talks like one.",
        "Could the instructor maybe shower sometime?",
    ]),
    ("other", "other/meta", 2, False, False, [
        "N/A",
        "no comment",
        "Took it for my major.",
        "8am was rough but that's on me.",
        "It was fine.",
    ]),
    ("other", "other/room", 1, True, False, [
        "The classroom was freezing and the projector in room 204 never worked. Move the class or fix the room.",
        "Lecture hall was way too small, people were sitting on the floor. Needs a bigger room.",
    ]),
]

# Extra phrasings per family (appended to the family's templates) for lexical variety.
EXTRA = {
    "instr/praise-vague": ["Such a great instructor{wow}", "{prof} made me love this subject{wow}",
                           "Best class I've taken at this school. {prof} rocks."],
    "instr/positive-suggestion": ["Liked the class a lot. Only suggestion: post practice problems with solutions each week.",
                                  "Strong teaching. Would help to start each lecture with a 5 minute review of last time."],
    "instr/confusing-specific": ["{prof} assumed we knew calculus already; a quick review in week 1 would have helped.",
                                 "Examples in lecture were way easier than the exam problems. Show harder examples."],
    "instr/rant-vague": ["this class was a nightmare", "zero stars", "Just awful from start to finish."],
    "instr/attack": ["{prof} is a total moron.", "Our instructor is a smug loser."],
    "instr/attack-specific": ["{prof} is a condescending jerk and never explained the assignments before they were due."],
    "workload/heavy-specific": ["The weekly {pset} took 10+ hours each. Two shorter ones would be more reasonable.",
                                "Reading load was 150 pages a week on top of {pset}. Please trim it."],
    "workload/vague-heavy": ["too much work for one class", "exhausting course tbh"],
    "workload/manageable": ["Good balance of work{wow}", "never too much, never too little"],
    "workload/insult": ["{prof} must hate students, what a miserable person."],
    "grading/unfair-specific": ["Points were taken off for formatting rules that were never in the syllabus.",
                                "The final was worth 60% and nobody knew that until week 12. Put the weights in the syllabus."],
    "grading/fair-praise": ["Fair grader{wow}", "Clear rubrics and quick feedback{wow}"],
    "grading/rant-attack": ["The TA who graded our labs is a power-tripping idiot."],
    "grading/vague-neg": ["grades felt unfair", "Harsh grader. Beware."],
    "materials/textbook-specific": ["The online homework code cost $120 on top of tuition. Find a free alternative.",
                                    "Lecture slides had tons of typos and wrong formulas in the chapter 4 set."],
    "materials/slides-request": ["Please upload the lab handouts earlier than the night before.",
                                 "Posting the reading list at the start of term would help."],
    "materials/praise": ["The readings were so interesting{wow}", "Great videos, I rewatched them all before the final."],
    "materials/vague-neg": ["materials were meh", "Not a fan of the textbook."],
    "access/captions": ["The videos in module 3 had no transcripts and I need them. Please add transcripts.",
                        "Slides used red/green only charts that I can't tell apart. Add labels or patterns."],
    "access/accommodation-missed": ["My note-taking accommodation was ignored all semester even after I emailed twice."],
    "access/praise": ["Everything was screen-reader friendly. Thank you{wow}"],
    "org/lms-mess": ["Announcements were on {lms}, email, and in class and they said different things. Pick one place."],
    "org/schedule-changes": ["The quiz schedule kept shifting. Keep the dates from the syllabus."],
    "org/well-organized": ["Very well structured course{wow}", "Modules were clear and always posted on time{wow}"],
    "org/mixed": ["Nice layout on {lms}, but some weeks had no instructions until Sunday night."],
    "conduct/unavailable": ["{prof} never showed up to office hours and ignored {n} emails from me."],
    "conduct/disrespectful": ["The instructor laughed at a student's wrong answer. Please treat students with respect."],
    "conduct/praise": ["{prof} treated every student with respect{wow}", "Kind, available, and fair{wow}"],
    "other/looks": ["the TA is gorgeous, only reason I showed up lol", "10/10 would stare at {prof} again"],
    "other/appearance-insult": ["{prof} looks like a slob every day, gross."],
    "other/meta": ["nothing to add", "Required for my program.", "ok class", "-"],
    "other/room": ["The room had no outlets, so laptops died halfway through. A room with power would help."],
}

CONTEXT = ["", "", "", "", "", "Junior bio major here. ", "Took this as a senior. ", "Overall, ",
           "As a transfer student, ", "Honestly? ", "idk, "]
TAIL = ["", "", "", "", "", " (sorry for typos)", " That's all.", " Thanks.", ""]

PROMPTS = ["", "", "", "", "What could be improved? ", "Comments: ", "Q: What did you like most? A: ",
           "Additional feedback: ", "What should the instructor keep doing? "]


def build(rng):
    examples = []
    for theme, fam, sent, act, inapp, templates in FAMILIES:
        for i in range(PER_FAMILY):
            tpls = templates + EXTRA.get(fam, [])
            text = C.fill(rng, tpls[i % len(tpls)], SLOTS)
            ctx = C.pick(rng, CONTEXT)
            if ctx:
                text = ctx + (text[0].lower() + text[1:] if ctx.endswith(", ") else text)
            text += C.pick(rng, TAIL)
            text = C.messy(rng, text, typo_rate=0.05, p_typo=0.4)
            if sent == 0 and rng.random() < 0.15:
                text = text.upper()
            text = C.pick(rng, PROMPTS) + text
            examples.append({
                "family": fam, "group": theme,
                "state": {"comment": text},
                "gold": {"theme": theme, "sentiment": sent, "actionable": act, "inappropriate": bool(inapp)},
            })
    return examples


TEST_FAMILIES = ["instr/harsh-fair", "instr/attack-specific", "workload/sarcasm", "grading/mixed",
                 "materials/praise", "access/accommodation-missed", "org/lms-mess", "conduct/disrespectful",
                 "other/looks", "workload/manageable"]


def main():
    rng = C.rng_for(NAME, SEED)
    splits = C.write_dataset(NAME, build(rng), HERE, PREFIX, seed=SEED, test_families=TEST_FAMILIES)
    C.summary(NAME, splits)
    return splits


if __name__ == "__main__":
    main()
