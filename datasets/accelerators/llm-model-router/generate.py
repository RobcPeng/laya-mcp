"""Generate the llm-model-router accelerator set (deterministic, stdlib only).

Hand-written prompt families cover 7 domains x 4 difficulty levels. Each family fixes its gold labels
(domain, difficulty, needs_tools, is_sensitive) and has 2-3 templates with slots (languages, topics,
numbers, fake records), so one family yields many distinct prompts. Tool-needing and sensitive variants
are separate families written for each domain where they make sense, with hard negatives on both sides:
"what is PII?" is not sensitive, pasted tables do not need tools, historical facts do not need search.
TEST holds out one family per (domain, difficulty) cell plus unseen tool and sensitive phrasings.

    python datasets/accelerators/llm-model-router/generate.py
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import _common as C  # noqa: E402

NAME = "llm-model-router"
PREFIX = "rtr"
SEED = 808
PER_FAMILY = 15


def fake_record(rng):
    n = C.person(rng)
    return (f"{n}, DOB {C.dob(rng)}, SSN {C.fake_ssn(rng)}, phone {C.phone(rng)}, "
            f"{C.address(rng)}")


def patient(rng):
    return (f"Patient {C.person(rng)} (MRN {rng.randrange(100000, 999999)}), age {rng.randrange(19, 88)}, "
            f"{C.pick(rng, ['type 2 diabetes', 'hypertension', 'major depressive disorder', 'COPD', 'HIV positive', 'post-op knee replacement'])}, "
            f"on {C.pick(rng, ['metformin 500mg', 'lisinopril 10mg', 'sertraline 50mg', 'an albuterol inhaler', 'apixaban 5mg'])}")


def cred(rng):
    return C.pick(rng, [
        f"postgres://svc_app:Pa55w0rd-{rng.randrange(1000, 9999)}@db.internal.example.com:5432/prod",
        f"AWS_SECRET_ACCESS_KEY=exampleKEY{rng.randrange(10**7, 10**8)}abcdEFGH",
        f"api_key = 'sk_test_example_{rng.randrange(10**9, 10**10)}'",
        f"password: Winter{rng.randrange(2020, 2027)}!  user: admin",
    ])


def fin(rng):
    return (f"Q{rng.randrange(1, 5)} internal numbers (not yet public): revenue ${rng.randrange(20, 90)}.{rng.randrange(10)}M, "
            f"EBITDA margin {rng.randrange(5, 30)}%, planned layoffs of {rng.randrange(40, 400)} staff in {C.pick(rng, ['ops', 'sales', 'support'])}")


def customers(rng):
    rows = [f"{C.person(rng)}, {C.email(rng)}, {C.phone(rng)}, balance ${rng.randrange(50, 9000)}" for _ in range(3)]
    return "; ".join(rows)


SLOTS = {
    "lang": ["Python", "JavaScript", "TypeScript", "Go", "Java", "Rust", "C#", "SQL", "Bash", "Scala"],
    "tlang": ["Spanish", "French", "German", "Japanese", "Vietnamese", "Portuguese", "Korean", "Arabic", "Tagalog"],
    "topic": ["photosynthesis", "inflation", "the water cycle", "black holes", "the French Revolution",
              "vaccines", "plate tectonics", "supply and demand", "the immune system", "compound interest",
              "the electoral college", "machine learning"],
    "city": ["Denver", "Boise", "Austin", "Phoenix", "Salt Lake City", "Albuquerque", "Cheyenne", "Tucson"],
    "ticker": ["the S&P 500", "Bitcoin", "gold", "the 10-year Treasury yield", "crude oil", "the euro"],
    "country": ["Canada", "Kenya", "Peru", "Norway", "Vietnam", "Chile", "Portugal", "Egypt", "Mongolia"],
    "n1": [str(x) for x in (17, 23, 48, 125, 360, 1024, 88, 12, 7, 64)],
    "n2": [str(x) for x in (3, 5, 9, 14, 32, 6, 11, 15)],
    "product": ["a budgeting app", "a hiking backpack", "a coffee subscription", "a project management tool",
                "a city recycling program", "a used-bike marketplace", "a library reading challenge"],
    "hi": ["hi", "hey there", "good morning!", "hello", "yo", "hey, how's it going?", "morning :)", "hiya"],
    "thanks": ["thanks!", "thank you so much", "ok cool thanks", "perfect, thanks", "appreciate it", "ty"],
    "record": fake_record, "patient": patient, "cred": cred, "fin": fin, "customers": customers,
    "person": C.person, "email": C.email, "phone": C.phone,
}

# (domain, difficulty, needs_tools, is_sensitive, family, [templates])
FAMILIES = [
    # ================================================================ coding
    ("coding", 0, False, False, "coding/rename", [
        "Rename the variable `tmp` to `total` in this line: tmp = a + b",
        "fix the typo: pritn('hello')",
        "What's the {lang} keyword for defining a constant?",
    ]),
    ("coding", 0, False, False, "coding/syntax-lookup", [
        "How do I comment out a line in {lang}?",
        "what's the file extension for {lang} files",
        "In {lang}, how do you get the length of a list?",
    ]),
    ("coding", 1, False, False, "coding/small-func", [
        "Write a {lang} function that reverses a string.",
        "Write a {lang} function to check if a number is prime.",
        "Give me a SQL query that counts orders per customer from an orders table.",
    ]),
    ("coding", 1, False, False, "coding/explain-snippet", [
        "What does this do? `[x*x for x in range(10) if x % 2 == 0]`",
        "Explain this regex: ^[0-9]+-[a-z]*$",
        "Why does `0.1 + 0.2 == 0.3` return false in {lang}?",
    ]),
    ("coding", 2, False, False, "coding/debug", [
        "My {lang} API returns 500 only when two requests hit it at the same time. Here's the handler, it updates a shared dict of counters without a lock. Walk me through what's going wrong and how to fix it.",
        "This recursive function blows the stack for n > 5000. Rewrite it iteratively and explain the change:\ndef depth(node): return 0 if not node else 1 + max(depth(c) for c in node.children)",
        "Refactor this 80-line {lang} class into smaller functions and add unit tests for the date parsing branch.",
    ]),
    ("coding", 2, False, False, "coding/pipeline", [
        "Write a PySpark job that reads daily JSON files, dedupes on event_id keeping the latest timestamp, and writes a partitioned table. Include the merge logic.",
        "Build a small {lang} CLI that watches a folder, resizes new images to 800px wide, and logs errors to a file.",
        "Write a {lang} script that paginates through a REST API, retries on 429 with backoff, and writes results to CSV.",
        "Convert this nested-loop {lang} code to use a hash map so it runs in linear time, and explain the complexity before and after.",
    ]),
    ("coding", 3, False, False, "coding/system", [
        "Design and implement a distributed rate limiter in {lang} that works across 20 app servers with Redis, handles clock skew, and degrades safely if Redis is down. Provide the code and a failure-mode analysis.",
        "Implement a lock-free multi-producer single-consumer queue in Rust, explain the memory ordering on every atomic, and prove it is ABA-safe.",
        "Write a query planner for a toy SQL dialect supporting joins, predicate pushdown, and cost-based join ordering. Full {lang} implementation please.",
    ]),
    ("coding", 3, False, False, "coding/migration", [
        "We have a 40k-line {lang} monolith with a hand-rolled ORM. Plan and write the first stage of migrating it to a service architecture without downtime, including the dual-write strategy and rollback plan.",
        "Port this numerical simulation from Fortran to {lang} with vectorization, keep results bit-for-bit reproducible, and explain every place floating point order changes.",
    ]),
    ("coding", 1, True, False, "coding/run-this", [
        "Run this {lang} script and tell me what it prints: for i in range({n2}): print(i*i)",
        "Execute this and show me the output: SELECT COUNT(*) FROM orders WHERE status = 'late';",
        "Can you run my test suite in the attached repo zip and tell me which tests fail?",
    ]),
    ("coding", 2, True, False, "coding/latest-lib", [
        "What changed in the newest release of the {lang} web framework I use? Check the current release notes and tell me if my code needs updates.",
        "Search GitHub issues for this error message from the latest version of the library and summarize the fixes people found.",
        "Look up the current CVEs for the version of OpenSSL we ship and tell me which apply to us.",
        "Browse the docs site and find the current rate limits for the public API.",
    ]),
    ("coding", 2, False, True, "coding/secret-in-code", [
        "Why does this connection fail? conn = connect('{cred}')",
        "Clean up this config file for me, it's giving a parse error:\n{cred}\nretries=3",
    ]),
    ("coding", 1, False, False, "coding/nearmiss-secrets", [
        "How should I store API keys in a {lang} app instead of hardcoding them?",
        "Write a regex that detects things that look like AWS keys in commit messages.",
        "Explain what a connection string is and what parts it has.",
        "What's the difference between hashing and encrypting passwords?",
    ]),
    # ================================================================ math
    ("math", 0, False, False, "math/arith", [
        "what's {n1} times {n2}",
        "{n1} + {n2} = ?",
        "Convert {n2} kilometers to miles.",
    ]),
    ("math", 1, False, False, "math/word", [
        "If a train travels {n1} miles in {n2} hours, what's its average speed?",
        "A shirt costs $40 and is 25% off. What's the sale price?",
        "Solve for x: 3x + {n2} = {n1}",
    ]),
    ("math", 2, False, False, "math/stats", [
        "I flipped a coin 100 times and got 61 heads. Is the coin biased at the 5% level? Show the test.",
        "Find the derivative of f(x) = x^3 * ln(x) and the critical points.",
        "What's the probability of getting at least one six in {n2} rolls of a fair die? Explain the steps.",
    ]),
    ("math", 3, False, False, "math/proof", [
        "Prove that there are infinitely many primes of the form 4k+3.",
        "Prove that every continuous function on a closed interval is uniformly continuous, with full epsilon-delta detail.",
        "Derive the closed-form solution for ridge regression and show when the matrix is invertible.",
        "Prove that the square root of 2 is irrational and generalize the argument to any non-square integer.",
    ]),
    ("math", 3, False, False, "math/modeling", [
        "Set up and solve the optimal stopping problem for hiring from {n1} applicants, then extend it to the case where you can recall one rejected candidate.",
        "Model queue wait times at a 311 call center with 6 agents, Poisson arrivals at 40 per hour, and exponential service at 8 minutes. Compute expected wait and staffing needed for 90% answered in 60 seconds.",
        "Formulate the school bus routing problem for 40 stops and 6 buses as an integer program, then describe a heuristic that scales to 2,000 stops.",
    ]),
    ("math", 2, True, False, "math/live-numbers", [
        "Using today's mortgage rates, calculate my monthly payment on a $420,000 loan over 30 years.",
        "What's the current exchange rate from dollars to the euro, and how much is $2,500 right now?",
        "If I put $10,000 into {ticker} a year ago, what would it be worth today?",
        "Calculate the sales tax on a $1,200 purchase in {city} using the current local rate.",
    ]),
    ("math", 1, False, True, "math/salary-sensitive", [
        "Here are my team's salaries (confidential, from payroll): {person} $84,000, {person} $91,500, {person} $77,250. What's the mean and median?",
        "Compute the average claim amount for these members: {customers}",
    ]),
    # ================================================================ writing
    ("writing", 0, False, False, "writing/fix-line", [
        "fix the grammar: me and him goes to the store yesterday",
        "Make this shorter: 'At this point in time we are currently in the process of reviewing.'",
        "Capitalize this title properly: a guide to city budgets",
    ]),
    ("writing", 1, False, False, "writing/short-email", [
        "Write a short email telling my team the meeting moved to 3pm.",
        "Draft a polite two-sentence reply declining a vendor demo.",
        "Write a tweet announcing {product}.",
    ]),
    ("writing", 2, False, False, "writing/longer", [
        "Write a 600-word blog post about {product} for first-time users, with a friendly tone and three section headings.",
        "Rewrite this press release for a general audience and cut it to half the length, keeping every number accurate.",
        "Write a cover letter for a data analyst role at a county health department, highlighting SQL and dashboard work.",
    ]),
    ("writing", 3, False, False, "writing/policy", [
        "Draft a 5-page RFP for a city's 311 CRM replacement: scope, functional requirements, integration with GIS and work-order systems, evaluation criteria, and a scoring rubric.",
        "Write a grant narrative for a rural broadband program that addresses each of the funder's 8 scoring criteria with evidence, budget justification, and a logic model.",
        "Write a 3,000-word white paper on data governance for state agencies, covering records retention, data sharing agreements, and access controls, with citations to the kinds of statutes involved.",
        "Draft the full technical proposal section for a statewide unemployment insurance modernization bid, mapping each requirement to our approach, risks, and staffing plan.",
    ]),
    ("writing", 1, False, True, "writing/customer-email", [
        "Write an apology email to this customer about the late refund: {record}",
        "Draft a reminder letter to these customers about overdue balances: {customers}",
    ]),
    ("writing", 2, False, True, "writing/hr-letter", [
        "Write a termination letter for {person} (employee ID {n1}{n2}), citing the attendance issues and the medical leave dates we discussed.",
        "Draft a memo announcing the restructuring to managers only. Context: {fin}",
    ]),
    ("writing", 1, False, False, "writing/nearmiss-privacy", [
        "Write a short privacy notice explaining how a city website uses cookies.",
        "Explain in plain words what PII means for a staff training handout.",
        "Write a one-paragraph reminder to employees not to paste customer data into chat tools.",
        "Write a checklist for anonymizing a dataset before sharing it with researchers.",
        "Draft a short FAQ answering: what counts as sensitive data at a county agency?",
    ]),
    ("writing", 1, True, False, "writing/news-based", [
        "Write a LinkedIn post reacting to today's top tech news story.",
        "Summarize this morning's headlines about {country} into a 3-bullet brief.",
    ]),
    # ================================================================ data_analysis
    ("data_analysis", 0, False, False, "data/lookup", [
        "In this table, which row has the highest value? a: 4, b: 9, c: 2",
        "What's the total of this column: 12, 15, 9, 22",
    ]),
    ("data_analysis", 1, False, False, "data/pasted-small", [
        "Here are monthly sign-ups: Jan 120, Feb 135, Mar 128, Apr 160. What's the month-over-month growth?",
        "Given region,sales\\nNorth,{n1}\\nSouth,{n2}0\\nWest,300 - which region leads and by how much?",
        "Which chart type should I use to show {n2} categories over 12 months?",
    ]),
    ("data_analysis", 2, False, False, "data/interpret", [
        "Our A/B test: control 4,812 visitors 3.1% conversion, variant 4,790 visitors 3.6%. Is it significant, and what would you recommend?",
        "Explain why the churn rate went up even though the number of cancellations went down, using these numbers: start customers 2,000 vs 1,400; cancellations 180 vs 150.",
        "Here are weekly visits and conversions for 8 weeks (pasted below). Identify the trend, any outliers, and whether the drop in week 6 looks real.\nwk,visits,conv\n1,900,31\n2,950,33\n3,920,30\n4,980,35\n5,1010,36\n6,700,12\n7,990,34\n8,1005,37",
    ]),
    ("data_analysis", 3, False, False, "data/causal", [
        "Design an analysis to estimate whether the new bus route caused ridership changes, given staggered rollout across 14 neighborhoods, seasonality, and a fare change midyear. Specify the model and threats to validity.",
        "Build a forecasting approach for 311 call volume with weather, holidays, and service outages; compare three models and explain how you'd backtest them.",
        "Given 5 years of monthly benefit caseloads, design a model that separates the effect of policy changes from the unemployment rate, and explain identification.",
    ]),
    ("data_analysis", 2, True, False, "data/attached-file", [
        "Analyze the attached spreadsheet of Q3 expenses and flag categories that grew more than 20%.",
        "Open sales_2025.csv from my drive and make a pivot of revenue by region and month.",
        "Load the uploaded parquet file and tell me which columns have the most nulls.",
        "I attached two CSV exports; join them on account_id and tell me how many accounts are missing from the second.",
    ]),
    ("data_analysis", 1, True, False, "data/live-query", [
        "Pull yesterday's order count from the warehouse and compare it to last week.",
        "Query our dashboard for current open tickets by priority.",
        "Check the live inventory system and tell me which SKUs are below reorder level.",
        "Look up this week's 311 call volume from the city open data portal and compare it to last year.",
    ]),
    ("data_analysis", 2, False, True, "data/sensitive-table", [
        "Find patterns in these patient records and suggest follow-ups: {patient}; {patient}",
        "Which of these customers are most likely to default? {customers}",
    ]),
    ("data_analysis", 3, False, True, "data/sensitive-fin", [
        "Here are our unreleased financials: {fin}. Build a three-scenario model for next year and identify which cost lines to cut to keep margin above 15%.",
    ]),
    # ================================================================ knowledge
    ("knowledge", 0, False, False, "knowledge/fact", [
        "What's the capital of {country}?",
        "Who wrote Pride and Prejudice?",
        "How many planets are in the solar system?",
    ]),
    ("knowledge", 0, False, False, "knowledge/historical-nearmiss", [
        "What year did the Berlin Wall fall?",
        "What was the capital of {country} in 1900?",
        "When was the first moon landing?",
    ]),
    ("knowledge", 1, False, False, "knowledge/explain", [
        "Explain {topic} in simple terms.",
        "What's the difference between weather and climate?",
        "Give me a quick overview of {topic}.",
    ]),
    ("knowledge", 2, False, False, "knowledge/compare", [
        "Compare how three countries fund public schools and the tradeoffs of each approach.",
        "Walk me through how a bill becomes law at the state level, including where it usually dies.",
        "Explain {topic} in depth for a college student, including the main misconceptions.",
    ]),
    ("knowledge", 3, False, False, "knowledge/expert", [
        "Critically evaluate the evidence for and against minimum wage increases on employment, citing the main study designs and their weaknesses.",
        "Explain the legal differences between a state's open records law and federal FOIA, and how courts have handled exemptions for deliberative process.",
        "Explain the tradeoffs between proportional representation and first-past-the-post systems, with evidence on party fragmentation and voter turnout.",
        "Assess the main scientific uncertainties in climate sensitivity estimates and how they affect policy cost-benefit analysis.",
    ]),
    ("knowledge", 0, True, False, "knowledge/weather-price", [
        "What's the weather in {city} right now?",
        "What's {ticker} trading at today?",
        "Is it going to snow in {city} tomorrow?",
    ]),
    ("knowledge", 1, True, False, "knowledge/news", [
        "What's the latest news about {country}?",
        "Search the web for the current city council agenda in {city}.",
        "Who won last night's game?",
    ]),
    ("knowledge", 1, False, True, "knowledge/medical-personal", [
        "My lab results: {patient}. What does an A1C of 8.1 mean for me?",
        "Here are my details: {record}. Am I eligible for Medicare yet?",
    ]),
    ("knowledge", 1, False, False, "knowledge/nearmiss-health", [
        "What does an A1C test measure?",
        "What is HIPAA and who has to follow it?",
        "What's considered personally identifiable information?",
        "Explain the difference between de-identified and anonymized health data.",
    ]),
    # ================================================================ translation
    ("translation", 0, False, False, "translation/word", [
        "How do you say 'thank you' in {tlang}?",
        "translate 'where is the library' to {tlang}",
        "What's 'trash pickup' in {tlang}?",
    ]),
    ("translation", 1, False, False, "translation/sentence", [
        "Translate into {tlang}: Your application has been received and will be reviewed within 10 business days.",
        "Translate this sign to {tlang}: No parking on street-sweeping days, 7am to 3pm.",
    ]),
    ("translation", 2, False, False, "translation/document", [
        "Translate this one-page tenant rights flyer into {tlang}, keeping the headings and plain-language reading level.",
        "Translate our 500-word website FAQ on property taxes into {tlang} and flag terms that don't have a direct equivalent.",
        "Translate this 3-paragraph school enrollment letter into {tlang} and keep it at a 6th-grade reading level.",
    ]),
    ("translation", 3, False, False, "translation/legal", [
        "Translate this 12-clause services contract into {tlang}, preserving the legal meaning of indemnification and limitation of liability, and note where local law uses different concepts.",
        "Translate this sonnet into {tlang} keeping the rhyme scheme and meter, and explain the tradeoffs you made.",
    ]),
    ("translation", 1, False, True, "translation/personal-letter", [
        "Translate this notice into {tlang} for the client: 'Dear {person}, your case {n1}-{n2} was denied. Our file shows: {record}.'",
        "Translate to {tlang}: Patient info - {patient}. Take medication twice daily.",
    ]),
    ("translation", 1, True, False, "translation/file", [
        "Translate the attached PDF brochure into {tlang}.",
        "Translate every string in the uploaded strings.json file into {tlang}.",
    ]),
    # ================================================================ chitchat
    ("chitchat", 0, False, False, "chitchat/greeting", [
        "{hi}",
        "{thanks}",
        "{hi} what's up",
        "lol ok",
    ]),
    ("chitchat", 0, False, False, "chitchat/smalltalk", [
        "how are you today?",
        "do you like music?",
        "what's your favorite color?",
        "tell me a joke",
        "good night!",
        "how was your weekend?",
        "nice to meet you",
    ]),
    ("chitchat", 1, False, False, "chitchat/light", [
        "I'm bored, give me 3 fun things to do on a rainy afternoon.",
        "I had a rough day at work, just want to vent for a sec.",
        "Recommend a fun board game for 4 people.",
        "any good podcast recs for a long drive?",
        "what should I name my new houseplant?",
        "I just got a puppy!! any tips for the first night?",
    ]),
    ("chitchat", 1, False, True, "chitchat/overshare", [
        "{hi}! btw I'm {person}, my number is {phone} and my email is {email}, can you remember that for later?",
        "Just got my diagnosis today, {patient}. Feeling kind of down, can we just chat?",
    ]),
    ("chitchat", 0, False, False, "chitchat/about-you", [
        "are you a robot?",
        "what's your name?",
        "do you ever get tired of answering questions?",
        "you're pretty helpful, you know that?",
        "who made you?",
        "can you hear me?",
    ]),
    ("chitchat", 1, False, False, "chitchat/opinion", [
        "cats or dogs, and why?",
        "If you could visit any city, where would you go?",
        "What's a good way to wind down after a long week?",
        "what's the best pizza topping, be honest",
        "summer or winter?",
        "tell me something that will make me smile",
    ]),
    ("chitchat", 0, True, False, "chitchat/whattime", [
        "what time is it in {city}?",
        "what's today's date?",
        "is it the weekend yet where you are? what day is it today",
        "what time does the sun set in {city} today?",
    ]),
]


def family_test_set():
    """One held-out family per (domain, difficulty) cell with >= 2 families, plus a tool and a sensitive
    family, chosen by a fixed rule so the list is reproducible and documented."""
    return ["coding/syntax-lookup", "coding/explain-snippet", "coding/migration", "coding/latest-lib",
            "math/proof", "writing/policy", "writing/hr-letter", "writing/nearmiss-privacy",
            "data/attached-file", "data/sensitive-table", "knowledge/historical-nearmiss",
            "knowledge/news", "knowledge/medical-personal", "translation/legal", "translation/file",
            "chitchat/smalltalk", "chitchat/overshare"]


TEST_FAMILIES = family_test_set()

PREFIXES = ["", "", "", "", "Quick question: ", "Hey, ", "Please ", "Can you help? ", "I need help. ",
            "urgent - ", "For work: "]
SUFFIXES = ["", "", "", "", " Thanks!", " Keep it brief.", " Be thorough.", " Use bullet points.",
            " ty", " Explain like I'm new to this."]


def build(rng):
    examples = []
    for domain, diff, tools, sens, fam, templates in FAMILIES:
        n = PER_FAMILY + (4 if len(templates) >= 3 else 0)
        for i in range(n):
            tpl = templates[i % len(templates)]
            text = C.fill(rng, tpl, SLOTS)
            if domain != "chitchat" and rng.random() < 0.5:
                pre = C.pick(rng, PREFIXES)
                if pre and pre.endswith((", ", "Please ", "- ")) and text[:1].isupper() and not text.startswith("I "):
                    text = text[0].lower() + text[1:]
                text = pre + text + C.pick(rng, SUFFIXES)
            if domain == "chitchat":
                text = text + C.pick(rng, ["", "", "", " :)", " haha", "!!", " lol", "?", " :D"])
            text = C.messy(rng, text, typo_rate=0.03, p_typo=0.3)
            examples.append({
                "family": fam, "group": domain,
                "state": {"prompt": text},
                "gold": {"difficulty": diff, "domain": domain, "needs_tools": tools, "is_sensitive": sens},
            })
    return examples


def main():
    rng = C.rng_for(NAME, SEED)
    splits = C.write_dataset(NAME, build(rng), HERE, PREFIX, seed=SEED, test_families=TEST_FAMILIES)
    C.summary(NAME, splits)
    return splits


if __name__ == "__main__":
    main()
