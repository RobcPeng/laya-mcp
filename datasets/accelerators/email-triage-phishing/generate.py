"""Generate the email-triage-phishing accelerator set (deterministic, stdlib only).

Each phrasing family is a hand-written kind of inbound email (a manager asking for a decision, a
meeting reschedule, a subscribed newsletter, a receipt, a credential-harvesting lure, cold junk ads...)
with fixed gold for route, phishing, spam, needs_reply and urgency. Slots vary names, companies,
dates, amounts, links, and sender addresses; wrappers add signatures, quoted threads, forwarded
headers, and mobile footers; a noise pass adds typos. Near-miss families pair legitimate security
notices and vendor invoices with phishing that imitates them. TEST holds out whole families.

    python datasets/accelerators/email-triage-phishing/generate.py
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import _common as C  # noqa: E402

NAME = "email-triage-phishing"
PREFIX = "etp"
PER_FAMILY = 28
SEED = 2207

VENDORS = ["Acme Supply", "Globex Logistics", "Initech Software", "Vandelay Imports", "Northwind Traders",
           "Contoso Print", "Fabrikam Cloud", "Tailspin Travel", "Wingtip Office", "Litware Analytics"]
PHISH_BRANDS = ["Northwind Bank", "Contoso Mail", "Fabrikam Cloud Storage", "Tailspin Parcel",
                "Wingtip Payroll", "Litware ID", "Globex Pay"]
LOOKALIKE = ["examp1e-secure.com", "example-verify.net", "account-examp1e.org", "secure-login.example-auth.co",
             "exarnple.com", "example.com.verify-id.info", "mail-examp1e.net", "support-example.help",
             "example-billing.center", "id-examp1e.com"]
SPAM_DOMAINS = ["deals-now.example.biz", "best-offers.example.shop", "promo.example-mail.top",
                "growth-hack.example.agency", "winner.example.club", "seo-rank.example.pro"]

SLOTS = {
    "boss": C.FIRST,
    "vendor": VENDORS,
    "brand": PHISH_BRANDS,
    "doc": ["the Q3 budget draft", "the vendor contract", "the hiring plan", "the board deck",
            "the grant application", "the policy memo", "the migration plan", "the pricing proposal"],
    "day": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"],
    "time": ["9:30", "10:00", "11:15", "1:00", "2:30", "3:45", "4:00"],
    "amount": ["$1,240.00", "$86.50", "$4,980.00", "$312.19", "$19.99", "$725.00", "$2,150.00"],
    "order": lambda r: f"{r.randrange(100, 999)}-{r.randrange(1000000, 9999999)}",
    "inv": lambda r: f"INV-{r.randrange(10000, 99999)}",
    "hours": ["24 hours", "12 hours", "48 hours", "2 hours"],
    "link": lambda r: f"https://{C.pick(r, LOOKALIKE)}/{C.pick(r, ['login', 'verify', 'secure', 'account/restore', 'pay', 'doc/view'])}?id={r.randrange(10000, 99999)}",
    "topic": ["remote work", "the new expense policy", "Q4 planning", "the office move", "the benefits enrollment",
              "security training", "the parking garage closure", "the holiday schedule"],
    "product": ["noise-cancelling headphones", "a standing desk", "printer toner", "a phone case", "running shoes",
                "a 2-pack of HDMI cables", "a coffee grinder"],
}

F = []


def fam(route, name, phishing, spam, reply, urgency, templates, sender):
    F.append(dict(route=route, name=name, phishing=phishing, spam=spam, reply=reply, urgency=urgency,
                  templates=templates, sender=sender))


def colleague(rng):
    n = C.person(rng)
    return f"{n} <{C.email(rng, n, 'corp.example.com')}>", n


def external(rng):
    n = C.person(rng)
    return f"{n} <{C.email(rng, n)}>", n


def vendor_sender(rng, kind="billing"):
    v = C.pick(rng, VENDORS)
    dom = re.sub(r"[^a-z]", "", v.lower()) + ".example.net"
    return f"{v} <{kind}@{dom}>", v


def phish_sender(rng):
    b = C.pick(rng, PHISH_BRANDS)
    return f"{b} Security <{C.pick(rng, ['no-reply', 'security', 'alerts', 'support', 'admin'])}@{C.pick(rng, LOOKALIKE)}>", b


def spam_sender(rng):
    n = C.pick(rng, ["Special Offers", "Deal Alert", "Marketing Team", "Jenny from Growth", "Rewards Center", "SEO Experts"])
    return f"{n} <{C.pick(rng, ['offers', 'hello', 'info', 'noreply', 'win'])}@{C.pick(rng, SPAM_DOMAINS)}>", n


def exec_spoof(rng):
    n = C.person(rng)
    return f"{n} (CEO) <{re.sub(r'[^a-z]', '', n.lower())}.ceo@{C.pick(rng, ['gmail-example.com', 'example-mail.net', 'ceo-office.example.org'])}>", n


def newsletter_sender(rng):
    n = C.pick(rng, ["The Weekly Brief", "Data Digest", "City Council Updates", "Product News from Litware",
                     "Garden Club Newsletter", "Morning Tech Roundup", "Fabrikam Cloud Blog"])
    return f"{n} <newsletter@{C.pick(rng, ['news.example.org', 'lists.example.com', 'mail.example.net'])}>", n


def service_sender(rng):
    s = C.pick(rng, ["Contoso Mail", "Litware ID", "Northwind Bank", "Fabrikam Cloud"])
    dom = re.sub(r"[^a-z]", "", s.lower()) + ".example.com"
    return f"{s} <no-reply@{dom}>", s


# ------------------------------------------------------------------ action
fam("action", "action/review-doc", False, False, True, 2, [
    ("Need your sign-off today", "Hi,\n\nCan you review {doc} and tell me if you're OK with it? I need your sign-off before 5pm today so I can send it up.\n\nThanks,\n{sig}"),
    ("quick review?", "hey - could you look at {doc} and send me your comments by end of day? legal is waiting on us.\n\n{sig}"),
    ("Decision needed: {doc}", "We need to pick between option A and option B in {doc}. Which do you prefer? I'm submitting it this afternoon.\n\n{sig}"),
], colleague)
fam("action", "action/client-question", False, False, True, 1, [
    ("Question about our order", "Hello,\n\nWe received the shipment but the invoice lists 12 units and we only got 10. Could you confirm what happened? No rush, sometime this week is fine.\n\nBest,\n{sig}"),
    ("follow up on proposal", "Hi, following up on the proposal you sent last week. Does the price include onboarding? Let me know when you get a chance.\n\n{sig}"),
    ("Can we extend the pilot?", "Our team would like to extend the pilot by two weeks. Is that possible on your end? Please let me know by Friday.\n\n{sig}"),
], external)
fam("action", "action/client-today", False, False, True, 2, [
    ("Signed contract needed today", "Hi,\n\nOur procurement closes the books at 5pm today. Could you send back the signed contract and confirm the start date before then?\n\n{sig}"),
    ("Are we still on for delivery?", "Hello - our event is tomorrow morning. Can you confirm today that the order will arrive on time? Otherwise we need a backup plan.\n\n{sig}"),
], external)
fam("action", "action/urgent-outage", False, False, True, 3, [
    ("URGENT: production is down", "The customer portal is returning errors for everyone. I need you on the bridge call right now. Reply with your ETA.\n\n{sig}"),
    ("Need an answer in 30 min", "The client is on the phone and wants to know if we can ship tomorrow. Can you confirm in the next 30 minutes? Just reply yes or no.\n\n{sig}"),
], colleague)
fam("action", "action/task-no-reply", False, False, False, 1, [
    ("Reminder: form about {topic}", "Hi all,\n\nPlease complete the form about {topic} in the HR portal by Friday. No need to reply to this email.\n\n{sig}"),
    ("Timesheet due", "Friendly reminder that timesheets are due Thursday. Submit them in the usual system; don't reply here.\n\n{sig}"),
], colleague)
fam("receipt", "receipt/vendor-invoice-legit", False, False, False, 0, [
    ("Invoice {inv} due in 30 days", "Hello,\n\nAttached is invoice {inv} for {amount} for last month's services, per our contract. Payment terms are net 30 to the account on file. Contact us if you have questions.\n\n{vendor} Accounts Receivable"),
    ("Your invoice {inv}", "Please find invoice {inv} ({amount}) attached. It will be paid automatically through your usual PO process.\n\n{vendor} Billing"),
], vendor_sender)
fam("action", "action/schedule-question", False, False, True, 1, [
    ("Can you cover {day}?", "Hi,\n\nI'm out on {day}. Could you cover the customer call at {time}? Let me know either way.\n\n{sig}"),
    ("need a volunteer", "Anyone free to present at next week's all-hands? Reply to me if you're up for it.\n\n{sig}"),
], colleague)
# ------------------------------------------------------------------ fyi
fam("fyi", "fyi/team-update", False, False, False, 0, [
    ("Update on {topic}", "Hi team,\n\nQuick update on {topic}: we've finalized the plan and nothing is needed from you right now. Details are on the wiki.\n\n{sig}"),
    ("FYI - {doc} is done", "Just letting you know {doc} was approved yesterday. No action needed.\n\n{sig}"),
    ("Status", "fyi the migration finished over the weekend, all green. nothing to do on your side.\n\n{sig}"),
], colleague)
fam("fyi", "fyi/security-notice-legit", False, False, False, 0, [
    ("New sign-in to your account", "We noticed a new sign-in to your {svc} account from Chrome on Windows. If this was you, you don't need to do anything. If not, open the {svc} app directly and review your security settings. We will never ask for your password by email."),
    ("Your password was changed", "The password for your {svc} account was changed on {day}. If you made this change, no further action is required. You can review recent activity in your account settings."),
], service_sender)
fam("fyi", "fyi/it-announcement", False, False, False, 0, [
    ("Scheduled maintenance {day}", "IT will patch the file servers {day} evening from 8 to 10pm. Save your work before you leave. Reminder: IT will never ask for your password over email.\n\nIT Service Desk"),
    ("Phishing awareness reminder", "Heads up: we're seeing fake 'password expiry' emails going around. Don't click links in them; report them with the Report button. No action needed otherwise.\n\nSecurity Team"),
], colleague)
# ------------------------------------------------------------------ meeting
fam("meeting", "meeting/invite", False, False, False, 1, [
    ("Invitation: Project sync @ {day} {time}", "{sender_name} has invited you to Project sync.\nWhen: {day} {time} - 30 min\nJoin: https://meet.example.com/{code}\n\nAccept | Tentative | Decline"),
    ("Updated invitation: Quarterly review", "This event has been updated.\nWhen: {day} {time}\nWhere: Conference Room B\n\nGoing? Yes - Maybe - No"),
], colleague)
fam("meeting", "meeting/propose-time", False, False, True, 1, [
    ("Time to meet next week?", "Hi,\n\nWould {day} at {time} or Thursday morning work for a 30-minute call about {doc}? Let me know which is better.\n\n{sig}"),
    ("coffee chat", "hey! want to grab coffee {day}? i'm free after {time}. let me know\n\n{sig}"),
], external)
fam("meeting", "meeting/reschedule-now", False, False, True, 3, [
    ("Running late - move to {time}?", "Stuck in traffic. Can we push our meeting that starts in 20 minutes to {time}? Reply so I know whether to dial in from the car.\n\n{sig}"),
    ("Room changed for 2pm", "The 2pm today moved to Room 4C because of a leak. Can you still make it? Reply ASAP.\n\n{sig}"),
], colleague)
fam("meeting", "meeting/cancelled", False, False, False, 0, [
    ("Canceled: Weekly standup", "This event has been canceled.\nWeekly standup, {day} {time}\nNo action needed."),
    ("Canceled event: Vendor demo", "{sender_name} canceled Vendor demo on {day}. It will be rescheduled later."),
], colleague)
# ------------------------------------------------------------------ newsletter
fam("newsletter", "news/digest", False, False, False, 0, [
    ("This week: 5 stories on {topic}", "Welcome to this week's issue. Top stories: a look at {topic}, three tips for spreadsheets, and reader questions.\n\nRead online | You're receiving this because you subscribed. Unsubscribe | Manage preferences"),
    ("Your monthly digest", "Here's what happened this month in the community: new meetup dates, a recap of the spring workshop, and a volunteer spotlight.\n\nYou signed up for this list at example.org. Unsubscribe anytime."),
    ("Issue #{num}", "In this issue: release notes, a customer story, and upcoming webinars.\n\nYou are subscribed as a member. Update preferences or unsubscribe."),
], newsletter_sender)
fam("newsletter", "news/product-promo-subscribed", False, False, False, 0, [
    ("New features just for you", "Thanks for being a customer! This month we launched dashboards and offline mode. Explore them in the app.\n\nYou're getting this because you opted in to product updates. Unsubscribe."),
    ("20% off for members", "As a member, you get 20% off annual plans through {day}. Log in to your account to redeem.\n\nYou're receiving this as a registered member. Manage email preferences."),
], newsletter_sender)
# ------------------------------------------------------------------ receipt
fam("receipt", "receipt/order", False, False, False, 0, [
    ("Your order {order} is confirmed", "Thanks for your order!\nOrder {order}\n1 x {product} - {amount}\nEstimated delivery: {day}\n\nView your order in your account."),
    ("Order confirmation #{order}", "We received your order for {product}. Total charged: {amount}. We'll email you when it ships."),
], vendor_sender)
fam("receipt", "receipt/shipped", False, False, False, 0, [
    ("Shipped: {product}", "Good news - your {product} has shipped and should arrive {day}. Track it in your account under Orders."),
    ("Delivered", "Your package was delivered today at the front door. Order {order}."),
], vendor_sender)
fam("receipt", "receipt/payment", False, False, False, 0, [
    ("Payment received - {inv}", "We received your payment of {amount} for invoice {inv}. Thank you.\n\n{vendor} Accounts Receivable"),
    ("Receipt for your subscription", "Receipt\nPlan: Team annual\nAmount: {amount}\nPaid with card ending 4242\n\nNo action is needed."),
], vendor_sender)
# ------------------------------------------------------------------ junk: phishing
fam("junk", "phish/account-suspended", True, False, False, 0, [
    ("Action required: account suspended", "Dear Customer,\n\nWe detected unusual activity and your {brand} account has been suspended. Verify your identity within {hours} or it will be permanently closed:\n{link}\n\n{brand} Security Team"),
    ("Your mailbox is full", "Your mailbox has exceeded its storage limit. You will stop receiving messages in {hours}. Sign in to upgrade for free: {link}"),
    ("Unusual sign-in activity", "Someone tried to access your {brand} account. If this wasn't you, confirm your password here immediately: {link}"),
], phish_sender)
fam("junk", "phish/fake-invoice", True, False, False, 0, [
    ("Overdue invoice {inv} - final notice", "Your invoice {inv} for {amount} is overdue. To avoid legal action, pay within {hours} using the secure portal: {link}"),
    ("Payment failed", "We couldn't process your payment of {amount}. Update your card details now to avoid service interruption: {link}"),
], phish_sender)
fam("junk", "phish/ceo-giftcard", True, False, False, 0, [
    ("Quick favor", "Are you at your desk? I need you to buy 5 gift cards of $200 each for a client appreciation. Keep this between us, I'm in meetings all day. Send me the codes by email.\n\nSent from my iPhone"),
    ("Urgent wire", "I need a wire of {amount} sent to a new supplier today before 3pm. I'll send the bank details. Don't call, I'm in a board meeting. Confidential."),
], exec_spoof)
fam("junk", "phish/parcel-fee", True, False, False, 0, [
    ("Delivery attempt failed", "We tried to deliver your parcel but the address was incomplete. Pay the $1.99 redelivery fee to schedule a new attempt: {link}"),
    ("Your package is on hold", "Package on hold at our facility due to unpaid customs duty. Release it here within {hours}: {link}"),
], phish_sender)
fam("junk", "phish/shared-doc", True, False, False, 0, [
    ("{sender_name} shared \"Salary adjustments 2025.xlsx\" with you", "You have a new shared document. Sign in with your work email and password to view it:\n{link}\n\nThis link expires in {hours}."),
    ("Document for your signature", "Please review and sign the attached agreement. Log in to access the secure document: {link}"),
], phish_sender)
fam("junk", "phish/vendor-bank-change", True, False, False, 0, [
    ("Updated bank details for {vendor}", "Hello,\n\nPlease note our bank details have changed. All future payments, including invoice {inv} for {amount}, should go to the new account below. Please confirm once updated and process today.\n\nAccounts, {vendor}"),
    ("Change of remittance account", "Due to an audit, our old account is frozen. Kindly remit the outstanding {amount} to our new account; details attached. Urgent."),
], lambda r: (f"{C.pick(r, VENDORS)} Accounts <accounts@{C.pick(r, LOOKALIKE)}>", "Accounts"))
# ------------------------------------------------------------------ junk: spam
fam("junk", "spam/ads", False, True, False, 0, [
    ("\U0001F525 70% OFF everything - today only!!!", "HUGE SALE on {product} and more. Limited stock! Click now to shop the deals: https://{spamdom}/sale\n\nTo stop these emails reply STOP."),
    ("You've been selected", "Congratulations! You've been selected for an exclusive offer on {product}. Claim your discount before it's gone: https://{spamdom}/claim"),
    ("Last chance!!", "Don't miss out - buy one {product} get one free. Offer ends midnight. https://{spamdom}/bogo"),
], spam_sender)
fam("junk", "spam/cold-seo", False, True, False, 0, [
    ("Rank #1 on search", "Hi,\n\nI checked your website and found 37 errors hurting your ranking. We guarantee first-page results in 30 days for only $99/month. Interested?\n\nJenny, SEO Experts"),
    ("Grow your business 10x", "We help companies like yours get 500 new leads a month with our AI outreach. Can I send you a price list?"),
    ("Web design offer", "Dear business owner, your site looks outdated. We build modern websites starting at $299. Reply for a free mockup."),
], spam_sender)
fam("junk", "spam/crypto-lottery", False, True, False, 0, [
    ("Double your crypto in 7 days", "Our trading bot made members 312% last month. Join the private group now, spots limited: https://{spamdom}/join"),
    ("Weight loss secret doctors hate", "Lose 20 lbs in 2 weeks with this one trick. Order today and get a free bottle: https://{spamdom}/trial"),
], spam_sender)

fam("junk", "spam/event-pitch", False, True, False, 0, [
    ("Exclusive invite: Leadership Summit 2025", "Dear Professional,\n\nYou are invited to the premier executive summit. Early bird tickets only $1,999 until {day}! Register: https://{spamdom}/summit\n\nReply REMOVE to opt out."),
    ("Buy our attendee list", "Hello, we have the verified attendee list of 14,500 contacts from the big trade show. Interested in pricing? https://{spamdom}/list"),
], spam_sender)
fam("junk", "spam/loan-offer", False, True, False, 0, [
    ("Pre-approved: up to $50,000", "Good news! Your business is pre-approved for a working capital loan up to $50,000. No credit check. Apply in 2 minutes: https://{spamdom}/apply"),
    ("Lower your rate today", "Tired of high interest? Refinance today and save hundreds every month. Rates as low as 1.9%! https://{spamdom}/rates"),
    ("Cash for your old car", "We buy any car, any condition, cash same day. Get a quote now at https://{spamdom}/car"),
], spam_sender)
fam("junk", "spam/unknown-shop", False, True, False, 0, [
    ("New arrivals you'll love", "Hi there! Check out our new collection of {product}. Free shipping over $25 and 15% off your first order with code HELLO15: https://{spamdom}/new"),
    ("Flash sale: {product}", "Flash sale starts now: {product} from $9.99. Only 50 left in stock! https://{spamdom}/flash"),
], spam_sender)

TEST_FAMILIES = ["action/client-today", "action/urgent-outage", "action/task-no-reply", "fyi/security-notice-legit",
                 "news/product-promo-subscribed", "phish/ceo-giftcard", "phish/vendor-bank-change", "spam/cold-seo"]

FOOTERS = {
    "newsletter": ["", "\n\nForward this to a friend.", "\n\nView in browser.", "\n\n(c) 2025 Example Media, 100 Example Way.",
                   "\n\nFollow us for more.", "\n\nQuestions? Just reply to this email.", "\n\nSee you next week!"],
    "receipt": ["", "\n\nQuestions? Contact support@example.com.", "\n\nKeep this email for your records.",
                "\n\nThis is an automated message.", "\n\nReturns accepted within 30 days.", "\n\nThank you for your business."],
    "phish": ["", "\n\n(c) 2025 {brand}. All rights reserved.", "\n\nThis is an automated message, do not reply.",
              "\n\nFailure to comply will result in account termination.", "\n\nCustomer Protection Department",
              "\n\nRef: SEC-{num}"],
    "spam": ["", "\n\nUnsubscribe", "\n\nYou received this because you are a valued customer.",
             "\n\nLimited time. Terms apply.", "\n\n100% satisfaction guaranteed!", "\n\nNot interested? Ignore this email."],
}

SIGN = ["Thanks", "Best", "Cheers", "Regards", "Thank you", "-"]


def signature(rng, name):
    r = rng.random()
    first = name.split()[0]
    if r < 0.3:
        return first
    if r < 0.6:
        return f"{name}\n{C.pick(rng, ['Director of Operations', 'Program Manager', 'Account Executive', 'Finance Lead', 'Engineer'])}\n{C.phone(rng)}"
    if r < 0.8:
        return f"{first}\nSent from my phone"
    return f"{name} | {C.pick(rng, VENDORS)}"


def fill_consistent(rng, texts, slots):
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
    for f in F:
        for i in range(PER_FAMILY):
            subj_t, body_t = f["templates"][i % len(f["templates"])]
            sender, sname = f["sender"](rng)
            slots = dict(SLOTS)
            slots["sig"] = [signature(rng, sname)]
            slots["sender_name"] = [sname]
            slots["svc"] = [sname]
            slots["spamdom"] = SPAM_DOMAINS
            slots["code"] = lambda r: "".join(C.pick(r, "abcdefghjkmnpqrstuvwxyz") for _ in range(9))
            slots["num"] = lambda r: str(r.randrange(12, 240))
            if f["sender"] is vendor_sender:
                slots["vendor"] = [sname]
            kind = ("phish" if f["phishing"] else "spam" if f["spam"] else f["route"])
            foot = C.pick(rng, FOOTERS[kind]) if kind in FOOTERS else ""
            subject, body = fill_consistent(rng, [subj_t, body_t + foot], slots)
            # human-written families get typos and casing noise; machine-generated mail stays clean
            if f["route"] in ("action", "meeting") and f["name"] not in ("meeting/invite", "meeting/cancelled"):
                body = "\n".join(C.messy(rng, ln, typo_rate=0.03, p_typo=0.35) if ln.strip() else ""
                                 for ln in body.split("\n"))
            elif f["name"].startswith("phish") and rng.random() < 0.4:
                body = C.typo(rng, body, 0.03)          # phishing often has sloppy spelling
            r = rng.random()
            if r < 0.1 and f["route"] in ("action", "fyi", "meeting"):
                subject = "Re: " + subject
                q = C.person(rng)
                body += (f"\n\nOn {C.pick(rng, SLOTS['day'])}, {q} <{C.email(rng, q, 'corp.example.com')}> wrote:\n"
                         "> Sounds good, see notes below.\n> Thanks")
            elif r < 0.18 and f["route"] != "junk":
                fwd = C.person(rng)
                body = (f"{C.pick(rng, ['FYI', 'see below', 'Is this legit?', 'forwarding', ''])}\n\n"
                        f"---------- Forwarded message ---------\nFrom: {sender}\nSubject: {subject}\n\n{body}")
                subject = "Fwd: " + subject
                sender = f"{fwd} <{C.email(rng, fwd, 'corp.example.com')}>"
            examples.append({
                "family": f["name"], "group": f["route"],
                "state": {"sender": sender, "subject": subject, "body": body},
                "gold": {"route": f["route"], "phishing": f["phishing"], "spam": f["spam"],
                         "needs_reply": f["reply"], "urgency": f["urgency"]},
            })
    return examples


def main():
    rng = C.rng_for(NAME, SEED)
    splits = C.write_dataset(NAME, build(rng), HERE, PREFIX, seed=SEED, test_families=TEST_FAMILIES)
    C.summary(NAME, splits)
    return splits


if __name__ == "__main__":
    main()
