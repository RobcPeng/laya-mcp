"""Generate the rag-relevance-filter accelerator set (deterministic, stdlib only).

A small invented knowledge base: 6 domains x 4 entities x 3 attributes. Every attribute of an entity has
2-3 hand-written question phrasings and one answer passage sentence. Rows pair a query with a passage
built from those facts, so the gold label follows from which facts the passage contains:

    complete (3)  the passage states every fact the query asks for
    partial  (2)  a two-part query where the passage states only one of the two facts
    related  (1)  same entity but a different attribute, or the same attribute of a sibling entity
    irrelevant(0) another domain, or a keyword-overlap distractor that shares words but not the subject

relevant = relevance >= 1; answers = relevance == 3. Passages are rendered as retrieved chunks (doc
headers, breadcrumbs, FAQ layout, bullet fragments, a trailing cut-off sentence). TEST holds out one whole
domain (the health-plan FAQ) plus one entity from every other domain.

    python datasets/accelerators/rag-relevance-filter/generate.py
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import _common as C  # noqa: E402

NAME = "rag-relevance-filter"
PREFIX = "rag"
SEED = 707

# domain -> {"doc": [doc titles], "distractors": [keyword-overlap sentences from other subjects],
#            "entities": {entity_id: {"name": display name, "attrs": {attr: (questions, answer)}}}}
# Every entity in a domain uses the same attribute keys so a sibling's answer is a lexical near-miss.
KB = {
    "hr": {
        "doc": ["Employee Handbook", "People Team Policies", "HR Policy Library", "Benefits Guide 2025"],
        "distractors": [
            "The Leave No Trace program asks park visitors to pack out everything they bring in.",
            "Remote sensing data from the satellite is processed in batches every six hours.",
            "Tuition at the state university rose four percent this year according to the regents' report.",
            "Paid parking is enforced downtown Monday through Saturday from 8 a.m. to 6 p.m.",
            "The leave-behind brochure summarizes the product roadmap for prospective customers.",
            "Time off between races lets the engine cool before the next heat.",
        ],
        "entities": {
            "parental-leave": {"name": "parental leave", "attrs": {
                "amount": (["How many weeks of parental leave do employees get?",
                            "how long is paid parental leave",
                            "What's the parental leave length for new parents?"],
                           "Eligible employees receive 16 weeks of fully paid parental leave, which may be taken within 12 months of a birth or adoption."),
                "eligibility": (["Who is eligible for parental leave?",
                                 "do I qualify for parental leave if I just started",
                                 "What are the eligibility rules for parental leave?"],
                                "Parental leave is available to full-time and part-time employees after 90 days of continuous employment, regardless of gender."),
                "process": (["How do I request parental leave?",
                             "what's the process to apply for parental leave",
                             "Where do I submit a parental leave request?"],
                            "To request parental leave, submit the Leave Request form in the HR portal at least 30 days before your planned start date and notify your manager."),
            }},
            "pto": {"name": "paid time off (PTO)", "attrs": {
                "amount": (["How many PTO days do we get per year?",
                            "what's the annual PTO allowance",
                            "How much paid time off do full-time staff accrue?"],
                           "Full-time employees accrue 20 days of PTO per year, accrued each pay period; part-time employees accrue on a prorated basis."),
                "eligibility": (["Can PTO be carried over to next year?",
                                 "is there a PTO carryover limit",
                                 "What happens to unused PTO at year end?"],
                                "Up to 5 unused PTO days carry over into the next calendar year; any balance above 5 days is forfeited on January 1."),
                "process": (["How do I book PTO?",
                             "where do I put in a time off request",
                             "What is the process for requesting vacation days?"],
                            "Book PTO in the time-tracking tool under Time Off > New Request; requests of more than 3 consecutive days need manager approval two weeks ahead."),
            }},
            "remote-work": {"name": "remote work", "attrs": {
                "amount": (["How many days a week can I work remotely?",
                            "what's the remote work limit per week",
                            "Is there a cap on work-from-home days?"],
                           "Hybrid employees may work remotely up to 3 days per week; the other 2 days are anchor days in the office."),
                "eligibility": (["Who can work fully remote?",
                                 "am I eligible for a fully remote arrangement",
                                 "What are the criteria for a remote work agreement?"],
                                "Fully remote arrangements require director approval and are limited to roles that do not need on-site equipment or in-person customer contact."),
                "process": (["How do I set up a remote work agreement?",
                             "what's the process to go remote",
                             "Which form do I use to request remote work?"],
                            "Submit a Remote Work Agreement through the HR portal; your manager and director sign it and it is reviewed every 12 months."),
            }},
            "tuition": {"name": "tuition reimbursement", "attrs": {
                "amount": (["What is the tuition reimbursement cap?",
                            "how much tuition does the company pay back per year",
                            "Max annual tuition reimbursement?"],
                           "The tuition reimbursement program covers up to $5,250 per calendar year for approved courses."),
                "eligibility": (["Which courses qualify for tuition reimbursement?",
                                 "who can use tuition reimbursement",
                                 "Do I qualify for tuition assistance?"],
                                "Courses must be job-related or part of a degree program relevant to your role, and you must have completed 6 months of employment."),
                "process": (["How do I get reimbursed for tuition?",
                             "what's the process to claim tuition reimbursement",
                             "When do I submit grades for tuition reimbursement?"],
                            "Get pre-approval before the course starts, then submit your receipt and a passing grade (C or better) within 60 days of course completion."),
            }},
        },
    },
    "product": {
        "doc": ["Brightline Support Center", "Kestrel Home Help Docs", "Product Manual", "Knowledge Base Article"],
        "distractors": [
            "The warranty deed transfers the property with a guarantee of clear title.",
            "Factory reset of expectations: our quarterly offsite focused on planning.",
            "The router table in the woodshop needs a new fence and a dust collection port.",
            "A smart plug-in hybrid can drive about 40 miles on electric power alone.",
            "Thermostat wafers in a car engine open at around 195 degrees Fahrenheit.",
            "The capacity of the stadium was expanded to 52,000 seats in the renovation.",
        ],
        "entities": {
            "b200": {"name": "Brightline B200 router", "attrs": {
                "warranty": (["What is the warranty on the B200 router?",
                              "how long is the Brightline B200 warranty",
                              "Is the B200 still under warranty after 18 months?"],
                             "The Brightline B200 router carries a 1-year limited hardware warranty from the date of purchase."),
                "reset": (["How do I factory reset the B200?",
                           "b200 router reset steps",
                           "How can I restore the Brightline B200 to default settings?"],
                          "To factory reset the B200, hold the recessed Reset button on the back for 10 seconds until the status light blinks amber, then wait 3 minutes."),
                "capacity": (["How many devices can the B200 handle?",
                              "max connected devices on the Brightline B200",
                              "Will the B200 support 40 devices?"],
                             "The B200 supports up to 32 simultaneously connected devices across its 2.4 GHz and 5 GHz bands."),
            }},
            "b400": {"name": "Brightline B400 mesh router", "attrs": {
                "warranty": (["What is the warranty on the B400?",
                              "how long is the Brightline B400 mesh warranty",
                              "Does the B400 mesh router have a 3-year warranty?"],
                             "The Brightline B400 mesh router is covered by a 3-year limited warranty, extendable to 5 years with registration."),
                "reset": (["How do I reset the B400 mesh system?",
                           "b400 factory reset",
                           "How do I restore defaults on a Brightline B400 node?"],
                          "To reset a B400 node, open the Brightline app, choose the node, and tap Remove and Reset; a physical reset needs the pinhole button held for 15 seconds."),
                "capacity": (["How many devices can a B400 mesh network support?",
                              "B400 max clients",
                              "What's the device limit on the Brightline B400?"],
                             "A B400 mesh network supports up to 150 connected devices, with up to 60 per node."),
            }},
            "thermostat": {"name": "Kestrel smart thermostat", "attrs": {
                "warranty": (["What's the warranty on the Kestrel thermostat?",
                              "kestrel smart thermostat warranty length",
                              "Is the Kestrel thermostat covered for 2 years?"],
                             "The Kestrel smart thermostat includes a 2-year limited warranty covering defects in materials and workmanship."),
                "reset": (["How do I reset the Kestrel thermostat?",
                           "kestrel thermostat factory reset",
                           "How do I wipe my Kestrel thermostat before selling it?"],
                          "To reset the Kestrel thermostat, press and hold the dial for 10 seconds, choose Settings > Reset > All Settings, and confirm."),
                "capacity": (["How many temperature sensors can the Kestrel thermostat use?",
                              "max remote sensors for kestrel thermostat",
                              "Can I pair 8 room sensors with the Kestrel?"],
                             "The Kestrel smart thermostat can pair with up to 6 remote room sensors and average their readings."),
            }},
            "plug": {"name": "Kestrel smart plug", "attrs": {
                "warranty": (["What's the warranty on the Kestrel smart plug?",
                              "kestrel plug warranty",
                              "How long is the smart plug covered?"],
                             "Kestrel smart plugs have a 1-year limited warranty; replacements ship after a photo of the serial number is submitted."),
                "reset": (["How do I reset the Kestrel smart plug?",
                           "smart plug won't connect, how to factory reset",
                           "Reset steps for a Kestrel plug?"],
                          "To reset a Kestrel smart plug, hold the power button for 12 seconds until the LED flashes blue and red, then set it up again in the app."),
                "capacity": (["What's the max load on the Kestrel smart plug?",
                              "how many watts can the Kestrel plug handle",
                              "Can the Kestrel plug run a space heater?"],
                             "The Kestrel smart plug is rated for 15 amps / 1,800 watts continuous load; do not use it with loads above that rating."),
            }},
        },
    },
    "dataeng": {
        "doc": ["Lakehouse Platform Docs", "Data Engineering Guide", "Table Format Reference", "Pipeline Runbook"],
        "distractors": [
            "Time travel stories were popular in science fiction magazines of the 1950s.",
            "The vacuum cleaner's HEPA filter should be replaced every six months.",
            "Evolution of the schema of a novel: how the plot outline changed over three drafts.",
            "Partitions in the office were removed to create an open floor plan.",
            "Checkpoints on the highway were set up for the holiday weekend.",
            "Z-order in the drawing app controls which shape appears on top.",
        ],
        "entities": {
            "time-travel": {"name": "table time travel", "attrs": {
                "what": (["What is time travel on a table?",
                          "explain table time travel",
                          "What does time travel let me do with a lakehouse table?"],
                         "Time travel lets you query a table as it existed at an earlier version or timestamp, using the transaction log to reconstruct older snapshots."),
                "default": (["How far back can I time travel by default?",
                             "default retention for time travel",
                             "What is the default log retention period for table history?"],
                            "By default, table history is kept for 30 days of log retention, and deleted data files are kept for 7 days, which limits how far back time travel can reach."),
                "how": (["How do I query an older version of a table?",
                         "syntax to read a table at a previous version",
                         "How do I use VERSION AS OF?"],
                        "Query an older snapshot with SELECT * FROM my_table VERSION AS OF 12, or TIMESTAMP AS OF '2025-01-15' for a point in time."),
            }},
            "vacuum": {"name": "the VACUUM command", "attrs": {
                "what": (["What does VACUUM do?",
                          "explain the vacuum command for tables",
                          "Why would I run VACUUM on a table?"],
                         "VACUUM removes data files that are no longer referenced by the table and are older than the retention threshold, reclaiming storage."),
                "default": (["What is the default VACUUM retention?",
                             "vacuum default retention hours",
                             "How old must files be before VACUUM deletes them by default?"],
                            "The default VACUUM retention threshold is 7 days (168 hours); running with a shorter window requires disabling a safety check."),
                "how": (["How do I run VACUUM with a custom retention?",
                         "vacuum syntax retain hours",
                         "How do I vacuum a table keeping 10 days of files?"],
                        "Run VACUUM my_table RETAIN 240 HOURS to keep 10 days of unreferenced files; add DRY RUN first to list what would be deleted."),
            }},
            "schema-evolution": {"name": "schema evolution", "attrs": {
                "what": (["What is schema evolution?",
                          "explain schema evolution on writes",
                          "What does schema evolution do when new columns arrive?"],
                         "Schema evolution lets a write add new columns to the target table automatically instead of failing on a schema mismatch."),
                "default": (["Is schema evolution on by default?",
                             "default behavior when a write has extra columns",
                             "What happens by default if my DataFrame has a new column?"],
                            "Schema evolution is off by default: schema enforcement rejects writes whose columns do not match the table, and the write fails with a mismatch error."),
                "how": (["How do I enable schema evolution?",
                         "option to merge schema on write",
                         "How do I turn on mergeSchema?"],
                        "Enable it per write with .option(\"mergeSchema\", \"true\"), or for MERGE statements set the session's auto-merge configuration to true."),
            }},
            "partitioning": {"name": "table partitioning", "attrs": {
                "what": (["What is table partitioning?",
                          "explain partitioning a table",
                          "Why partition a lakehouse table?"],
                         "Partitioning splits a table's files into folders by the values of one or more columns so queries that filter on those columns can skip whole folders."),
                "default": (["When should I avoid partitioning?",
                             "is partitioning recommended for small tables",
                             "What's the rule of thumb for partition size?"],
                            "Avoid partitioning tables under about 1 TB, and avoid high-cardinality partition columns; each partition should hold at least 1 GB of data."),
                "how": (["How do I create a partitioned table?",
                         "partition by syntax",
                         "How do I write a DataFrame partitioned by date?"],
                        "Create one with CREATE TABLE events (...) PARTITIONED BY (event_date), or write with df.write.partitionBy(\"event_date\")."),
            }},
        },
    },
    "civic": {
        "doc": ["City Services Guide", "Residents' FAQ", "County Programs Handbook", "City Code Summary"],
        "distractors": [
            "The permit for the parking garage expansion was approved by the planning commission.",
            "Bulk buying clubs let families split large packages of groceries.",
            "Library science programs train archivists and records managers.",
            "Property of the museum includes 4,000 paintings and a sculpture garden.",
            "The fee schedule for the private tennis club changes each spring.",
            "Deferral of the band's tour dates was announced on its website.",
        ],
        "entities": {
            "tax-deferral": {"name": "the senior property tax deferral program", "attrs": {
                "eligibility": (["Who qualifies for the senior property tax deferral?",
                                 "eligibility for senior property tax deferral",
                                 "Can a 62-year-old homeowner get the tax deferral?"],
                                "Homeowners aged 65 or older, or with a qualifying disability, who own and live in the home and have household income under $48,000 qualify for the deferral."),
                "fee": (["Is there interest on deferred property taxes?",
                         "what does the senior tax deferral cost",
                         "What interest rate applies to deferred taxes?"],
                        "Deferred taxes accrue simple interest at 5% per year, and the total becomes a lien on the property that is repaid when the home is sold."),
                "apply": (["How do I apply for the property tax deferral?",
                           "where to apply for senior tax deferral",
                           "What's the deadline for the tax deferral application?"],
                          "Apply to the County Treasurer's office by April 1 each year with proof of age, proof of income, and a copy of the deed."),
            }},
            "parking-permit": {"name": "residential parking permits", "attrs": {
                "eligibility": (["Who can get a residential parking permit?",
                                 "am I eligible for a neighborhood parking permit",
                                 "Can renters get residential parking permits?"],
                                "Residents, including renters, who live on a block inside a designated permit zone can get a permit; vehicles must be registered at that address."),
                "fee": (["How much is a residential parking permit?",
                         "residential permit cost",
                         "What does a second parking permit cost?"],
                        "The first residential parking permit costs $35 per year and each additional vehicle permit costs $50, up to 3 permits per household."),
                "apply": (["How do I apply for a residential parking permit?",
                           "where to get a parking permit for my street",
                           "What documents do I need for a parking permit?"],
                          "Apply online through the city parking portal with a vehicle registration and a lease or utility bill showing your address; permits arrive by mail in 10 days."),
            }},
            "bulk-pickup": {"name": "bulk item pickup", "attrs": {
                "eligibility": (["What items can go out for bulk pickup?",
                                 "is a mattress allowed in bulk pickup",
                                 "Which items are not accepted for bulk trash collection?"],
                                "Bulk pickup accepts furniture, mattresses, and large appliances with doors removed; it does not accept tires, paint, batteries, or construction debris."),
                "fee": (["Does bulk pickup cost anything?",
                         "bulk trash pickup fee",
                         "How many free bulk pickups do I get?"],
                        "Each household gets 2 free bulk pickups per year; additional pickups cost $25 for up to 5 items."),
                "apply": (["How do I schedule a bulk pickup?",
                           "book a bulk trash collection",
                           "When should I put bulk items at the curb?"],
                          "Schedule bulk pickup by calling 311 or using the city app at least 5 days ahead, and place items at the curb by 6 a.m. on your scheduled day."),
            }},
            "library-card": {"name": "the public library card", "attrs": {
                "eligibility": (["Who can get a library card?",
                                 "can non-residents get a public library card",
                                 "Do kids need a parent to get a library card?"],
                                "Anyone who lives, works, or attends school in the county can get a free library card; children under 13 need a parent or guardian to sign."),
                "fee": (["Are there late fees at the library?",
                         "library overdue fines",
                         "How much does a lost library book cost?"],
                        "The library no longer charges overdue fines; lost or damaged items are billed at replacement cost plus a $5 processing fee."),
                "apply": (["How do I sign up for a library card?",
                           "where to get a library card",
                           "Can I get a library card online?"],
                          "Sign up online for a digital card instantly, or visit any branch with a photo ID and proof of address to get a physical card."),
            }},
        },
    },
    "health": {
        "doc": ["Member Handbook", "Health Plan FAQ", "Summary of Benefits", "Member Services Help"],
        "distractors": [
            "The plan for the new health sciences building includes a rooftop garden.",
            "Telehealth equipment makers reported higher quarterly revenue.",
            "The prescription for success, the coach said, is practice and sleep.",
            "Network outages at the data center lasted about two hours.",
            "The annual physical fitness test for recruits includes a 1.5-mile run.",
            "Refill stations for water bottles were installed in every school.",
        ],
        "entities": {
            "telehealth": {"name": "telehealth visits", "attrs": {
                "cost": (["What does a telehealth visit cost?",
                          "copay for a virtual doctor visit",
                          "Is telehealth free on my plan?"],
                         "Telehealth visits with in-network providers have a $0 copay on all Silver and Gold plans and a $15 copay on Bronze plans."),
                "requirement": (["Do I need a referral for telehealth?",
                                 "requirements for a telehealth appointment",
                                 "Can I use telehealth from another state?"],
                                "No referral is needed for telehealth, but you must be physically located in a state where the provider is licensed at the time of the visit."),
                "how": (["How do I book a telehealth visit?",
                         "how to start a virtual visit",
                         "Where do I schedule a video appointment?"],
                        "Book a telehealth visit in the member app under Care > Virtual Visit, or call Member Services; visits are available 24/7."),
            }},
            "refills": {"name": "prescription refills", "attrs": {
                "cost": (["How much do generic prescriptions cost?",
                          "copay for generic drugs",
                          "What's the mail-order price for a 90-day supply?"],
                         "Generic drugs cost $10 for a 30-day supply at retail, or $20 for a 90-day supply through mail order."),
                "requirement": (["Do refills need prior authorization?",
                                 "which prescriptions require prior auth",
                                 "When is a refill too early to fill?"],
                                "Specialty drugs require prior authorization, and a refill can be filled once 75% of the previous supply has been used."),
                "how": (["How do I refill a prescription?",
                         "refill my meds online",
                         "How do I set up automatic mail-order refills?"],
                        "Refill through the member app's Pharmacy tab or call the pharmacy line; mail-order members can turn on automatic refills in the app."),
            }},
            "out-of-network": {"name": "out-of-network care", "attrs": {
                "cost": (["What do I pay for out-of-network care?",
                          "out of network coinsurance",
                          "Is there a separate deductible for out-of-network?"],
                         "Out-of-network care has a separate $3,000 deductible, after which you pay 50% coinsurance plus any amount above the allowed charge."),
                "requirement": (["Is out-of-network care covered in an emergency?",
                                 "emergency care outside the network",
                                 "Do I need approval to see an out-of-network specialist?"],
                                "Emergency care is covered at in-network rates anywhere; non-emergency out-of-network specialist visits need prior approval to be covered."),
                "how": (["How do I file an out-of-network claim?",
                         "submit a claim for an out of network doctor",
                         "Where do I send an itemized bill for reimbursement?"],
                        "File an out-of-network claim by uploading the itemized bill and proof of payment in the member portal within 180 days of the service."),
            }},
            "physical": {"name": "the annual physical", "attrs": {
                "cost": (["Is my annual physical free?",
                          "cost of a yearly checkup",
                          "Will I be billed for labs at my physical?"],
                         "One preventive annual physical per year is covered at 100% in-network; labs ordered for a new problem during the visit may have cost sharing."),
                "requirement": (["How often can I get a physical?",
                                 "do I have to wait 12 months between physicals",
                                 "What counts as a preventive visit?"],
                                "The plan covers one preventive physical every calendar year; visits that address new symptoms are billed as diagnostic office visits."),
                "how": (["How do I schedule my annual physical?",
                         "book a yearly checkup",
                         "Do I need to pick a primary care doctor first?"],
                        "Schedule the physical directly with your assigned primary care provider; choose or change your PCP in the member app before booking."),
            }},
        },
    },
    "it": {
        "doc": ["IT Service Desk KB", "Security Standards", "Employee Tech Guide", "Help Center"],
        "distractors": [
            "The password to the escape room's final lock is hidden in a painting.",
            "Laptop sales rose ahead of the back-to-school season.",
            "Virtual private tours of the museum run every Thursday.",
            "Multi-factor analysis of the survey found three main drivers of satisfaction.",
            "Printer ink cartridges can be recycled at the office supply store.",
            "The service desk at the hotel lobby is open 24 hours.",
        ],
        "entities": {
            "vpn": {"name": "VPN access", "attrs": {
                "how": (["How do I connect to the VPN?",
                         "vpn setup steps",
                         "How do I install the VPN client on a new laptop?"],
                        "Install the VPN client from the Software Center, sign in with your work account, and choose the Nearest Gateway profile."),
                "policy": (["When is VPN required?",
                            "do I need the VPN on home wifi",
                            "Can I use the VPN on a personal computer?"],
                           "The VPN is required for internal systems whenever you are off the office network, and it may only be used on company-managed devices."),
                "contact": (["Who do I contact if the VPN is down?",
                             "vpn not working who to call",
                             "Where do I report VPN outages?"],
                            "Report VPN outages to the Service Desk at extension 4400 or open a Priority 2 ticket in the IT portal."),
            }},
            "password": {"name": "password resets", "attrs": {
                "how": (["How do I reset my password?",
                         "forgot my work password",
                         "How do I change my network password?"],
                        "Reset your password at the self-service reset page using your registered MFA method; new passwords take up to 15 minutes to sync."),
                "policy": (["How often do passwords expire?",
                            "password rules and length",
                            "What's the minimum password length?"],
                           "Passwords must be at least 14 characters and expire every 180 days; you cannot reuse your last 10 passwords."),
                "contact": (["Who can unlock my account?",
                             "account locked out who do I call",
                             "Where do I go if self-service reset fails?"],
                            "If self-service reset fails or your account is locked, call the Service Desk at extension 4400 with your employee ID ready."),
            }},
            "laptop": {"name": "laptop replacement", "attrs": {
                "how": (["How do I request a new laptop?",
                         "laptop replacement request",
                         "How do I order a replacement for a broken laptop?"],
                        "Request a replacement laptop through the IT portal under Hardware > Replace Device; include the asset tag of the current laptop."),
                "policy": (["How often are laptops refreshed?",
                            "laptop refresh cycle",
                            "Am I due for a new laptop after 3 years?"],
                           "Laptops are refreshed every 4 years; earlier replacement requires a hardware failure or a manager-approved business need."),
                "contact": (["Who handles broken laptops?",
                             "my laptop screen cracked who do I tell",
                             "Where do I drop off a damaged laptop?"],
                            "Bring damaged laptops to the Tech Bar on floor 2, or contact the Service Desk to arrange a courier for remote staff."),
            }},
            "mfa": {"name": "multi-factor authentication (MFA)", "attrs": {
                "how": (["How do I enroll in MFA?",
                         "set up multi-factor authentication",
                         "How do I add the authenticator app?"],
                        "Enroll in MFA at the security info page: add the authenticator app, scan the QR code, and approve the test notification."),
                "policy": (["Which apps require MFA?",
                            "is MFA mandatory",
                            "Can I use SMS for MFA?"],
                           "MFA is mandatory for email, VPN, and all cloud apps; SMS codes are not allowed, so use the authenticator app or a hardware key."),
                "contact": (["Who do I contact if I lost my MFA phone?",
                             "new phone, lost authenticator, help",
                             "Where do I go to reset MFA?"],
                            "If you lose your MFA device, call the Service Desk at extension 4400; they verify your identity and issue a temporary access pass."),
            }},
        },
    },
}

# Held out: all of the health-plan domain, plus one entity per other domain.
TEST_FAMILIES = ["health/telehealth", "health/refills", "health/out-of-network", "health/physical",
                 "product/b400", "dataeng/vacuum"]

# Close siblings: same kind of thing, heavy word overlap, so the sibling's answer to the same attribute is
# "same subject, does not help" (1). Entities without a close sibling get a second same-entity passage.
SIBLING = {"b200": "b400", "b400": "b200", "thermostat": "plug", "plug": "thermostat",
           "parental-leave": "pto", "pto": "parental-leave", "time-travel": "vacuum", "vacuum": "time-travel",
           "password": "mfa", "mfa": "password", "telehealth": "physical", "physical": "telehealth"}

FILLER = {
    "hr": ["Policies are reviewed annually by the People team.", "Questions? Contact your HR business partner.",
           "This section applies to U.S. employees.", "See also: Leave of Absence overview."],
    "product": ["Firmware updates install automatically overnight.", "Keep the device away from heat sources.",
                "Registration is optional but recommended.", "See the Quick Start card in the box."],
    "dataeng": ["Examples use SQL; the Python API is equivalent.", "Applies to tables created with the default table format.",
                "Last updated for runtime 14.x.", "See also: table maintenance best practices."],
    "civic": ["Office hours are Monday through Friday, 8 a.m. to 5 p.m.", "Information is subject to change by ordinance.",
              "Spanish-language materials are available on request.", "Call 311 with questions."],
    "health": ["Coverage details depend on your plan year.", "Check your Evidence of Coverage for exclusions.",
               "Member Services is available 7 days a week.", "Amounts shown are for in-network care unless noted."],
    "it": ["All requests are logged in the IT portal.", "Follow the acceptable use policy at all times.",
           "Service Desk hours: 7 a.m. to 7 p.m. local time.", "See the onboarding checklist for new hires."],
}

CUTOFF = ["For more information, see the", "Note that exceptions may", "In addition, employees who",
          "The following table lists", "Related articles:", "If you have questions about"]


def header(rng, domain, ent_name):
    doc = C.pick(rng, KB[domain]["doc"])
    style = rng.randrange(6)
    title = ent_name[0].upper() + ent_name[1:]
    if style == 0:
        return f"## {title}\n"
    if style == 1:
        return f"{doc} > {title}\n"
    if style == 2:
        return f"[{doc} | chunk {rng.randrange(2, 60)}/{rng.randrange(60, 140)}]\n"
    if style == 3:
        return f"{doc}\nSection {rng.randrange(1, 12)}.{rng.randrange(1, 9)} {title}\n"
    if style == 4:
        return ""
    return f"Title: {title} - {doc}\n"


def render(rng, domain, ent_name, sentences, faq_q=None):
    """Turn fact sentences into a retrieved-chunk-looking passage."""
    parts = list(sentences)
    if rng.random() < 0.5:
        parts.insert(rng.randrange(len(parts) + 1), C.pick(rng, FILLER[domain]))
    style = rng.randrange(4)
    if style == 0 and faq_q:
        body = f"Q: {faq_q}\nA: " + " ".join(parts)
    elif style == 1:
        body = "\n".join("- " + p for p in parts)
    else:
        body = " ".join(parts)
    tail = f" {C.pick(rng, CUTOFF)}" if rng.random() < 0.35 else ""
    lead = "..." if rng.random() < 0.2 else ""
    return (header(rng, domain, ent_name) + lead + body + tail).strip()


def ask(rng, q):
    """Query variation: casing, punctuation, a little typo noise, occasional preamble."""
    pre = C.pick(rng, ["", "", "", "", "quick q: ", "Hi, ", "question - ", "pls help: "])
    q = C.messy(rng, q, typo_rate=0.05, p_typo=0.3)
    if rng.random() < 0.2:
        q = q.rstrip("?")
    return pre + q


def lowerfirst(s):
    return s[0].lower() + s[1:] if s and not s.startswith(("B", "I ", "VERSION")) else s


def two_part(rng, qa, qb):
    joiner = C.pick(rng, [" And ", " Also, ", " Plus, ", " and ", " + "])
    b = qb if joiner.strip() in ("And", "Also,", "Plus,") else lowerfirst(qb)
    return qa.rstrip() + joiner + b


def gold(score):
    return {"relevant": score >= 1, "answers": score == 3, "relevance": score}


def build(rng):
    examples = []
    all_ents = [(d, e) for d in KB for e in KB[d]["entities"]]

    def other_domain_sentence(domain):
        d2, e2 = C.pick(rng, [x for x in all_ents if x[0] != domain])
        ent2 = KB[d2]["entities"][e2]
        return d2, ent2, C.pick(rng, list(ent2["attrs"].values()))[1]

    def add(domain, eid, score, query, passage):
        examples.append({"family": f"{domain}/{eid}", "group": domain,
                         "state": {"query": query, "passage": passage}, "gold": gold(score)})

    for domain, dd in KB.items():
        ents = dd["entities"]
        for eid, ent in ents.items():
            attrs = list(ent["attrs"])
            # ---- single-attribute queries
            for a in attrs:
                qs, ans = ent["attrs"][a]
                for k in range(2):                                  # complete
                    q = ask(rng, qs[(k + rng.randrange(3)) % len(qs)])
                    extra = [ent["attrs"][C.pick(rng, [x for x in attrs if x != a])][1]] if rng.random() < 0.4 else []
                    sents = [ans] + extra if rng.random() < 0.6 else extra + [ans]
                    add(domain, eid, 3, q, render(rng, domain, ent["name"], sents, faq_q=qs[0]))
                q = ask(rng, C.pick(rng, qs))                         # related: other attribute, same entity
                others = [x for x in attrs if x != a]
                rng.shuffle(others)
                sents = [ent["attrs"][x][1] for x in others[:1 + (rng.random() < 0.4)]]
                add(domain, eid, 1, q, render(rng, domain, ent["name"], sents,
                                              faq_q=ent["attrs"][others[0]][0][0]))
                q = ask(rng, C.pick(rng, qs))                         # related: close sibling, same attribute
                if eid in SIBLING:
                    sib = ents[SIBLING[eid]]
                    add(domain, eid, 1, q, render(rng, domain, sib["name"], [sib["attrs"][a][1]],
                                                  faq_q=sib["attrs"][a][0][0]))
                else:
                    x = C.pick(rng, others)
                    add(domain, eid, 1, q, render(rng, domain, ent["name"], [ent["attrs"][x][1]],
                                                  faq_q=ent["attrs"][x][0][-1]))
                q = ask(rng, C.pick(rng, qs))                         # irrelevant: keyword-overlap distractor
                dist = C.pick(rng, dd["distractors"])
                d2, ent2, s2 = other_domain_sentence(domain)
                src = C.pick(rng, ["", "", "News digest\n", "Blog post excerpt\n", "[web result]\n", "Newsletter, p. 3\n"])
                add(domain, eid, 0, q, (src + " ".join([dist] + ([s2] if rng.random() < 0.3 else []))).strip())
                q = ask(rng, C.pick(rng, qs))                         # irrelevant: another domain
                d2, ent2, s2 = other_domain_sentence(domain)
                add(domain, eid, 0, q, render(rng, d2, ent2["name"], [s2]))
            # ---- two-part queries: (a, b), third attribute c
            for i in range(len(attrs)):
                a, b = attrs[i], attrs[(i + 1) % len(attrs)]
                c = [x for x in attrs if x not in (a, b)][0]
                qa, qb = C.pick(rng, ent["attrs"][a][0]), C.pick(rng, ent["attrs"][b][0])
                ansa, ansb, ansc = ent["attrs"][a][1], ent["attrs"][b][1], ent["attrs"][c][1]
                both = [ansa, ansb] if rng.random() < 0.5 else [ansb, ansa]
                add(domain, eid, 3, ask(rng, two_part(rng, qa, qb)), render(rng, domain, ent["name"], both))
                add(domain, eid, 2, ask(rng, two_part(rng, qa, qb)), render(rng, domain, ent["name"], [ansa]))
                add(domain, eid, 2, ask(rng, two_part(rng, qa, qb)),
                    render(rng, domain, ent["name"], [ansb] + ([ansc] if rng.random() < 0.4 else [])))
                add(domain, eid, 1, ask(rng, two_part(rng, qa, qb)), render(rng, domain, ent["name"], [ansc]))
                d2, ent2, s2 = other_domain_sentence(domain)
                add(domain, eid, 0, ask(rng, two_part(rng, qa, qb)), render(rng, d2, ent2["name"], [s2]))
    return examples


def main():
    rng = C.rng_for(NAME, SEED)
    splits = C.write_dataset(NAME, build(rng), HERE, PREFIX, seed=SEED, test_families=TEST_FAMILIES)
    C.summary(NAME, splits)
    return splits


if __name__ == "__main__":
    main()
