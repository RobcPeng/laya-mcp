"""Use-case accelerator packs: one pack per production/POC use case, each with a synthetic training set
under datasets/accelerators/<pack name>/ (train/val/test JSONL built by that folder's generate.py).

The question wording here is the contract. The training rows carry these exact strings, so a checkpoint
fine-tuned on an accelerator set only transfers to inference that asks the same questions. Change a
wording and you must regenerate the set (python datasets/accelerators/build_all.py) and re-fine-tune.

packs.py merges PACKS into the main registry, so get_pack("support-ticket-triage") works everywhere.
"""
from .client import choice_q, noul_q, score_q

PACKS = {
    # ------------------------------------------------------------------ customer operations
    "support-ticket-triage": {
        "description": "Route a customer support ticket to a queue, score urgency, and flag churn risk, "
                       "refund requests, and tickets that need a human.",
        "state_fields": ["subject", "body"],
        "questions": {
            "queue": choice_q("Which support queue should handle the ticket in `subject` and `body`?", {
                "billing": "charges, invoices, payment methods, pricing, refunds",
                "account_access": "login problems, passwords, two-factor codes, locked or hacked accounts",
                "technical": "the product is broken, erroring, slow, or not syncing",
                "shipping": "physical orders, delivery status, damaged or missing packages, returns",
                "cancellation": "the customer wants to cancel, close the account, or downgrade the plan",
                "feature_request": "a suggestion for a new capability or an improvement",
                "how_to": "a question about how to use an existing feature",
            }),
            "urgency": score_q("How urgent is the ticket in `body`?", [
                "low: no time pressure",
                "normal: handle in the usual queue order",
                "high: the customer is blocked or losing money",
                "critical: outage, security problem, or many users affected",
            ]),
            "churn_risk": noul_q("Does `body` suggest the customer may cancel, leave, or switch to a competitor?"),
            "refund_requested": noul_q("Does `body` ask for a refund, credit, or money back?"),
            "needs_human": noul_q("Should a human agent handle `body` instead of an automated reply?"),
        },
    },
    "email-triage-phishing": {
        "description": "Sort an inbound email into a folder and flag phishing, junk marketing, whether it "
                       "needs a reply, and how time-sensitive it really is.",
        "state_fields": ["sender", "subject", "body"],
        "questions": {
            "route": choice_q("Where should the email in `subject` and `body` be filed?", {
                "action": "a person needs the recipient to do, decide, or answer something",
                "fyi": "informational update from a real contact; no action needed",
                "meeting": "scheduling, invitations, or changes to a meeting",
                "newsletter": "a newsletter or marketing email the recipient subscribed to",
                "receipt": "an order confirmation, invoice, receipt, or shipping notice",
                "junk": "phishing, scams, or unsolicited junk mail",
            }),
            "phishing": noul_q("Is the email from `sender` a phishing or scam attempt, such as a fake login "
                               "link, a request for credentials, or a fraudulent payment demand?"),
            "spam": noul_q("Is the email unsolicited advertising or junk mail, not a phishing attempt?"),
            "needs_reply": noul_q("Should the recipient write a reply to the email in `body`?"),
            "urgency": score_q("How soon does the recipient genuinely need to act on the email in `body`?", [
                "none: no action or deadline",
                "low: sometime this week",
                "high: today",
                "critical: within the hour",
            ]),
        },
    },
    # ------------------------------------------------------------------ public sector (SLED)
    "public-sector-311-intake": {
        "description": "Route a city 311 service request to the right service, catch emergencies that "
                       "belong with 911, check for a usable location, and set priority.",
        "state_fields": ["channel", "request"],
        "questions": {
            "service": choice_q("Which city service should handle the 311 request in `request`?", {
                "pothole": "potholes, cracked or sunken road surface, damaged pavement",
                "streetlight": "streetlights out, flickering, or damaged light poles",
                "trash": "missed garbage, recycling, or bulk pickup, overflowing bins, illegal dumping",
                "noise": "loud music, parties, construction noise, barking, or other noise complaints",
                "graffiti": "graffiti or vandalism painted on walls, signs, or public property",
                "water": "water main breaks, leaks, low pressure, hydrants, sewer backups, flooding drains",
                "animal": "stray, loose, injured, or dead animals, and wildlife problems",
                "parking": "illegally parked, abandoned, or blocking vehicles",
                "other": "anything that fits none of the other services",
            }),
            "emergency": noul_q("Does `request` describe an emergency that should go to 911 instead of 311, "
                                "such as a fire, a crime in progress, an injury, a gas leak, or immediate "
                                "danger to someone?"),
            "location_present": noul_q("Does `request` include a usable location, such as a street address, "
                                       "an intersection, a block, or a named landmark?"),
            "priority": score_q("What priority should the city give `request`?", [
                "routine: cosmetic or a minor inconvenience",
                "standard: fix within normal service times",
                "elevated: a safety hazard or affects many residents",
                "urgent: immediate risk to public safety",
            ]),
        },
    },
    "public-records-foia-routing": {
        "description": "Route a public records (FOIA / open records) request to the department that holds "
                       "the records, separate records requests from complaints, flag PII, and size the work.",
        "state_fields": ["request"],
        "questions": {
            "department": choice_q("Which department most likely holds the records sought in `request`?", {
                "police": "incident and arrest reports, body camera or dashcam video, 911 calls, crash reports",
                "fire_ems": "fire incident reports, EMS runs, fire inspections, fire code violations",
                "public_works": "streets, water and sewer, utilities, traffic, capital construction projects",
                "planning_zoning": "building permits, zoning cases, code enforcement, inspections, site plans",
                "finance": "budgets, contracts, bids, purchasing, vendor payments, audits",
                "human_resources": "employee salaries, personnel files, job postings, hiring, discipline",
                "clerk": "council agendas and minutes, ordinances, resolutions, elections, city records",
                "parks": "parks, recreation programs, facility rentals, trails",
                "health": "restaurant and food inspections, environmental health, disease reports",
            }),
            "request_type": choice_q("What kind of submission is `request`?", {
                "records_request": "asks for copies of or access to existing public records",
                "complaint": "complains about a service, an employee, or a decision",
                "service_request": "asks the city to fix, do, or change something",
                "question": "asks a general question that does not need records",
            }),
            "contains_pii": noul_q("Does `request` include personal data about a private individual, such as a "
                                   "home address, date of birth, phone number, or government ID number?"),
            "complexity": score_q("How much work will fulfilling `request` take?", [
                "simple: one known document",
                "moderate: a few records from one office",
                "complex: many records, a long date range, or several offices",
                "extensive: large volume that needs heavy review or redaction",
            ]),
        },
    },
    "benefits-eligibility-intake": {
        "description": "Screen a public benefits inquiry: which program fits, is there an urgent hardship, "
                       "and is the intake missing information a caseworker needs.",
        "state_fields": ["message"],
        "questions": {
            "program": choice_q("Which assistance program best fits the need described in `message`?", {
                "snap": "food assistance, groceries, food stamps, EBT",
                "medicaid": "health coverage, doctor visits, prescriptions, medical bills",
                "unemployment": "income after losing a job or having work hours cut",
                "housing": "rent help, eviction, shelter, homelessness, housing vouchers",
                "childcare": "help paying for child care or daycare so a parent can work or study",
                "energy_assistance": "heating, cooling, electric, or gas bills and utility shutoffs",
                "cash_assistance": "general monthly cash support for a low-income family",
            }),
            "urgent_hardship": noul_q("Does `message` describe an urgent hardship, such as an eviction or "
                                      "shutoff notice, no food in the home, homelessness, or a medical "
                                      "emergency?"),
            "missing_info": noul_q("Is `message` missing any of the details a caseworker needs to start an "
                                   "application: household size, monthly income, and county of residence?"),
        },
    },
    # ------------------------------------------------------------------ trust and safety
    "content-moderation": {
        "description": "Moderate user-generated text: toxicity, targeted harassment, threats, spam, and an "
                       "overall severity for the action to take.",
        "state_fields": ["text"],
        "questions": {
            "toxic": noul_q("Is `text` insulting, demeaning, or profane toward a person or group?"),
            "harassment": noul_q("Does `text` target a specific person with personal attacks, intimidation, "
                                 "or humiliation?"),
            "threat": noul_q("Does `text` threaten violence or harm against someone?"),
            "spam": noul_q("Is `text` spam, such as unsolicited ads, scam links, or repetitive promotion?"),
            "severity": score_q("How severe is `text` for a moderator?", [
                "none: acceptable",
                "low: rude or off-topic but allowed",
                "medium: remove the content",
                "high: remove it and escalate or suspend the account",
            ]),
        },
    },
    # ------------------------------------------------------------------ AI / LLM infrastructure
    "rag-relevance-filter": {
        "description": "Filter or rerank retrieved passages for RAG: is the passage on topic, does it answer "
                       "the query, and how relevant is it.",
        "state_fields": ["query", "passage"],
        "questions": {
            "relevant": noul_q("Is `passage` about the same subject as `query`?"),
            "answers": noul_q("Does `passage` contain the information needed to answer `query`?"),
            "relevance": score_q("How useful is `passage` for answering `query`?", [
                "irrelevant: different subject",
                "related: same subject but does not help answer",
                "partial: answers part of the query",
                "complete: fully answers the query",
            ]),
        },
    },
    "llm-model-router": {
        "description": "Route a prompt to a cheap or strong model: difficulty, domain, whether it needs tools, "
                       "and whether it carries data that should stay on a private model.",
        "state_fields": ["prompt"],
        "questions": {
            "difficulty": score_q("How hard is the task in `prompt` for a language model?", [
                "trivial: a greeting, lookup, or one-line edit",
                "easy: a short, well-known task",
                "moderate: multi-step reasoning or longer writing",
                "hard: expert reasoning, long code, or careful analysis",
            ]),
            "domain": choice_q("What is the main domain of `prompt`?", {
                "coding": "writing, fixing, or explaining code, SQL, or scripts",
                "math": "calculations, proofs, statistics, or quantitative puzzles",
                "writing": "drafting, editing, or rewriting prose, emails, or marketing copy",
                "data_analysis": "analyzing tables, metrics, spreadsheets, or datasets",
                "knowledge": "factual questions or explanations about the world or a subject",
                "translation": "translating text between languages",
                "chitchat": "greetings, small talk, or casual conversation",
            }),
            "needs_tools": noul_q("Does answering `prompt` require live data, web search, running code, or "
                                  "access to files?"),
            "is_sensitive": noul_q("Does `prompt` contain personal, confidential, or regulated data, such as "
                                   "health records, customer details, credentials, or internal financials?"),
        },
    },
    # ------------------------------------------------------------------ security and finance ops
    "security-incident-triage": {
        "description": "Triage a security alert: category, likely true positive, severity, and whether to "
                       "escalate to incident response now.",
        "state_fields": ["source", "alert"],
        "questions": {
            "category": choice_q("What kind of security event is described in `alert`?", {
                "malware": "malicious files, ransomware, trojans, suspicious processes or scripts",
                "phishing": "malicious emails, lure links, or credential-harvesting pages",
                "account_compromise": "brute force, password spraying, impossible travel, stolen sessions",
                "data_exfiltration": "large or unusual transfers of data to outside destinations",
                "reconnaissance": "port scans, directory enumeration, or probing of systems",
                "denial_of_service": "traffic floods or resource exhaustion that degrade a service",
                "misconfiguration": "exposed storage, open ports, weak settings, or missing patches",
                "policy_violation": "unapproved software, shadow IT, or acceptable-use violations",
            }),
            "true_positive": noul_q("Is `alert` likely a real malicious or unauthorized event rather than a "
                                    "false positive or approved activity?"),
            "severity": score_q("How severe is the event in `alert`?", [
                "informational: no action needed",
                "low: minor, handle in normal work",
                "medium: investigate today",
                "high: active threat to important systems or data",
                "critical: confirmed breach or widespread impact",
            ]),
            "needs_escalation": noul_q("Should `alert` be escalated to the incident response team right now?"),
        },
    },
    "invoice-ap-exceptions": {
        "description": "Accounts payable three-way-match exceptions: compare an invoice with its purchase "
                       "order and receipt, name the exception, and score fraud risk.",
        "state_fields": ["invoice", "purchase_order"],
        "questions": {
            "exception": choice_q("What exception, if any, does `invoice` have compared with `purchase_order`?", {
                "clean": "the invoice matches the purchase order and receipt within tolerance",
                "price_mismatch": "unit prices are higher than the purchase order allows",
                "quantity_mismatch": "billed quantity differs from what was ordered or received",
                "missing_po": "no valid purchase order is referenced or on file",
                "duplicate": "the same invoice appears to have been submitted or paid already",
                "bank_change": "the vendor's payment or bank details changed",
                "math_error": "line totals, tax, or the invoice total do not add up",
            }),
            "needs_approval": noul_q("Does `invoice` need manual review or approval before it is paid?"),
            "fraud_risk": score_q("How likely is `invoice` to be fraudulent?", [
                "low: ordinary invoice",
                "moderate: unusual and worth a check",
                "high: strong signs of fraud",
            ]),
        },
    },
    # ------------------------------------------------------------------ data engineering
    "data-quality-record-check": {
        "description": "Check a single record against its schema rules (lakehouse ingest/quarantine): valid "
                       "or not, which issue, and personal data leaking into free-text fields.",
        "state_fields": ["schema", "record"],
        "questions": {
            "is_valid": noul_q("Does `record` satisfy every rule in `schema`?"),
            "issue": choice_q("What is the main problem with `record` according to `schema`?", {
                "none": "the record passes every rule",
                "missing_value": "a required field is missing, null, or empty",
                "wrong_type": "a field has the wrong data type, like text where a number belongs",
                "out_of_range": "a value is outside its allowed range or not an allowed value",
                "bad_format": "a date, email, phone, code, or ID is malformed",
                "inconsistent": "fields contradict each other, like an end date before the start date",
            }),
            "pii_in_text": noul_q("Does a free-text field in `record`, such as notes or comments, contain "
                                  "personal data like an email address, phone number, or ID number?"),
        },
    },
    # ------------------------------------------------------------------ sales
    "sales-lead-qualification": {
        "description": "BANT-style lead qualification: budget, authority, need, timing, pipeline stage, "
                       "and overall fit for the product.",
        "state_fields": ["product", "lead"],
        "questions": {
            "budget": noul_q("Does `lead` indicate that money is available or approved for a purchase?"),
            "authority": noul_q("Is the person in `lead` a decision maker or directly involved in the "
                                "buying decision?"),
            "need": noul_q("Does `lead` describe a concrete problem that `product` solves?"),
            "timing": noul_q("Does `lead` mention a plan to buy or start within the next six months?"),
            "stage": choice_q("What sales stage is the lead in `lead` at?", {
                "not_a_fit": "wrong audience, no relevant need, a student, a vendor pitch, or a job seeker",
                "research": "early learning or browsing with no active project",
                "evaluating": "actively comparing options, requesting demos, trials, or pricing",
                "ready_to_buy": "asking for a quote, contract, or procurement steps",
            }),
            "fit": score_q("How good a fit is `lead` for `product`?", [
                "poor: not worth pursuing",
                "weak: nurture, follow up later",
                "good: worth a discovery call",
                "strong: prioritize now",
            ]),
        },
    },
}

# ---------------------------------------------------------------------- higher education (SLED)
# Student-facing sets route to people. None of them decide anything about a student on their own.
# he-early-alert and he-safety-escalation in particular are recall-first routing aids for staff.
HE_PACKS = {
    "he-student-services-routing": {
        "description": "Route a student's message to the campus office that handles it, score urgency, and "
                       "flag messages that need a staff member rather than an FAQ answer.",
        "state_fields": ["message"],
        "questions": {
            "office": choice_q("Which campus office should handle `message`?", {
                "registrar": "registration, enrollment verification, transcripts, grades on record, graduation",
                "financial_aid": "FAFSA, grants, loans, scholarships, aid eligibility and awards",
                "student_accounts": "tuition bills, payments, payment plans, refunds of a balance, account holds",
                "admissions": "applying, admission decisions, deposits, transfer applications",
                "housing": "residence halls, roommates, room assignments, maintenance in housing, meal plans",
                "it_help": "passwords, campus login, email, Wi-Fi, the learning management system",
                "advising": "choosing courses, degree requirements, changing majors, academic plans",
                "accessibility": "disability accommodations and accessibility services",
                "counseling": "mental health, counseling appointments, emotional support",
                "library": "library accounts, books, research help, study rooms, interlibrary loan",
                "other": "parking, dining, athletics, clubs, or anything else",
            }),
            "urgency": score_q("How urgent is `message`?", [
                "low: a general question",
                "normal: needs an answer within a few days",
                "high: a deadline, hold, or lost access is blocking the student now",
                "critical: a safety concern or crisis",
            ]),
            "needs_human": noul_q("Should a staff member respond to `message` personally instead of an "
                                  "automated answer or FAQ link?"),
        },
    },
    "he-financial-aid-triage": {
        "description": "Triage financial aid messages by topic, flag near deadlines, and flag messages that "
                       "carry sensitive financial or identity details.",
        "state_fields": ["message"],
        "questions": {
            "topic": choice_q("What financial aid topic is `message` about?", {
                "verification": "verification requests, tax transcripts, documents the aid office asked for",
                "sap_appeal": "satisfactory academic progress, aid suspension, or an appeal to regain aid",
                "dependency_override": "independent status, unusual family circumstances, no parent information",
                "award_letter": "understanding or changing an aid offer or award package",
                "disbursement": "when aid pays out, refund checks, aid applied to the bill",
                "work_study": "federal work-study jobs, hours, or paychecks",
                "loans": "student or parent loans, loan counseling, promissory notes, borrowing limits",
                "scholarships": "scholarship applications, renewals, or outside scholarships",
                "other": "anything else",
            }),
            "deadline_sensitive": noul_q("Does `message` involve a deadline or date that is close, such as a "
                                         "payment due date, an appeal deadline, or the start of the term?"),
            "sensitive_info": noul_q("Does `message` include sensitive financial or identity details, such as "
                                     "income figures, tax information, bank account numbers, or a Social "
                                     "Security number?"),
        },
    },
    "he-admissions-inquiry": {
        "description": "Classify an admissions inquiry by funnel stage and topic, and flag hot leads.",
        "state_fields": ["message"],
        "questions": {
            "stage": choice_q("Where in the admissions process is the person writing `message`?", {
                "prospect": "has not applied yet; exploring or planning to apply",
                "applicant": "has applied and is waiting for a decision",
                "admitted": "has been admitted and has not committed yet",
                "deposited": "has paid the enrollment deposit or committed to attend",
                "other": "a current student, alum, counselor, vendor, or someone outside the process",
            }),
            "topic": choice_q("What is `message` mainly asking about?", {
                "application_status": "whether an application is complete or when a decision comes",
                "requirements": "admission requirements, deadlines, essays, or documents to submit",
                "transfer_credit": "how credits from another college will transfer",
                "international": "international applicants, visas, I-20s, English proficiency",
                "test_policy": "SAT, ACT, test-optional policy, or score reporting",
                "campus_visit": "tours, visit days, open houses, or meeting someone on campus",
                "cost_aid": "tuition, cost of attendance, scholarships, or financial aid",
            }),
            "hot_lead": noul_q("Does `message` show strong intent to apply or enroll soon, such as a specific "
                               "term, a visit request, or asking about next steps to commit?"),
        },
    },
    "he-early-alert": {
        "description": "Decision support for advisors: read an advisor or faculty early-alert note and flag "
                       "academic, attendance, financial, and wellbeing signals. Routes to a human; never acts "
                       "on a student.",
        "state_fields": ["note"],
        "questions": {
            "academic_risk": noul_q("Does `note` describe academic risk, such as failing grades, missing "
                                    "assignments, or falling behind?"),
            "attendance": noul_q("Does `note` describe missed classes or poor attendance?"),
            "financial_stress": noul_q("Does `note` mention financial stress, such as trouble paying tuition, "
                                       "rent, or food, or needing to work more hours?"),
            "wellbeing_concern": noul_q("Does `note` suggest a wellbeing concern, such as stress, isolation, "
                                        "illness, or a change in mood or behavior?"),
            "risk": score_q("How much advisor support does the student described in `note` need?", [
                "none: on track",
                "low: a check-in would help",
                "moderate: reach out this week",
                "high: reach out promptly and refer to support services",
            ]),
        },
    },
    "he-safety-escalation": {
        "description": "High-recall routing of student messages that need a trained person now (possible "
                       "self-harm, threats of violence, sexual misconduct disclosures, medical emergencies) "
                       "versus ordinary stress. Routing only: people and crisis resources respond.",
        "state_fields": ["message"],
        "questions": {
            "escalate_now": noul_q("Does `message` need a trained person to respond right away because of "
                                   "possible self-harm, a threat of violence, sexual misconduct, or a medical "
                                   "emergency?"),
            "category": choice_q("Which best describes `message`?", {
                "self_harm": "thoughts of suicide or self-harm, or saying goodbye",
                "violence_threat": "a threat or plan to hurt other people, or fear of someone who threatened them",
                "sexual_misconduct": "sexual assault, harassment, stalking, or dating violence (Title IX)",
                "medical_emergency": "someone is hurt, unconscious, overdosing, or in medical danger now",
                "stress_venting": "ordinary stress, frustration, or exaggeration with no safety risk",
                "routine": "an ordinary question or message",
            }),
        },
    },
    "he-course-evaluation-comments": {
        "description": "Code open-ended course evaluation comments by theme and sentiment, and flag actionable "
                       "feedback and inappropriate remarks.",
        "state_fields": ["comment"],
        "questions": {
            "theme": choice_q("What is the main theme of `comment`?", {
                "instruction": "how well the instructor explains and teaches",
                "workload": "the amount of work, pace, or time the course takes",
                "grading": "grading fairness, clarity of rubrics, or feedback on work",
                "materials": "textbooks, readings, slides, videos, or other course materials",
                "accessibility": "access barriers, captions, accommodations, or formats",
                "organization": "course structure, schedule, deadlines, or the LMS site layout",
                "instructor_conduct": "the instructor's professionalism, respect, or availability",
                "other": "anything else",
            }),
            "sentiment": score_q("What is the sentiment of `comment`?", [
                "very negative", "negative", "mixed or neutral", "positive", "very positive"]),
            "actionable": noul_q("Does `comment` give specific feedback the instructor could act on?"),
            "inappropriate": noul_q("Does `comment` contain a personal attack, insult, or inappropriate remark "
                                    "about the instructor or anyone else?"),
        },
    },
    "he-ferpa-sensitive": {
        "description": "DLP for education records: does text contain FERPA-protected information about an "
                       "identifiable student (versus directory information), and what kind.",
        "state_fields": ["text"],
        "questions": {
            "protected_record": noul_q("Does `text` contain FERPA-protected education record information about "
                                       "an identifiable student, such as grades, GPA, discipline, financial aid, "
                                       "disability information, or a student ID or SSN tied to the student?"),
            "record_type": choice_q("What kind of student information does `text` contain?", {
                "grades": "grades, GPA, transcripts, test scores, or academic standing of a named student",
                "discipline": "conduct or disciplinary records of a named student",
                "financial": "financial aid, account balances, or family finances of a named student",
                "health_disability": "disability, accommodation, counseling, or medical information about a named student",
                "identifiers": "a student ID number or SSN tied to a named student",
                "directory_only": "only directory information, like name, major, enrollment status, or degrees",
                "none": "no information about an identifiable student",
            }),
        },
    },
    "he-accommodation-request-routing": {
        "description": "Route disability accommodation requests by type, and flag mentioned documentation and "
                       "time-sensitive requests.",
        "state_fields": ["request"],
        "questions": {
            "type": choice_q("What kind of accommodation does `request` ask for?", {
                "testing": "extended time, a separate room, or other exam arrangements",
                "housing": "a single room, accessible room, or other housing arrangement",
                "course_materials": "alternative formats, captions, transcripts, or accessible materials",
                "attendance": "flexibility with attendance or deadlines because of a condition",
                "animal": "a service animal or an emotional support animal",
                "other": "parking, dining, note-taking, lab access, or anything else",
            }),
            "documentation_mentioned": noul_q("Does `request` mention documentation, such as a doctor's "
                                              "letter, diagnosis paperwork, or an existing accommodation letter?"),
            "time_sensitive": noul_q("Is `request` time-sensitive, such as an exam, move-in, or deadline in the "
                                     "next two weeks?"),
        },
    },
    "he-it-helpdesk": {
        "description": "Campus IT help desk triage: category, whether many users are affected, and priority.",
        "state_fields": ["ticket"],
        "questions": {
            "category": choice_q("Which IT area does `ticket` belong to?", {
                "lms": "the learning management system: course sites, assignments, quizzes, gradebook",
                "sso_mfa": "campus login, single sign-on, passwords, multi-factor authentication",
                "wifi": "wireless or wired network access on campus",
                "email": "campus email, calendars, mailing lists",
                "software": "software licenses, installs, and campus software downloads",
                "classroom_tech": "projectors, lecture capture, microphones, and classroom computers",
                "research_computing": "HPC clusters, research storage, compute allocations, research software",
                "other": "printing, phones, hardware, or anything else",
            }),
            "outage": noul_q("Does `ticket` describe an outage or problem affecting many users rather than one "
                             "person?"),
            "priority": score_q("What priority should `ticket` get?", [
                "low: a question or minor issue with a workaround",
                "medium: one person is blocked from normal work",
                "high: a class, exam, or deadline is affected right now",
                "critical: campus-wide or many users are down",
            ]),
        },
    },
    "he-research-admin": {
        "description": "Sponsored research office email triage: topic and upcoming deadlines.",
        "state_fields": ["email"],
        "questions": {
            "topic": choice_q("What sponsored research topic is `email` about?", {
                "proposal": "preparing, routing, or submitting a grant proposal",
                "budget": "budget questions, rates, indirect costs, or whether a cost is allowable",
                "subaward": "subawards or subcontracts to or from another institution",
                "compliance": "IRB, animal care, conflict of interest, export control, or research security",
                "effort": "effort reporting or effort certification",
                "award_setup": "a new award notice, account setup, or award terms",
                "closeout": "final reports, final invoices, or closing out an award",
                "other": "anything else",
            }),
            "deadline": noul_q("Does `email` mention an upcoming sponsor or internal deadline?"),
        },
    },
}
PACKS.update(HE_PACKS)
