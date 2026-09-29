"""Generate the he-it-helpdesk accelerator set (deterministic, stdlib only).

Each phrasing family is one kind of campus IT ticket (a category, a scope, and a timing) with fixed gold
labels. Families come in pairs where it matters: one person's Wi-Fi vs a whole building down, one
student locked out vs single sign-on down for everyone, a single projector vs lecture capture failing in
every room. Tickets are wrapped as a portal form, an email, a chat transcript, or phone notes, from a
student, faculty member, staff member, TA, or researcher, then get a noise pass. TEST holds out whole
families.

Priority rules (see README): 3 = many users fully down; 2 = a class, exam, or deadline affected right
now, or many users degraded; 1 = one person blocked; 0 = question or minor issue with a workaround.

    python datasets/accelerators/he-it-helpdesk/generate.py
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import _common as C  # noqa: E402

NAME = "he-it-helpdesk"
PREFIX = "heit"
PER_FAMILY = 24
SEED = 7070

BLDGS = ["Hale Hall", "the Science Library", "Ortega Hall", "the Student Union", "Birch Residence Hall",
         "the Engineering Annex", "Maple Commons", "the Fine Arts Center", "Lindqvist Hall", "North Tower dorm",
         "the Business School", "the Rec Center", "Cedar Hall", "the Nursing Building"]
COURSES = ["BIO 101", "CHEM 210", "MATH 152", "HIST 330", "PSYC 100", "ENGL 205", "CS 240", "ECON 201",
           "NURS 310", "STAT 250", "PHYS 121", "SOC 110", "ART 115", "ME 340"]
SLOTS = {
    "bldg": BLDGS, "course": COURSES,
    "room": lambda r: f"{C.pick(r, ['Hale', 'Ortega', 'Cedar', 'Lindqvist', 'SCI', 'ENG'])} {r.randrange(100, 450)}",
    "soon": ["in 20 minutes", "at 10am today", "in an hour", "right now", "this period", "starting at 1:30",
             "in 15 min", "today at noon"],
    "due": ["tonight at 11:59", "at midnight", "in two hours", "by 5pm today", "at 9am tomorrow morning"],
    "dur": ["since this morning", "for about an hour", "since last night", "for the past 30 minutes",
            "since around 9", "all day"],
    "many": ["everyone", "everyone on my floor", "all of us", "all my students", "the whole class",
             "most of the department", "dozens of students", "everybody in the lab"],
    "please": ["Please help.", "Thanks.", "Thank you!", "Any ideas?", "Can someone look?", "", "", "pls help",
               "Appreciate it."],
    "sw": ["the statistics package", "the CAD suite", "the campus Office license", "MATLAB-style numeric software",
           "the GIS software", "the PDF editor", "the reference manager", "the Adobe-style design suite"],
    "phone_os": ["iPhone", "Android phone", "new phone", "phone"],
}

# (category, family, outage, priority, [templates])
FAMILIES = [
    # ---------------------------------------------------------------- LMS
    ("lms", "lms/single-submit", False, 2, [
        "I can't submit my {course} assignment on the course site, the upload button just spins. It's due {due}. {please}",
        "Getting an error when I try to turn in my paper in the LMS for {course}. Due {due}!!",
        "The quiz in {course} kicked me out halfway and now it says I have no attempts left. {please}",
    ]),
    ("lms", "lms/class-wide", True, 3, [
        "{many} in {course} can't open the midterm on the course site, it says 'page not available'. The exam is {soon}.",
        "The LMS is down for {many}, nobody can log into their course sites {dur}.",
        "Students in all my sections are getting a 500 error on the course site. I teach {course} and students keep emailing me.",
    ]),
    ("lms", "lms/gradebook-question", False, 0, [
        "How do I hide the total column in my gradebook on the course site? Not urgent.",
        "Is there a way to copy last semester's {course} course site into this one? {please}",
        "Quick question: can students see rubric comments before I publish grades in the LMS?",
    ]),
    ("lms", "lms/missing-course", False, 1, [
        "I registered for {course} a week ago but it still doesn't show up in my LMS dashboard. {please}",
        "My {course} course site disappeared from my list. I can't see any of the readings. {please}",
    ]),
    ("lms", "lms/slow-degraded", True, 2, [
        "The course site is super slow for {many} today, pages take a minute to load but they do eventually load.",
        "LMS keeps timing out intermittently for {many} in the lab, refreshing works sometimes. {please}",
    ]),
    # ---------------------------------------------------------------- SSO / MFA
    ("sso_mfa", "sso/locked-out", False, 1, [
        "I got a new {phone_os} and my authenticator app didn't transfer, now I can't log in to anything. {please}",
        "My campus account is locked after too many password attempts. {please}",
        "Not getting the push notification for MFA anymore on my {phone_os}. Can't get into email or the portal.",
    ]),
    ("sso_mfa", "sso/locked-exam", False, 2, [
        "Locked out of my campus login and I have an online exam in {course} {soon}!! Please reset my MFA.",
        "Password expired and the reset page won't load, I need to log in to present {soon}. {please}",
    ]),
    ("sso_mfa", "sso/campus-down", True, 3, [
        "Single sign-on is down, {many} getting 'authentication service unavailable' {dur}.",
        "The campus login page won't load for anyone in our office, no one can get into anything. {please}",
        "MFA pushes aren't being delivered to {many}. Nobody can sign in.",
    ]),
    ("sso_mfa", "sso/password-question", False, 0, [
        "How often do I have to change my campus password? Just curious.",
        "Can I register a second device for MFA as a backup? {please}",
        "What's the policy on password managers for campus accounts?",
    ]),
    # ---------------------------------------------------------------- Wi-Fi
    ("wifi", "wifi/single-device", False, 1, [
        "My laptop won't connect to campus Wi-Fi in {bldg}, my roommate's works fine. {please}",
        "Wi-Fi keeps asking for my password on my laptop only. Other devices are ok. {please}",
        "Can't get my new game console registered on the dorm network. {please}",
    ]),
    ("wifi", "wifi/building-down", True, 3, [
        "Wi-Fi is completely down in {bldg}, {many} can't connect {dur}.",
        "No internet anywhere in {bldg}, wired or wireless. Whole building is offline.",
        "The network in {bldg} dropped for {many}, none of the access points show up anymore.",
    ]),
    ("wifi", "wifi/slow-area", True, 2, [
        "Wi-Fi in {bldg} is really slow for {many}, it works but video calls keep dropping.",
        "Spotty wireless on the third floor of {bldg} for {many}, connects and drops. {please}",
    ]),
    ("wifi", "wifi/guest-question", False, 0, [
        "How do visitors get on the guest Wi-Fi? I have a speaker coming next month.",
        "Is there Wi-Fi coverage in the outdoor quad? Just wondering.",
    ]),
    # ---------------------------------------------------------------- email
    ("email", "email/single-mailbox", False, 1, [
        "My campus email says my mailbox is full and I can't receive anything. {please}",
        "Emails from my advisor are going to junk and I can't find the setting to stop it. {please}",
        "I can't add my campus email to my {phone_os}, keeps saying account error. {please}",
    ]),
    ("email", "email/delivery-outage", True, 3, [
        "Campus email isn't delivering for {many}, messages stuck in outbox {dur}.",
        "No one in our department has received any email since 8am. Outlook-style client and web both. {please}",
    ]),
    ("email", "email/list-question", False, 0, [
        "How do I create a mailing list for my student club? {please}",
        "Can I set up an out-of-office reply for the summer? Not urgent.",
        "How do I share my calendar with the department admin?",
    ]),
    ("email", "email/deadline-send", False, 2, [
        "I need to send my application materials by email {due} and my campus email won't let me attach files. {please}",
        "Calendar invites for my thesis defense {soon} aren't going out to the committee. Help!",
    ]),
    # ---------------------------------------------------------------- software
    ("software", "software/license-request", False, 0, [
        "How do I get a license for {sw} as a grad student? {please}",
        "Is {sw} available for free to students? I'd like to install it on my laptop.",
        "Where do I download {sw} from the campus software store?",
    ]),
    ("software", "software/install-fail", False, 1, [
        "{sw} won't install on my laptop, keeps failing at 90%. {please}",
        "The license for {sw} says expired even though I renewed. Can't open my files. {please}",
    ]),
    ("software", "software/license-server-down", True, 3, [
        "{sw} says 'cannot reach license server' for {many} in the computer lab {dur}.",
        "The campus license server seems down, {sw} won't launch for anyone in our department.",
    ]),
    ("software", "software/class-lab", False, 2, [
        "The lab machines in {room} don't have {sw} installed and my {course} lab starts {soon}. {please}",
        "{sw} crashes on every lab computer in {room} when students open the class file. Lab is {soon}.",
    ]),
    # ---------------------------------------------------------------- classroom tech
    ("classroom_tech", "class/projector-now", False, 2, [
        "Projector in {room} won't turn on and my lecture starts {soon}. {please}",
        "No sound from the classroom speakers in {room}, I'm teaching {course} {soon}.",
        "The podium computer in {room} is stuck on a login loop, class is {soon}. Send someone!",
    ]),
    ("classroom_tech", "class/minor", False, 0, [
        "The wireless mic in {room} has a weak battery, it still works with the spare. Just FYI.",
        "HDMI adapter in {room} is a little loose but works if you wiggle it.",
        "Could someone update the instructions card on the podium in {room}? It's outdated.",
    ]),
    ("classroom_tech", "class/capture-many", True, 3, [
        "Lecture capture failed in every classroom in {bldg} this morning, none of the recordings exist.",
        "All the room displays in {bldg} are showing 'no signal', {many} in several classes affected.",
    ]),
    ("classroom_tech", "class/future-setup", False, 0, [
        "I need a room with lecture capture for {course} next semester. Who do I ask?",
        "Can someone show me how to use the document camera in {room} sometime next week?",
    ]),
    # ---------------------------------------------------------------- research computing
    ("research_computing", "hpc/job-stuck", False, 1, [
        "My jobs on the cluster have been pending {dur} even though the queue looks empty. {please}",
        "Getting 'disk quota exceeded' in my research storage and my pipeline stopped. {please}",
        "Can't ssh to the HPC login node from off campus anymore. {please}",
    ]),
    ("research_computing", "hpc/cluster-down", True, 3, [
        "The HPC cluster is down, {many} in our lab can't submit jobs and the scheduler isn't responding.",
        "Research storage is offline for {many}, none of the shared project drives mount {dur}.",
    ]),
    ("research_computing", "hpc/deadline", False, 2, [
        "Grant renewal figures are due {due} and my cluster job was killed at the time limit. Can I get an extension on the job?",
        "I need GPU time for my thesis results due {due} and my allocation ran out today. {please}",
    ]),
    ("research_computing", "hpc/allocation-question", False, 0, [
        "How do I request a compute allocation for a new project starting next term?",
        "Is there a way to install my own Python packages on the cluster? {please}",
        "What's the backup policy for research storage? Asking for a data management plan.",
    ]),
    # ---------------------------------------------------------------- other
    ("other", "other/printer", False, 1, [
        "The printer in {bldg} ate my print credits and didn't print. {please}",
        "My office phone has no dial tone. {please}",
        "Laptop screen cracked, need a loaner for the week. {please}",
    ]),
    ("other", "other/print-deadline", False, 2, [
        "Campus print release station in {bldg} won't take my card and my poster is due {due}!",
        "Need to print my exam for {course} {soon} and the department copier is jammed. Help!",
    ]),
    ("other", "other/phones-down", True, 3, [
        "Desk phones are down across {bldg}, no one on any floor has a dial tone.",
        "All the printers in {bldg} are offline for {many} {dur}.",
    ]),
    ("other", "other/question", False, 0, [
        "Where can I recycle an old laptop from my office?",
        "Does campus IT sell discounted hardware for students?",
    ]),
]

# Near misses: words that sound like outages but are one person, or "everyone" used loosely.
NEAR_MISS = [
    ("wifi", "nearmiss/wifi-me-only", False, 1, [
        "Is the Wi-Fi down?? It's not working for me in {bldg}, but I'm the only one here right now.",
        "Internet is out! Well, on my laptop. My phone is fine on the same network. {please}",
    ]),
    ("lms", "nearmiss/lms-everyone-loose", False, 1, [
        "Everyone says the course site works for them but I can't see my {course} grades. {please}",
        "I know the LMS is fine for the rest of my class, but my account shows no courses. {please}",
    ]),
    ("sso_mfa", "nearmiss/outage-resolved", False, 0, [
        "Earlier today login was down for everyone but it's back now. Just wanted to confirm it's fixed.",
        "Was there an outage last night? It's working this morning, just curious what happened.",
    ]),
]

TEST_FAMILIES = ["lms/single-submit", "sso/campus-down", "wifi/slow-area", "email/list-question",
                 "software/install-fail", "class/capture-many", "hpc/allocation-question", "hpc/deadline",
                 "other/printer", "nearmiss/wifi-me-only"]

ROLES = ["student", "faculty", "staff", "TA", "researcher", "grad student"]
CHANNELS = ["portal", "email", "chat", "phone"]


def wrap(rng, text):
    name, role, ch = C.person(rng), C.pick(rng, ROLES), C.pick(rng, CHANNELS)
    if ch == "portal":
        cat = C.pick(rng, ["General", "Account", "Network", "Teaching tools", "Other", "Hardware/Software"])
        return f"Submitted via portal | Role: {role} | Selected category: {cat}\nDescription: {text}"
    if ch == "email":
        subj = C.pick(rng, ["Help", "IT issue", "URGENT", "Question", "not working", "Re: ticket"])
        sig = C.pick(rng, ["", f"\n\n{name}\n{role.title()}", f"\n\n-- {C.first_name(rng)}", "\n\nSent from my phone"])
        return f"From: {C.email(rng, name, 'example.edu')}\nSubject: {subj}\n\n{text}{sig}"
    if ch == "chat":
        return (f"[chat] {C.first_name(rng)} ({role}): {text}\n[chat] agent: Thanks, looking into it."
                if rng.random() < 0.5 else f"[chat] {role}: {text}")
    return f"Phone call from {role} {name}, callback {C.phone(rng)}. Caller says: {text}"


def build(rng):
    examples = []
    for cat, fam, outage, prio, tpls in FAMILIES + NEAR_MISS:
        for i in range(PER_FAMILY):
            text = C.fill(rng, tpls[i % len(tpls)], SLOTS)
            text = C.messy(rng, text, typo_rate=0.04, p_typo=0.4)
            examples.append({"family": fam, "group": cat, "state": {"ticket": wrap(rng, text)},
                             "gold": {"category": cat, "outage": outage, "priority": prio}})
    return examples


def main():
    rng = C.rng_for(NAME, SEED)
    splits = C.write_dataset(NAME, build(rng), HERE, PREFIX, seed=SEED, test_families=TEST_FAMILIES)
    C.summary(NAME, splits)
    return splits


if __name__ == "__main__":
    main()
