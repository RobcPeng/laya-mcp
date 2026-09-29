"""Generate the support-ticket-triage accelerator set (deterministic, stdlib only).

Each phrasing family is a hand-written core description of one kind of support ticket with its own
queue and urgency. Two compositional modifiers add a churn sentence ("thinking about switching") or a
refund sentence ("I want this month credited") to eligible families, which sets churn_risk or
refund_requested without changing the queue. needs_human is computed from a fixed rule (see README).
Email wrappers add greetings, signatures, quoted replies, and forwarded-message cruft. TEST holds out
whole families.

    python datasets/accelerators/support-ticket-triage/generate.py
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import _common as C  # noqa: E402

NAME = "support-ticket-triage"
PREFIX = "stt"
PER_FAMILY = 24
SEED = 4101

PRODUCTS = ["the app", "the dashboard", "the mobile app", "the desktop client", "the web portal",
            "Brightdesk", "the sync service", "the reporting module", "the scheduler", "the API"]
DEVICES = ["hub", "thermostat", "smart plug", "camera", "doorbell", "sensor kit", "router", "speaker"]
COMPANIES = ["Acme Widgets", "Globex Ltd", "Initech", "Vandelay Imports", "Hooli Farms", "Pied Piper Bakery",
             "Umbrella Dental", "Stark Plumbing", "Wayne Tutoring", "Duff Distributing", "Soylent Foods",
             "Tyrell Tiles", "Oscorp Cleaning", "Cyberdyne Books"]

SLOTS = {
    "product": PRODUCTS,
    "device": DEVICES,
    "amount": ["$49.00", "$19.99", "$129", "$240.00", "$12.50", "$599", "$89.99", "$35"],
    "order": lambda r: f"#{r.randrange(100000, 999999)}",
    "inv": lambda r: f"INV-{r.randrange(10000, 99999)}",
    "err": ["Error 500", "\"Something went wrong\"", "error code E-4031", "a blank white screen",
            "\"sync failed (timeout)\"", "a spinning wheel forever", "\"403 Forbidden\"", "ERR_CONN_RESET"],
    "since": ["since this morning", "since yesterday", "since the last update", "for two days",
              "since Friday", "for about an hour", "since we upgraded", "all week"],
    "seats": ["3", "5", "12", "25", "40", "8"],
    "feature": ["export to CSV", "dark mode", "a bulk edit option", "recurring invoices", "SSO with our IdP",
                "a Spanish translation", "custom fields on contacts", "an API webhook for new orders",
                "calendar sync", "keyboard shortcuts", "a way to archive old projects"],
    "task": ["add a teammate", "change my billing email", "export my data", "set up two-factor",
             "merge two accounts", "change the time zone", "create a recurring task", "share a report",
             "connect my calendar", "rename a workspace"],
    "days": ["3", "5", "7", "10", "two weeks", "12"],
    "thanks": ["Thanks.", "Thank you!", "Thanks in advance.", "Appreciate any help.", "", "thx", "Cheers,",
               "Regards,", "Please advise."],
}

# (queue, family, urgency, human_flag, allow_mods, base_churn, base_refund, [(subject, body), ...])
# human_flag: True forces needs_human (legal threat, security, abusive, complex); None = rule decides.
F = []


def fam(queue, name, urgency, templates, human=None, mods=True, churn=False, refund=False):
    F.append((queue, name, urgency, human, mods, churn, refund, templates))


# ---------------------------------------------------------------- billing
fam("billing", "billing/double-charge", 2, [
    ("Charged twice", "I was charged {amount} twice on my card this month for the same plan. Can you fix this? {thanks}"),
    ("duplicate charge??", "my bank shows two identical charges of {amount} from you on the same day. only have one account"),
    ("Billing error on {inv}", "Our finance team noticed invoice {inv} was paid twice by auto-pay. Please reverse the duplicate. {thanks}"),
], refund=True)
fam("billing", "billing/invoice-question", 0, [
    ("Where is my invoice", "Where can I download last month's invoice? Our accountant needs it for the books. {thanks}"),
    ("Invoice needs VAT number", "Can you add our tax ID to invoice {inv}? The company name is {company}. {thanks}"),
    ("receipt", "hi, need a receipt for my {amount} payment for expense reports. {thanks}"),
], mods=False)
fam("billing", "billing/price-increase", 1, [
    ("Price went up?", "My renewal was {amount} this year but it was a lot less last year. Nobody told us about a price change. What happened?"),
    ("Unexpected renewal amount", "We were billed {amount} on renewal, which is more than the quote we got. Can you explain the difference? {thanks}"),
])
fam("billing", "billing/payment-failed", 2, [
    ("Payment keeps failing", "I've tried three cards and the payment page keeps saying declined. Our account gets suspended tomorrow if this doesn't go through. {thanks}"),
    ("Can't update card", "Trying to update our card on file and the form throws {err}. Service is paused until we pay. Please help ASAP."),
])
fam("billing", "billing/wrong-plan", 1, [
    ("Billed for wrong plan", "We're on the Starter plan but got charged for Pro ({amount}). Please correct the plan and the charge. {thanks}"),
    ("seat count wrong", "We only have {seats} users but the invoice {inv} bills for more seats than that. {thanks}"),
], refund=True)
fam("billing", "billing/refund-policy-nearmiss", 0, [
    ("Refund policy question", "Before we upgrade to annual: what's your refund policy if we cancel partway through the year? Just want to know for planning. {thanks}"),
    ("question about proration", "If I add {seats} seats mid-cycle, how is that prorated on the next invoice? {thanks}"),
], mods=False)

# ---------------------------------------------------------------- account_access
fam("account_access", "access/password-reset", 1, [
    ("Can't log in", "I forgot my password and the reset email never arrives. Checked spam too. {thanks}"),
    ("password reset link expired", "the reset link says expired every time i click it, even right after it's sent"),
    ("Locked out", "Account says locked after too many attempts. How long until I can try again? {thanks}"),
])
fam("account_access", "access/2fa", 2, [
    ("Lost my phone - 2FA", "I got a new phone and lost my authenticator codes. I can't get into {product} at all and I have client work due today. {thanks}"),
    ("two factor code not working", "The 6-digit codes are always rejected. I've synced the clock on my phone. Completely locked out {since}."),
])
fam("account_access", "access/hacked", 3, [
    ("Account hacked!!", "Someone logged into my account from another country and changed my email address. I did not do this. Lock it down now!"),
    ("Suspicious login", "Got an alert about a login I didn't make, and now there are API keys on our account nobody on my team created. We think we're compromised."),
    ("unauthorized access", "One of our former contractors still seems to have access and just deleted a bunch of records. please help immediately"),
], human=True)
fam("account_access", "access/sso", 2, [
    ("SSO broken for our team", "Since the last update, our whole team of {seats} gets an error when signing in with SSO. Nobody can work. {thanks}"),
    ("SAML login failing", "Every login through our identity provider fails with {err}. The whole company is locked out {since}."),
])
fam("account_access", "access/add-user-nearmiss", 0, [
    ("Login question", "Not locked out or anything, just wondering if two people can share one login or if we need separate seats? {thanks}"),
    ("backup codes", "Password reset worked fine, thanks. Quick one: where do I find my 2FA backup codes to print them? {thanks}"),
], mods=False)

# ---------------------------------------------------------------- technical
fam("technical", "tech/error", 2, [
    ("{err} when saving", "Every time I try to save a record in {product} I get {err}. It's been happening {since}. I can't get any work done."),
    ("App crashing", "{product} crashes as soon as I open a project. Reinstalled twice, same thing. {thanks}"),
    ("Broken after update", "After the latest update {product} shows {err} on the main page. Cleared cache, tried two browsers. {thanks}"),
])
fam("technical", "tech/slow", 1, [
    ("Very slow", "{product} has been really slow {since}, pages take 20+ seconds to load. Is something going on? {thanks}"),
    ("performance", "reports take forever to run now, used to be instant. not urgent but annoying"),
])
fam("technical", "tech/sync", 1, [
    ("Sync not working", "My changes on the phone don't show up on the desktop. Sync says complete but data is missing. {thanks}"),
    ("{device} offline", "My {device} keeps going offline every few hours and I have to unplug it. {thanks}"),
    ("data not syncing", "Calendar events stopped syncing {since}. Everything else works. {thanks}"),
])
fam("technical", "tech/outage", 3, [
    ("OUTAGE - nothing loads", "{product} is completely down for our entire company. {seats} people can't work and we have customers waiting. Is there an outage?"),
    ("API returning 500s", "All our API calls have returned {err} {since}. Our checkout depends on this and we're losing orders every minute."),
    ("Everything down", "None of our locations can process anything, the whole system is dead. This is costing us a lot of money."),
])
fam("technical", "tech/data-loss", 3, [
    ("Data missing!", "Half of our customer records disappeared overnight. We didn't delete anything. Please tell me they can be restored."),
    ("Lost a month of work", "After the sync conflict yesterday, a month of project notes is gone from every device. {thanks}"),
], human=True)
fam("technical", "tech/device-dead", 1, [
    ("{device} won't turn on", "My {device} stopped powering on. Tried a different outlet and cable. Light doesn't come on at all. {thanks}"),
    ("{device} broken?", "the {device} makes a clicking noise and then restarts over and over. had it about 3 months"),
])

# ---------------------------------------------------------------- shipping
fam("shipping", "ship/where-order", 1, [
    ("Where is my order {order}", "Order {order} was supposed to arrive {days} days ago and tracking hasn't updated. {thanks}"),
    ("order status", "Placed order {order} last week, never got a shipping confirmation. can you check?"),
    ("Tracking stuck", "Tracking for {order} has said 'label created' for {days} days. {thanks}"),
])
fam("shipping", "ship/damaged", 1, [
    ("Arrived damaged", "My {device} arrived with a cracked case and the box was crushed. Order {order}. Can you send a replacement? {thanks}"),
    ("broken on arrival", "the {device} from order {order} was broken when I opened it. would like a new one sent"),
])
fam("shipping", "ship/wrong-item", 1, [
    ("Wrong item", "I ordered a {device} but received a completely different product. Order {order}. {thanks}"),
    ("Missing parts", "Order {order} came without the power adapter. Please send the missing part. {thanks}"),
])
fam("shipping", "ship/return", 0, [
    ("Return", "How do I return an unopened {device}? Still within the return window, order {order}. {thanks}"),
    ("return label", "can you email me a return label for order {order}? changed my mind about the color"),
], refund=True)
fam("shipping", "ship/cancel-order-nearmiss", 1, [
    ("Cancel order {order}", "Please cancel order {order} before it ships, I picked the wrong size. I'll place a new order right after. {thanks}"),
    ("change shipping address", "Need to change the delivery address on {order}, we moved. Hasn't shipped yet I think. {thanks}"),
], mods=False)

# ---------------------------------------------------------------- cancellation
fam("cancellation", "cancel/close-account", 1, [
    ("Cancel my subscription", "Please cancel my subscription effective at the end of this billing period. We no longer need it. {thanks}"),
    ("close account", "how do i close my account and delete my data? not using it anymore"),
    ("Cancellation request", "We're consolidating tools and won't be renewing. Please cancel our account for {company}. {thanks}"),
], churn=True)
fam("cancellation", "cancel/switching", 1, [
    ("Cancelling - moving to another provider", "We've decided to move to a competitor that's cheaper. Please cancel at renewal. {thanks}"),
    ("Leaving", "Honestly the last few months have been frustrating and we signed with another vendor. Cancel us please."),
], churn=True)
fam("cancellation", "cancel/angry-refund", 2, [
    ("CANCEL AND REFUND", "I've been charged for months for something that never worked. Cancel my account and refund every penny or I'm disputing with my bank."),
    ("Cancel immediately", "Cancel this today. I want a full refund for this year, I never agreed to auto-renew."),
], churn=True, refund=True, mods=False)
fam("cancellation", "cancel/downgrade", 0, [
    ("Downgrade plan", "We'd like to move from Pro to the Starter plan at our next renewal. We don't use the advanced features. {thanks}"),
    ("fewer seats", "Can we drop from {seats} seats to fewer? Two people left the team. {thanks}"),
])
fam("cancellation", "cancel/legal", 2, [
    ("Formal notice of cancellation", "This is formal notice that {company} is terminating the agreement for breach of the uptime terms. Our attorney is copied. Confirm cancellation in writing."),
    ("Cancel or we escalate", "Cancel our contract. If I don't get written confirmation this week I'm filing a complaint with the consumer protection office."),
], churn=True, human=True, mods=False)

# ---------------------------------------------------------------- feature_request
fam("feature_request", "feature/please-add", 0, [
    ("Feature request: {feature}", "It would be great if {product} supported {feature}. We'd use it every day. {thanks}"),
    ("suggestion", "please add {feature}!! would save me so much time"),
    ("Idea", "Any plans to add {feature}? Our team keeps asking for it. {thanks}"),
])
fam("feature_request", "feature/improve", 0, [
    ("Improvement idea", "The search in {product} would be much better if it matched partial words. {thanks}"),
    ("UI feedback", "Small thing: the save button is hard to find on mobile. Could it be moved to the top? {thanks}"),
])
fam("feature_request", "feature/dealbreaker", 1, [
    ("Need {feature} or we can't renew", "We really need {feature}. Without it, our renewal is hard to justify to management."),
    ("Missing feature", "Our other tool has {feature} and yours doesn't. If it's not on the roadmap soon we'll have to look elsewhere."),
], churn=True, mods=False)
fam("feature_request", "feature/integration", 0, [
    ("Integration request", "Would love an integration with our accounting software so invoices flow over automatically. {thanks}"),
    ("API", "Could you expose {feature} through the API? {thanks}"),
])

# ---------------------------------------------------------------- how_to
fam("how_to", "howto/basic", 0, [
    ("How do I {task}?", "How do I {task} in {product}? Couldn't find it in the help center. {thanks}"),
    ("quick question", "hey, what's the easiest way to {task}?"),
    ("Help with {task}", "I'm new to {product}. Can you walk me through how to {task}? {thanks}"),
])
fam("how_to", "howto/is-there-a-way-nearmiss", 0, [
    ("Is there a way to export?", "Is there a way to export my contacts to a spreadsheet? Not sure if this exists already. {thanks}"),
    ("Can it do this?", "Does {product} already let me {task}, or is that not possible? {thanks}"),
], mods=False)
fam("how_to", "howto/setup", 0, [
    ("Setting up the {device}", "Just got the {device}. Which app do I use to pair it with my phone? {thanks}"),
    ("setup help", "setting up my {device} for the first time, the manual says hold the button but for how long?"),
])
fam("how_to", "howto/competitor-import-nearmiss", 0, [
    ("Importing from our old tool", "We switched to you from another provider last year and love it. How do I import the old archive files we exported? {thanks}"),
    ("migration question", "Moved over from a competitor recently. Is there an import wizard for their CSV format? {thanks}"),
], mods=False)
fam("how_to", "howto/deadline", 1, [
    ("Need help before tomorrow", "I have to present a report tomorrow and I can't figure out how to {task}. Any quick pointers? {thanks}"),
    ("How to share report", "How do I share a report with a client who doesn't have an account? Need to send it today. {thanks}"),
])

CHURN_MODS = [
    " Honestly, we're starting to look at other options.",
    " If this keeps happening we'll switch to a competitor.",
    " This is the third problem this month. Seriously considering cancelling.",
    " Our contract is up next month and this isn't helping your case.",
    " Starting to regret signing up for this.",
    " My boss is asking whether we should move to a different vendor.",
]
REFUND_MODS = [
    " I'd like a refund for this month.",
    " Please credit our account for the time this was broken.",
    " I expect my money back for this.",
    " Can you refund the {amount}?",
    " We should get a partial refund for the downtime.",
]
GREETINGS = ["", "", "Hi,\n\n", "Hello,\n\n", "Hi there,\n\n", "Hey team,\n\n", "Good morning,\n\n",
             "To whom it may concern,\n\n", "Support -\n\n"]


def signature(rng):
    name = C.person(rng)
    r = rng.random()
    if r < 0.25:
        return ""
    if r < 0.5:
        return f"\n\n{name}"
    if r < 0.7:
        return f"\n\n{name}\n{C.pick(rng, ['Office Manager', 'IT Admin', 'Owner', 'Operations Lead', 'Bookkeeper'])}, {C.pick(rng, COMPANIES)}\n{C.phone(rng)}"
    if r < 0.85:
        return "\n\nSent from my iPhone"
    return f"\n\n--\n{name} | {C.email(rng, name)}"


def wrap(rng, subject, body):
    r = rng.random()
    if r < 0.12:
        quoted = ("\n\nOn " + C.pick(rng, ["Mon", "Tue", "Wed", "Thu", "Fri"]) + ", Support <support@example.com> wrote:\n"
                  "> Thanks for contacting us. We're looking into your request and will reply soon.\n"
                  "> Ticket reference " + str(rng.randrange(10000, 99999)))
        subject = "Re: " + subject
        body = body + quoted
    elif r < 0.2:
        fwd_name = C.person(rng)
        body = (f"FYI, forwarding from our team. See below.\n\n---------- Forwarded message ---------\n"
                f"From: {fwd_name} <{C.email(rng, fwd_name)}>\nSubject: {subject}\n\n{body}")
        subject = "Fwd: " + subject
    return subject, body


def fill_consistent(rng, texts, slots):
    """Fill several templates with one value per slot, so subject and body agree."""
    import re
    chosen = {}

    def rep(m):
        k = m.group(1)
        if k not in chosen:
            v = slots[k]
            chosen[k] = v(rng) if callable(v) else C.pick(rng, v)
        return chosen[k]
    return [re.sub(r"\{([a-z_0-9]+)\}", rep, t) for t in texts]


def build(rng):
    examples = []
    for queue, fname, urgency, human, mods, churn0, refund0, templates in F:
        for i in range(PER_FAMILY):
            subj_t, body_t = templates[i % len(templates)]
            slots = dict(SLOTS, company=COMPANIES)
            subject, body = fill_consistent(rng, [subj_t, body_t], slots)
            churn, refund = churn0, refund0
            if mods and not churn and rng.random() < 0.22:
                body += C.pick(rng, CHURN_MODS)
                churn = True
            if mods and not refund and queue in ("billing", "technical", "shipping") and rng.random() < 0.3:
                body += C.fill(rng, C.pick(rng, REFUND_MODS), slots)
                refund = True
            body = C.messy(rng, body, typo_rate=0.035, p_typo=0.4)
            body = C.pick(rng, GREETINGS) + body + signature(rng)
            if rng.random() < 0.1:
                subject = C.pick(rng, ["help", "question", "Support request", "urgent", "(no subject)", "hi"])
            subject, body = wrap(rng, subject, body)
            needs_human = bool(human) or churn or refund or urgency >= 2
            examples.append({
                "family": fname, "group": queue,
                "state": {"subject": subject, "body": body},
                "gold": {"queue": queue, "urgency": urgency, "churn_risk": churn,
                         "refund_requested": refund, "needs_human": needs_human},
            })
    return examples


TEST_FAMILIES = ["billing/wrong-plan", "billing/refund-policy-nearmiss", "access/2fa", "access/hacked",
                 "tech/sync", "ship/damaged", "cancel/switching", "cancel/downgrade", "feature/dealbreaker",
                 "howto/competitor-import-nearmiss"]


def main():
    rng = C.rng_for(NAME, SEED)
    splits = C.write_dataset(NAME, build(rng), HERE, PREFIX, seed=SEED, test_families=TEST_FAMILIES)
    C.summary(NAME, splits)
    return splits


if __name__ == "__main__":
    main()
