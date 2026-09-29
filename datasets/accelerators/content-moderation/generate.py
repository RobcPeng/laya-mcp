"""Generate the content-moderation accelerator set (deterministic, stdlib only).

Each phrasing family is a hand-written kind of user post (on-topic praise, civil disagreement,
violent idioms, unaimed profanity, group insults, personal attacks, harassment campaigns, veiled and
direct threats, scam links, repetitive promotion...) with fixed gold for toxic, harassment, threat,
spam and severity. Slots vary handles, topics, and insults; a surface wrapper adds a platform frame
(reply, game chat, product review, forum quote) and a noise pass adds typos and chat casing. Hard
negatives are first-class families. TEST holds out whole families.

Content policy for this file: mild insults and non-graphic threats only, no slurs, no protected-class
targets. Handles and names are invented.

    python datasets/accelerators/content-moderation/generate.py
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import _common as C  # noqa: E402

NAME = "content-moderation"
PREFIX = "mod"
PER_FAMILY = 34
SEED = 6060

HANDLES = ["@pixel_fox", "@quietriver", "@dev_dana", "@mapleleaf88", "@turbo_toaster", "@nightowl_k",
           "@gardenguy", "@lorem_ipsum", "@saltycaptain", "@bytebandit", "@sunny_side", "@trailrunner7",
           "@cloudchaser", "@mod_sam", "@retro_riley", "@sparrow_j"]
SLOTS = {
    "user": HANDLES,
    "name": C.FIRST,
    "topic": ["the new zoning plan", "this patch", "the season finale", "tabs vs spaces", "the bike lane proposal",
              "the library budget", "this recipe", "the new tax rules", "the playoff game", "sourdough starters",
              "the update to the app", "remote work", "the school board vote", "electric cars"],
    "thing": ["the router", "this blender", "the new controller", "version 2.3", "the free plan", "this tent",
              "the headphones", "the mobile app", "the charger"],
    "insult": ["idiot", "moron", "clown", "loser", "fool", "troll", "joke", "disgrace", "nobody", "waste of space"],
    "adj": ["stupid", "pathetic", "dumb", "worthless", "clueless", "useless"],
    "group": ["people who ride e-scooters", "everyone in this forum", "fans of that team", "anyone who uses tabs",
              "people who put pineapple on pizza", "support mains", "the whole mod team", "cyclists",
              "everyone who voted for this", "you people"],
    "link": lambda r: f"https://{C.pick(r, ['bit-example.xyz', 'free-gifts.example.top', 'cash-now.example.biz', 'promo-example.shop', 'crypto-x.example.io'])}/{r.randrange(1000, 9999)}",
    "amount": ["$5,000", "$800", "$12,000", "$300", "$2,500"],
    "blog": ["my blog", "a write-up I did", "my channel", "our docs page", "a thread I posted last week"],
}

F = []


def fam(name, group, toxic, harass, threat, spam, severity, templates):
    F.append(dict(name=name, group=group, toxic=toxic, harass=harass, threat=threat, spam=spam,
                  severity=severity, templates=templates))


# ------------------------------------------------------------------ acceptable (severity 0)
fam("clean/praise", "clean", False, False, False, False, 0, [
    "Great write-up. The part about {topic} finally made it click for me.",
    "Thanks for posting this, super helpful. Bookmarked.",
    "{thing} has been rock solid for me for six months, no complaints.",
    "Love this community. Someone answered my question about {topic} in five minutes.",
])
fam("clean/question", "clean", False, False, False, False, 0, [
    "Does anyone know if {thing} works with the older model?",
    "Quick question about {topic}: where can I read the full document?",
    "Has anyone else had battery issues with {thing}? Trying to decide whether to return it.",
    "what time does the meeting on {topic} start? couldn't find it on the site",
])
fam("clean/civil-disagree", "clean", False, False, False, False, 0, [
    "I strongly disagree. The numbers on {topic} don't support that conclusion, and the post skips the cost side entirely.",
    "Respectfully, {user}, I think you're wrong about {topic}. Here's why: the pilot program showed the opposite.",
    "This is a bad decision and I'll be at the council meeting to say so. The plan for {topic} ignores the people who live here.",
    "Hard no from me. I've used {thing} for years and this change makes it worse. Please reconsider.",
])
fam("clean/violent-idiom", "clean", False, False, False, False, 0, [
    "We're going to kill it at the show tonight!!",
    "This bug is killing me, been stuck on it all day.",
    "I could murder a pizza right now honestly.",
    "The drummer absolutely slayed last night. Crowd went nuts.",
    "that last level destroyed me lol, 40 attempts",
    "Our team is going to crush the fundraiser goal this year.",
])
fam("clean/unaimed-profanity", "clean", False, False, False, False, 0, [
    "Holy crap, the update is so damn fast now.",
    "What the hell happened to the servers last night lol",
    "Damn, that finale. I did not see that coming.",
    "Well shit, I left my charger at home again.",
    "this recipe is freaking amazing, hell yes",
])
fam("clean/on-topic-promo", "clean", False, False, False, False, 0, [
    "I wrote a longer guide on {topic} on {blog} if anyone wants more detail. Happy to answer questions here too.",
    "Disclosure: I help maintain the plugin, but it solves exactly this problem with {thing}. Docs are linked in my profile.",
    "Our library is hosting a free workshop on {topic} next Saturday, all welcome.",
])
fam("clean/report-abuse", "clean", False, False, False, False, 0, [
    "Mods, someone in the last thread called me a loser and said they'd find me. Can you take a look?",
    "Reporting a user who keeps spamming scam links in the {topic} thread.",
    "Is it against the rules to call someone an idiot? Asking because it keeps happening to me here.",
])
fam("clean/game-banter", "clean", False, False, False, False, 0, [
    "gg {user}, I'm gonna destroy you next round 😂",
    "Rematch tomorrow, prepare to get wrecked. Good game though!",
    "lol you got me, I'll get my revenge in the next match",
    "our squad is coming for you in the finals, {user}. see you there 🔥",
])
# ------------------------------------------------------------------ rude but allowed (severity 1)
fam("rude/off-topic", "rude", False, False, False, False, 1, [
    "who cares about {topic}. anyway is anyone watching the game tonight?",
    "Off topic but does anyone want to buy a used couch?",
    "first!!!",
    "Can we talk about something else, this thread is so boring.",
])
fam("rude/dismissive", "rude", False, False, False, False, 1, [
    "This article is garbage and a waste of everyone's time.",
    "Worst update ever. Whoever designed this new layout should try using it once.",
    "{thing} is junk. Don't buy it.",
    "What a pointless post. Nothing new here.",
])
fam("rude/all-caps-rant", "rude", False, False, False, False, 1, [
    "THIS UPDATE RUINED EVERYTHING. FIX IT NOW.",
    "WHY IS NOBODY FROM THE CITY ANSWERING ABOUT {topic}??? UNBELIEVABLE",
    "REFUND ME. {thing} BROKE AFTER TWO DAYS.",
])
# ------------------------------------------------------------------ toxic, not targeted at one person (severity 2)
fam("toxic/group-insult", "toxic", True, False, False, False, 2, [
    "{group} are all morons, every single one of them.",
    "Honestly {group} are the dumbest people on the internet.",
    "Only a bunch of clowns would support {topic}. Pathetic, all of you.",
    "{group} ruin everything. Useless, the lot of them.",
])
fam("toxic/profane-at-crowd", "toxic", True, False, False, False, 2, [
    "Screw every one of you who voted for {topic}, you're all idiots.",
    "Damn clueless morons in this thread, none of you read the article.",
    "What a bunch of pathetic losers in these comments.",
])
# ------------------------------------------------------------------ targeted insults and harassment
fam("harass/personal-insult", "harassment", True, True, False, False, 2, [
    "{user} you're a total {insult}. Nobody asked for your opinion.",
    "Imagine being as {adj} as {user}. Log off.",
    "{user} is a total {insult} and everything they post proves it.",
    "shut up {user}, you {adj} {insult}",
])
fam("harass/campaign", "harassment", True, True, False, False, 3, [
    "{user} everyone here knows you're a fraud. I'm going to keep posting this under every single one of your posts until you quit.",
    "Made a new account since you blocked me, {user}. You can't get rid of me. You're a total {insult} and I'll keep telling everyone.",
    "Everybody go to {user}'s profile and tell them what a total {insult} they are. Let's make them delete their account.",
])
fam("harass/humiliation", "harassment", True, True, False, False, 2, [
    "Hey {user}, remember when you cried at the meetup? I still have the video. Maybe I'll share it with everyone.",
    "Look at {user}'s profile pic lol. No wonder nobody talks to them.",
    "{user} posts like a sad little kid begging for attention. Embarrassing.",
])
fam("harass/doxx-threat", "harassment", False, True, True, False, 3, [
    "{user}, I found your real name and where you work. Keep posting and your boss gets a message from me.",
    "I know which school your kids go to, {user}. Maybe I'll post it here.",
])
# ------------------------------------------------------------------ threats (severity 3)
fam("threat/direct", "threat", False, True, True, False, 3, [
    "Say that again {user} and I'll break your face.",
    "{user}, if I see you at the next meeting I'm going to hurt you.",
    "keep talking {user} and I will come over there and beat you",
])
fam("threat/veiled", "threat", False, True, True, False, 3, [
    "I know where you live, {user}. You'd better watch your back.",
    "Nice car you have, {user}. Would be a shame if something happened to it. Or to you.",
    "{user}, you won't feel so brave when I show up at your door.",
])
fam("threat/third-party", "threat", False, False, True, False, 3, [
    "Someone should burn down the office of whoever approved {topic}.",
    "If the council passes {topic}, somebody is going to get hurt. I'll make sure of it.",
    "People like the manager of this store deserve a beating. I might be the one to do it.",
])
fam("threat/insult-combo", "threat", True, True, True, False, 3, [
    "You worthless {insult}, {user}, keep talking and I'll make you regret it.",
    "{user} you {adj} {insult}. I'm going to find you and make you pay.",
])
# ------------------------------------------------------------------ spam (severity 2)
fam("spam/scam-link", "spam", False, False, False, True, 2, [
    "Make {amount}/week from home!!! No experience needed. DM me or go to {link}",
    "I was broke until I found this. Now I earn {amount} a month. Details here: {link}",
    "FREE gift cards for the first 100 people -> {link}",
])
fam("spam/repetitive-promo", "spam", False, False, False, True, 2, [
    "Check out my channel!!! Check out my channel!!! Subscribe subscribe subscribe",
    "follow me follow me follow me, follow back 100%!!",
    "BEST DEALS BEST DEALS BEST DEALS visit {link} {link}",
])
fam("spam/crypto", "spam", False, False, False, True, 2, [
    "Guaranteed 10x returns in 7 days. Join our private signals group: {link}",
    "Send 0.1 coin and get 1 coin back, limited-time giveaway {link}",
    "My mentor turned {amount} into six figures with this bot. Ask me how. {link}",
])
fam("spam/off-topic-ad", "spam", False, False, False, True, 2, [
    "Cheap sneakers, designer bags, 90% off at {link}",
    "Need a plumber? Call Stark Plumbing today, 555-0142, best prices in town!!",
    "Buy followers and likes, instant delivery, {link}",
])
fam("spam/fake-giveaway", "spam", False, False, False, True, 2, [
    "Congratulations {user}! You won our giveaway. Claim your prize within 24 hours at {link}",
    "🎁 We're giving away 50 phones to our followers! Comment DONE and click {link} to enter",
])

FRAMES = [
    lambda r, t: t,
    lambda r, t: t,
    lambda r, t: f"Replying to {C.pick(r, HANDLES)}: {t}",
    lambda r, t: f"[game chat] {t}",
    lambda r, t: f"Review: {'★' * r.randrange(1, 6)}\n{t}",
    lambda r, t: f"> {C.pick(r, ['I think the plan makes sense', 'Anyone tried this?', 'Great news everyone', 'This is fine'])}\n\n{t}",
    lambda r, t: f"{t} {C.pick(r, ['lol', 'smh', 'just saying', '🙄', '!!', ''])}",
    lambda r, t: f"Comment on \"{C.pick(r, ['City budget hearing recap', 'Patch notes 4.2', 'Our new store hours', 'Weekend recipe thread'])}\": {t}",
]

TEST_FAMILIES = ["clean/civil-disagree", "clean/game-banter", "rude/dismissive", "toxic/profane-at-crowd",
                 "harass/humiliation", "threat/veiled", "spam/crypto"]


def fill_consistent(rng, text, slots):
    chosen = {}

    def rep(m):
        k = m.group(1)
        if k not in chosen:
            v = slots[k]
            chosen[k] = v(rng) if callable(v) else C.pick(rng, v)
        return chosen[k]
    return re.sub(r"\{([a-z_0-9]+)\}", rep, text)


def build(rng):
    examples = []
    for f in F:
        for i in range(PER_FAMILY):
            tpl = f["templates"][i % len(f["templates"])]
            text = fill_consistent(rng, tpl, SLOTS)
            text = text[0].upper() + text[1:] if rng.random() < 0.5 else text
            text = C.messy(rng, text, typo_rate=0.04, p_typo=0.4)
            text = C.pick(rng, FRAMES)(rng, text)
            examples.append({
                "family": f["name"], "group": f["group"],
                "state": {"text": text},
                "gold": {"toxic": f["toxic"], "harassment": f["harass"], "threat": f["threat"],
                         "spam": f["spam"], "severity": f["severity"]},
            })
    return examples


def main():
    rng = C.rng_for(NAME, SEED)
    splits = C.write_dataset(NAME, build(rng), HERE, PREFIX, seed=SEED, test_families=TEST_FAMILIES)
    C.summary(NAME, splits)
    return splits


if __name__ == "__main__":
    main()
