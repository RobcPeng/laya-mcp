"""MLflow pyfunc wrapper so a fine-tuned checkpoint can be registered, versioned and served with
`mlflow models serve` or loaded with `mlflow.pyfunc.load_model`.

Input: a DataFrame (or list of dicts) with columns
    state      dict or JSON string
    questions  dict or JSON string (a laya_mcp pack's "questions")
Output: one JSON string per row: the laya result ({"answers", "usage", "routing"...}).
"""
import json
import os

import mlflow.pyfunc


def _as_obj(v):
    return json.loads(v) if isinstance(v, str) else v


class LayaModel(mlflow.pyfunc.PythonModel):
    def load_context(self, context):
        os.environ.setdefault("USE_TF", "0")
        from laya.agent import Agent
        self.agent = Agent(context.artifacts["checkpoint"], device=os.environ.get("LAYA_DEVICE") or None)

    def predict(self, context, model_input, params=None):
        records = model_input.to_dict("records") if hasattr(model_input, "to_dict") else list(model_input)
        out = []
        for rec in records:
            res = self.agent.predict(_as_obj(rec["state"]), _as_obj(rec["questions"]))
            out.append(json.dumps(res, default=str))
        return out


def log_model(mlflow, checkpoint_dir, registered_name=None, example=None):
    """Log (and optionally register) the checkpoint as a pyfunc model. Returns the ModelInfo."""
    here = os.path.dirname(os.path.abspath(__file__))
    kw = {}
    if example is not None:
        # an explicit signature instead of input_example, because input_example makes MLflow load the model
        # into this instance and then pickle it, and the loaded Agent holds locks that cannot be pickled
        import pandas as pd
        from mlflow.models import infer_signature
        df = pd.DataFrame([{"state": json.dumps(example["state"]), "questions": json.dumps(example["questions"])}])
        kw["signature"] = infer_signature(df, ["{\"answers\": {}}"])
    return mlflow.pyfunc.log_model(
        name="model", python_model=LayaModel(), artifacts={"checkpoint": checkpoint_dir},
        code_paths=[here], pip_requirements=["laya>=0.3.21", "torch", "safetensors", "pandas"],
        registered_model_name=registered_name, **kw)
