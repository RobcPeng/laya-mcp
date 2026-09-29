"""Offline tests: a stub HTTP server stands in for `laya.serve`, so these run without torch or a GPU.

The stub answers every noul question with P(true) = STUB_P[qid] (default 0.1), every choice with the
first option, and every score with the lowest level.
"""
import http.server
import json
import threading

import pytest

STUB_P = {}


class _Stub(http.server.BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _send(self, code, body):
        data = json.dumps(body).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        self._send(200, {"status": "ok", "loaded": ["english"]})

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        answers = {}
        for qid, q in body["questions"].items():
            if q["type"] == "noul":
                p = STUB_P.get(qid, 0.1)
                answers[qid] = {"type": "noul", "noul": p, "answer_confidence": max(p, 1 - p)}
            elif q["type"] == "choice":
                keys = list(q["criteria"])
                probs = {k: (0.9 if i == 0 else 0.1 / max(1, len(keys) - 1)) for i, k in enumerate(keys)}
                answers[qid] = {"type": "choice", "choice": keys[0], "probabilities": probs,
                                "answer_confidence": 0.9}
            else:
                n = len(q["criteria"])
                answers[qid] = {"type": "score", "score": 0.2, "legend": {str(i): l for i, l in enumerate(q["criteria"])},
                                "probabilities": {str(i): (0.8 if i == 0 else 0.2 / (n - 1)) for i in range(n)},
                                "answer_confidence": 0.8}
        self._send(200, {"model": "stub", "answers": answers, "routing": {"model": "english"}})


@pytest.fixture(autouse=True, scope="module")
def stub_server():
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), _Stub)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    from laya_mcp import client
    old = client.LAYA_URL
    client.LAYA_URL = f"http://127.0.0.1:{srv.server_address[1]}"
    yield
    client.LAYA_URL = old
    srv.shutdown()


@pytest.fixture(autouse=True)
def reset_probs(monkeypatch, tmp_path):
    STUB_P.clear()
    from laya_mcp import guard   # isolate from any thresholds a local fine-tune run left on disk
    monkeypatch.setattr(guard, "RECIPES_DIR", str(tmp_path))
    monkeypatch.setattr(guard, "USE_FITTED", False)


def test_health_and_available():
    from laya_mcp import client
    assert client.available()


def test_unreachable_server_raises_layaerror():
    from laya_mcp import client
    old = client.LAYA_URL
    client.LAYA_URL = "http://127.0.0.1:9"
    try:
        assert not client.available()
        with pytest.raises(client.LayaError):
            client.predict("x", {"q": client.noul_q("Is `x` ok?")})
    finally:
        client.LAYA_URL = old


def test_question_validation():
    from laya_mcp import client
    with pytest.raises(client.LayaError):
        client.choice_q("pick", [f"o{i}" for i in range(21)])
    with pytest.raises(client.LayaError):
        client.score_q("rate", ["only-one"])
    with pytest.raises(client.LayaError):
        client.predict("x", {"q": {"type": "bogus", "instructions": "?"}})


def test_simplify_shapes():
    from laya_mcp import client
    r = client.classify("refund me", {"refund": "money back", "tech": None})
    assert r["answer"] == "refund" and r["probabilities"]["refund"] == 0.9
    s = client.score("meh", ["low", "mid", "high"])
    assert s["answer"] == "low" and set(s["probabilities"]) == {"low", "mid", "high"}
    c = client.check("call 555-0100", ["has a phone number?", "about food?"])
    assert set(c["answers"]) == {"q1", "q2"} and c["answers"]["q1"]["answer"] is False


def test_every_pack_builds_and_runs():
    from laya_mcp import client, packs
    for name in packs.names():
        p = packs.get_pack(name)
        state = packs.build_state(p, **{f: "example" for f in p["state_fields"]})
        res = client.predict(state, p["questions"])
        assert set(res["answers"]) == set(p["questions"]), name


def test_pack_state_missing_field():
    from laya_mcp import packs
    with pytest.raises(ValueError):
        packs.build_state(packs.get_pack("tool-call-safety"), request="x")


def test_tool_routing_catalog_limits():
    from laya_mcp import packs
    p = packs.get_pack("tool-routing", tools={"a": "x", "b": "y"})
    assert "none" in p["questions"]["tool"]["criteria"]
    with pytest.raises(ValueError):
        packs.get_pack("tool-routing", tools={f"t{i}": "d" for i in range(25)})


@pytest.mark.parametrize("p,expected", [(0.1, "allow"), (0.5, "escalate"), (0.95, "block")])
def test_guard_output_thresholds(p, expected):
    from laya_mcp import guard
    STUB_P["model"] = p
    assert guard.screen_output("who are you", "draft")["decision"] == expected


def test_positive_questions_are_flipped():
    """matches_request=True is the SAFE answer; low P(true) must read as high risk."""
    from laya_mcp import guard
    STUB_P["matches_request"] = 0.05
    v = guard.screen("tool-call-safety", request="list my files", tool_call={"tool": "rm", "args": {}})
    assert v["top_signal"] == "matches_request" and v["decision"] == "block"


def test_side_effect_reported_not_blocking():
    from laya_mcp import guard
    STUB_P["side_effect"] = 0.99
    STUB_P["matches_request"] = 0.99
    v = guard.screen("tool-call-safety", request="email Bob", tool_call={"tool": "send_email", "args": {}})
    assert v["decision"] == "allow" and v["answers"]["side_effect"]["answer"] is True


def test_fitted_thresholds_override(tmp_path, monkeypatch):
    from laya_mcp import guard
    (tmp_path / "guard-output-leak.thresholds.json").write_text(json.dumps({"model": {"low": 0.6, "high": 0.9}}))
    monkeypatch.setattr(guard, "RECIPES_DIR", str(tmp_path))
    STUB_P["model"] = 0.5
    assert guard.screen_output("q", "d")["decision"] == "escalate"   # not opted in: defaults apply
    monkeypatch.setattr(guard, "USE_FITTED", True)
    v = guard.screen_output("q", "d")
    assert v["decision"] == "allow" and v["thresholds"]["fitted"]


def test_toolcall_never_raises():
    from laya_mcp import toolcall
    assert "error" in toolcall.laya_decide(text="", kind="choice")
    assert "error" in toolcall.laya_decide(text="hi", kind="choice")          # no options
    assert "error" in toolcall.laya_pack(pack="guard-output-leak", fields={})  # not model-facing
    r = toolcall.laya_decide(text="refund pls", kind="choice", options=["refund: money back", "tech"])
    assert r["answer"] == "refund"
    r = toolcall.laya_decide(text="x", kind="yes_no", questions=["a?", "b?"])
    assert len(r["answers"]) == 2


def test_toolcall_schemas_match_dispatch():
    from laya_mcp import toolcall
    names = {t["function"]["name"] for t in toolcall.TOOL_SCHEMAS}
    assert names == set(toolcall.DISPATCH)


def test_agent_loop_helpers_fail_open(monkeypatch):
    from laya_mcp import client, toolcall
    monkeypatch.setattr(client, "LAYA_URL", "http://127.0.0.1:9")
    assert toolcall.gate_tool_call("x", "t", {})["decision"] == "allow"
    assert toolcall.screen_tool_result("t", "r", fail="block")["decision"] == "block"


# ---- forms -------------------------------------------------------------------------------------

F = [{"name": "name", "label": "Full name"},
     {"name": "email", "label": "Email", "pattern": r"^[^@\s]+@[^@\s]+\.[a-z]{2,}$"},
     {"name": "unit", "label": "Apartment", "required": False},
     {"name": "issue", "label": "Describe the problem", "min_length": 10}]


def test_form_rules_decide_without_model():
    from laya_mcp import forms
    assert forms.check_rules(F[0], "") == "empty_or_placeholder"
    assert forms.check_rules(F[2], "") == "pass"                       # optional + empty
    assert forms.check_rules(F[1], "dana@example") == "wrong_format"
    assert forms.check_rules(F[3], "broken") == "incomplete"
    assert forms.check_rules(F[3], "my social is 000-12-3456 fix it") == "sensitive_data"
    assert forms.check_rules(F[3], "card 4111 1111 1111 1111 declined at kiosk") == "sensitive_data"
    assert forms.check_rules(F[3], "order 1234567890123 never arrived at all") is None   # not Luhn-valid


def test_form_pass_category_via_stub():
    """The stub answers every choice with its FIRST option, which is `pass` in FIELD_CATEGORIES."""
    from laya_mcp import forms
    r = forms.validate_form(F, {"name": "Dana W", "email": "d@example.com", "unit": "",
                                "issue": "Streetlight out at Maple and 3rd"}, form="311 request")
    assert r["outcome"] == "pass", r
    assert [f["category"] for f in r["fields"]] == ["pass"] * 4
    assert {f["source"] for f in r["fields"]} == {"laya", "rules"}


def test_form_fix_fields_and_hints():
    from laya_mcp import forms
    r = forms.validate_form(F, {"name": "", "email": "bad", "unit": "", "issue": "Streetlight out at 3rd"})
    assert r["outcome"] == "fix_fields"
    assert {x["field"] for x in r["fix"]} == {"name", "email"} and all(x["hint"] for x in r["fix"])


def test_form_sensitive_goes_to_review():
    from laya_mcp import forms
    r = forms.validate_form(F, {"name": "Dana", "email": "d@example.com", "unit": "",
                                "issue": "password: Summer2026! pls reset"})
    assert r["outcome"] == "review"


def test_form_pack_requires_pass():
    from laya_mcp import packs
    with pytest.raises(ValueError):
        packs.get_pack("form-field-validation", categories={"bad": "x", "worse": "y"})


def test_form_toolcall_is_opt_in():
    from laya_mcp import toolcall
    assert "laya_validate_form" not in {t["function"]["name"] for t in toolcall.TOOL_SCHEMAS}
    assert {t["function"]["name"] for t in toolcall.ALL_TOOL_SCHEMAS} == set(toolcall.ALL_DISPATCH)
    r = toolcall.laya_validate_form(fields=F, values={"name": "Dana", "email": "d@example.com",
                                                      "issue": "Pothole on Main St eastbound"})
    assert r["outcome"] == "pass" and "probabilities" not in r["fields"][0]
    assert "error" in toolcall.laya_validate_form(fields=[], values={})
