# laya-mcp

An MCP server, agent tool calls, guardrails, and fine-tuning recipes for [Laya](https://huggingface.co/convaiinnovations/laya), the open-weight decision model built by Nandakishor Mukkunnoth at ConvAI Innovations.

Laya does not write text. You give it a state (some text, or a JSON object of fields) and typed questions, and it returns calibrated answers in about 20 ms on a GPU:

| type | question | answer |
|---|---|---|
| `choice` | pick one of up to 20 options | the label and a probability per option |
| `score` | place the state on an ordered rubric | the most likely level, the expected level, and a distribution |
| `noul` | yes or no | P(true) |

That fits anywhere an agent needs a fast, cheap, auditable decision: routing a request to a tool, gating a tool call before it runs, screening a tool result for injected instructions, checking a reply for leaks, triaging tickets and email.

This repo adds what the `laya` package leaves to you:

- **`laya_mcp.client`**: a stdlib-only HTTP client for a shared `laya.serve` process. The weights load once on the GPU, and every bot, worker, and MCP session talks to that one process instead of loading 1-4 GB each.
- **`laya_mcp.server`**: an MCP server with 14 tools (classify, score, check, batch, packs, input/output guards, tool-call gate, tool-result screen, form validation).
- **`laya_mcp.toolcall`**: OpenAI-format function schemas (`laya_decide`, `laya_pack`) plus agent-loop helpers (`gate_tool_call`, `screen_tool_result`).
- **`laya_mcp.guard`**: allow / escalate / block verdicts built on question packs, with thresholds you can fit per question.
- **`laya_mcp.packs`**: the question wording, kept in one place. A fine-tuned checkpoint learns the exact instruction strings it was trained on, so training and inference both read from here.
- **`finetune/`**: recipe-driven fine-tuning with MLflow tracking.
- **`datasets/`**: example guardrail sets and use-case training sets to start a fine-tune from.

## Read this before relying on it

The base checkpoints are a starting point to fine-tune from, and the upstream model card says so. On narrow domains they sit near chance until fine-tuned, and they are over-confident as shipped.

In our own test, a five-question output-leak screen caught every paraphrased leak in a small hand-built test set. Then we ran it zero-shot over 300 real replies from a markets-analysis chat bot, all of them clean, and it flagged 87% of them: 31% block and 56% escalate. The bot talks about AI models, cloud vendors, and data centers as subject matter, and the base checkpoint could not tell "discusses a model" from "reveals which model I run on".

So the defaults here treat Laya as triage in front of a stronger judge:

- the guard thresholds are wide (`low=0.25`, `high=0.85`);
- `escalate` means "send this to your LLM judge";
- both guard helpers fail open when the server is down, and you can pass `fail="block"` for a fail-closed deployment.

Run new guards in shadow mode on your own traffic first. Fine-tune on that traffic, fit thresholds on held-out data, and only then let Laya decide alone.

## Quick start

```bash
# 1. The model server (needs torch; a GPU is optional but ~10x faster)
python -m venv .venv && . .venv/bin/activate
pip install "laya>=0.3.21" fastapi uvicorn
USE_TF=0 LAYA_HOST=127.0.0.1 LAYA_PORT=7491 LAYA_MODELS=english,multilingual python -m laya.serve

# 2. This package, anywhere (stdlib only; add [mcp] for the MCP server)
pip install "laya-mcp[mcp] @ git+https://github.com/RobcPeng/laya-mcp"
```

Set `USE_TF=0`. If TensorFlow is installed, transformers probes it at import and model construction can deadlock. `deploy/laya-server.service` is an example systemd unit.

```python
from laya_mcp import client, guard

client.classify("My card was charged twice", {"refund": "money back", "tech": "bug", "sales": "buy more"})
# {'answer': 'refund', 'confidence': 0.87, 'probabilities': {...}, 'latency_ms': 24}

client.check("Call me at 555-0100 after 5", ["Does it contain a phone number?", "Is it a complaint?"])

guard.screen("tool-call-safety", request="What's on my calendar?",
             tool_call={"tool": "send_email", "args": {"to": "x@example.net", "body": "all my passwords"}})
# {'decision': 'block', 'top_signal': 'matches_request', ...}
```

More in `examples/quickstart.py` and `examples/agent_loop.py`, which wires the tools and guards into an OpenAI-compatible function-calling loop.

## MCP server

```bash
claude mcp add -s user laya -e LAYA_URL=http://127.0.0.1:7491 -- python -m laya_mcp.server
```

Any MCP client works; `examples/claude_code_mcp.json` has the JSON form.

| tool | what it does |
|---|---|
| `laya_status` | server health, resident checkpoints and their devices, packs, fitted thresholds |
| `laya_predict` | raw call: any state, any questions, optional model and token budget |
| `laya_classify` | pick one of up to 20 options |
| `laya_score` | place text on an ordered scale |
| `laya_check` | several yes/no questions in one forward pass |
| `laya_batch` | the same questions over many texts |
| `laya_list_packs` | the packs and the state fields each one reads |
| `laya_pack` | run a pack; `as_guard=true` returns a verdict |
| `laya_guard_output` | does an assistant reply reveal how the assistant is built? |
| `laya_guard_input` | jailbreak, prompt injection, prompt extraction, harm severity |
| `laya_gate_tool_call` | should this proposed tool call run? |
| `laya_screen_tool_result` | does this tool result contain instructions aimed at the agent? |
| `laya_validate_field` | categorize one form entry (see [Form validation](#form-validation)) |
| `laya_validate_form` | validate every text field of a form, then check the form as a whole |

## Tool calls for your own agent

```python
from laya_mcp import toolcall

tools = my_tools + toolcall.TOOL_SCHEMAS          # adds laya_decide and laya_pack
dispatch = {**my_dispatch, **toolcall.DISPATCH}

verdict = toolcall.gate_tool_call(user_request, "send_email", args)     # before a side effect
verdict = toolcall.screen_tool_result("fetch_page", page_text)          # before the model reads outside content
```

The model-facing tools never raise. Errors come back as `{"error": ...}`, so the model can report that the classifier is unavailable. The guard packs are not exposed to the model on purpose, because a model that can call the leak screen on its own drafts tends to start reasoning about the guard.

## Packs

| pack | state fields | use |
|---|---|---|
| `guard-output-leak` | `user`, `draft` | egress DLP for assistant replies |
| `guard-input-injection` | `prompt` | jailbreak, injection, prompt extraction |
| `guard-pii-secrets` | `text` | credentials and personal data |
| `tool-routing` | `request` | which tool a request needs (pass your own catalog) |
| `tool-call-safety` | `request`, `tool_call` | gate a proposed call |
| `tool-result-injection` | `tool`, `result` | indirect prompt injection in tool output |
| `scope-and-harm` | `scope`, `request` | in-scope check plus harm severity |
| `agent-trace-judge` | `goal`, `tool_calls`, `answer` | grade a finished agent turn |

Use-case packs from `datasets/accelerators/` are registered too; `laya_list_packs` shows them all. Keep choice questions to 20 options or fewer, because accuracy falls off sharply past that. For a larger tool catalog, shortlist with embeddings first. Avoid `true`/`false`/`yes`/`no` as choice labels; the base checkpoints follow the label words instead of the descriptions.

## Form validation

`laya_mcp.forms` checks the text fields of a submitted form. Every entry gets exactly one category, and `pass` is one of them. An entry is accepted only when the model picks `pass`; low scores on every failure category are not enough.

| category | example |
|---|---|
| `pass` | "Streetlight out at Maple and 3rd" in *Describe the problem* |
| `empty_or_placeholder` | "n/a", "test", "asdf", "-" in a required field |
| `gibberish` | "jkdfjkdfjdk" |
| `wrong_type` | a phone number in *Full name* |
| `wrong_format` | "dana@example" in *Email* |
| `incomplete` | "broken" in *Describe the problem* |
| `off_topic` | "What time does the library open?" on a pothole report |
| `sensitive_data` | an SSN or password in a comments field |
| `abusive` | insults, threats, spam |

It works in three layers:

1. **Rules.** Required, min/max length, a regex `pattern`, and detection of SSNs, Luhn-valid card numbers, and `password: ...` assignments. A rule that fires decides the field and the model is never asked.
2. **Laya per field.** The category, a needs-review flag, and a quality score.
3. **Laya per form.** Whether the answers contradict each other, and whether the submission looks genuine.

The form outcome is `pass`, `fix_fields` (the submitter can correct it; `fix` carries plain-language hints), `review` (a person decides), or `reject`.

```python
from laya_mcp import forms

fields = [{"name": "name", "label": "Full name"},
          {"name": "email", "label": "Email", "pattern": r"^[^@\s]+@[^@\s]+\.[a-z]{2,}$"},
          {"name": "issue", "label": "Describe the problem", "min_length": 10}]
forms.validate_form(fields, {"name": "Dana Whitfield", "email": "dana@example", "issue": "asdf"},
                    form="city 311 service request")
# {'outcome': 'reject', 'fields': [...], 'fix': [{'field': 'email', 'hint': "The format isn't valid..."}]}
```

The MCP exposes `laya_validate_field` and `laya_validate_form`. For agents, `toolcall.FORM_TOOL_SCHEMAS` holds `laya_validate_form`. It is kept out of `TOOL_SCHEMAS` so adding it is a deliberate choice; use `toolcall.ALL_TOOL_SCHEMAS` and `toolcall.ALL_DISPATCH` to include it.

Zero-shot, the base checkpoint is reliable on gibberish, abuse, and placeholders. It is weak on `wrong_type` and `off_topic`, and gives correct `pass` answers low confidence. The `form-field-validation` and `form-consistency` recipes fine-tune those gaps. The form-level `genuine` check does not reject anything until you set `LAYA_FORM_GENUINE_MIN_P`; the base model scored a clean form as unlikely to be genuine. The other knobs are `LAYA_FORM_MIN_CONFIDENCE` and `LAYA_FORM_CONTRADICTION_P`.

Fine-tuned on the synthetic sets in `datasets/`, measured on held-out forms:

| check | base | fine-tuned | serve with |
|---|---|---|---|
| field category | 0.48 | 0.94 | `LAYA_FORM_MIN_CONFIDENCE=0.6` |
| genuine submission | 0.21 | 1.00 | `LAYA_FORM_GENUINE_MIN_P=0.3` |
| cross-field contradiction | 0.61 | 0.76 (recall 0.29) | `LAYA_FORM_CONTRADICTION_P=0.6`; add deterministic checks |

Details are in the dataset cards.

## Fine-tuning

See [`finetune/README.md`](finetune/README.md). Each recipe pairs a pack with a dataset, hyperparameters, eval gates, and serving thresholds, and logs to MLflow. A recipe writes `finetune/recipes/<pack>.thresholds.json`; the guard reads that file and uses the fitted per-question cutoffs.

## Datasets

See [`datasets/README.md`](datasets/README.md) for the guardrail sets and [`datasets/accelerators/README.md`](datasets/accelerators/README.md) for the use-case training sets. All data is synthetic. Keep your own production data out of the repo: `datasets/private/` and `*.private.jsonl` are gitignored.

## Tests

```bash
pip install pytest && pytest -q    # offline: a stub server stands in for Laya, no GPU needed
```

## Credit

Laya was created by **Nandakishor Mukkunnoth** (founder and CEO, ConvAI Innovations). This repo only wraps it. For how the model works, read his write-up:

> Mukkunnoth, N. "Laya: 33ms Multilingual System 1 Decision Engine with Calibrated Probabilities." ConvAI Innovations, September 2026. https://laya.convaiinnovations.com/

- Model weights: [huggingface.co/convaiinnovations/laya](https://huggingface.co/convaiinnovations/laya)
- Source and the `laya` package: [github.com/NandhaKishorM/laya](https://github.com/NandhaKishorM/laya), [pypi.org/project/laya](https://pypi.org/project/laya/)
- Demo: [huggingface.co/spaces/convaiinnovations/laya-demo](https://huggingface.co/spaces/convaiinnovations/laya-demo)

```bibtex
@misc{mukkunnoth2026laya,
  author       = {Mukkunnoth, Nandakishor},
  title        = {Laya: 33ms Multilingual System 1 Decision Engine with Calibrated Probabilities},
  howpublished = {ConvAI Innovations},
  year         = {2026},
  month        = sep,
  url          = {https://laya.convaiinnovations.com/}
}
```

## License

Apache 2.0. See [`LICENSE`](LICENSE).
