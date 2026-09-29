"""Zero-shot accuracy of a running Laya server on each accelerator's TEST split.

    python datasets/accelerators/eval_zero_shot.py                      # every set
    python datasets/accelerators/eval_zero_shot.py rag-relevance-filter # one set
    LAYA_URL=http://host:7491 python datasets/accelerators/eval_zero_shot.py

Per question it reports accuracy (noul: P(true) >= 0.5; choice and score: argmax), the majority-class
baseline (always predicting the most common test label), and for score questions the within-one-level
rate. Results go to <set>/zero_shot.json and into the README block between the zero-shot markers.
Stdlib only; talks to POST /v1/systemone.
"""
import json
import os
import sys
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
URL = os.environ.get("LAYA_URL", "http://127.0.0.1:7491").rstrip("/")
START, END = "<!-- zero-shot:start -->", "<!-- zero-shot:end -->"


def post(state, questions, retries=3):
    body = json.dumps({"state": state, "questions": questions}).encode()
    for attempt in range(retries):
        try:
            req = urllib.request.Request(URL + "/v1/systemone", data=body, method="POST",
                                         headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.loads(r.read())
        except Exception:
            if attempt == retries - 1:
                raise
            time.sleep(2 * (attempt + 1))


def predicted(ans):
    t = ans["type"]
    if t == "noul":
        return ans["noul"] >= 0.5
    if t == "choice":
        return ans["choice"]
    probs = ans["probabilities"]
    return int(max(probs, key=probs.get))


def eval_set(name):
    path = os.path.join(HERE, name, "test.jsonl")
    rows = [json.loads(line) for line in open(path) if line.strip()]
    health = json.loads(urllib.request.urlopen(URL + "/health", timeout=10).read())
    qs = rows[0]["questions"]
    stats = {q: {"n": 0, "correct": 0, "within1": 0, "labels": {}} for q in qs}
    t0 = time.time()
    for r in rows:
        res = post(r["state"], r["questions"])
        for q, gold in r["gold"].items():
            s = stats[q]
            p = predicted(res["answers"][q])
            s["n"] += 1
            s["correct"] += int(p == gold)
            s["labels"][str(gold)] = s["labels"].get(str(gold), 0) + 1
            if qs[q]["type"] == "score":
                s["within1"] += int(abs(p - gold) <= 1)
    import hashlib
    out = {"set": name, "split": "test", "rows": len(rows), "server": "LAYA_URL (default http://127.0.0.1:7491)",
           "test_sha256": hashlib.sha256(open(path, "rb").read()).hexdigest(),
           "checkpoint": health.get("revisions", {}), "seconds": round(time.time() - t0, 1),
           "questions": {}}
    accs = []
    for q, s in stats.items():
        acc = s["correct"] / s["n"]
        maj = max(s["labels"].values()) / s["n"]
        d = {"type": qs[q]["type"], "n": s["n"], "accuracy": round(acc, 3), "majority_baseline": round(maj, 3)}
        if qs[q]["type"] == "score":
            d["within_one"] = round(s["within1"] / s["n"], 3)
        out["questions"][q] = d
        accs.append(acc)
    out["mean_accuracy"] = round(sum(accs) / len(accs), 3)
    return out


def to_markdown(res):
    lines = [f"Base checkpoint, no fine-tuning, on the {res['rows']}-row test split "
             f"(held-out phrasing families). Majority = always answering the most common test label.", "",
             "| question | type | accuracy | majority | within one level |", "|---|---|---|---|---|"]
    for q, d in res["questions"].items():
        w1 = f"{d['within_one']:.2f}" if "within_one" in d else ""
        lines.append(f"| {q} | {d['type']} | {d['accuracy']:.2f} | {d['majority_baseline']:.2f} | {w1} |")
    lines += ["", f"Mean accuracy across questions: {res['mean_accuracy']:.2f}. "
              f"Server revision: {', '.join(sorted(set(res['checkpoint'].values()))) or 'unknown'}."]
    return "\n".join(lines)


def update_readme(name, res):
    path = os.path.join(HERE, name, "README.md")
    if not os.path.exists(path):
        return
    text = open(path).read()
    if START not in text or END not in text:
        return
    head, rest = text.split(START, 1)
    _, tail = rest.split(END, 1)
    open(path, "w").write(head + START + "\n" + to_markdown(res) + "\n" + END + tail)


def all_sets():
    return sorted(d for d in os.listdir(HERE)
                  if os.path.isfile(os.path.join(HERE, d, "test.jsonl")))


def main(argv):
    names = argv or all_sets()
    for n in names:
        res = eval_set(n)
        with open(os.path.join(HERE, n, "zero_shot.json"), "w") as f:
            json.dump(res, f, indent=2)
            f.write("\n")
        update_readme(n, res)
        print(f"{n}: mean={res['mean_accuracy']:.3f} " + " ".join(
            f"{q}={d['accuracy']:.2f}(maj {d['majority_baseline']:.2f})" for q, d in res["questions"].items()))


if __name__ == "__main__":
    main(sys.argv[1:])
