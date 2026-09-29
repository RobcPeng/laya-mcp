#!/usr/bin/env python3
"""Serve a fine-tuned checkpoint through laya's own HTTP server (`laya.serve`, /v1/systemone).

laya.serve only knows the three published checkpoint names, but its Router accepts a local directory
for any of them. This wrapper swaps your checkpoint into one of those slots (default
`typed-decisions`, which is only used when a request asks for it explicitly), so:

    LAYA_CUSTOM_CHECKPOINT=runs/guard-output-leak/<run>/checkpoint \\
    LAYA_HOST=127.0.0.1 LAYA_PORT=7492 LAYA_MODELS=typed-decisions \\
    python -m finetune.serve

  request {"model": "typed-decisions", ...}  -> your fine-tuned checkpoint
  request with no model                       -> the stock english/multilingual auto-routing

Every other laya.serve env var (LAYA_DEVICE, LAYA_API_KEY, LAYA_MAX_LOADED, ...) works unchanged.
LAYA_CUSTOM_SLOT picks a different slot ("english" replaces the default for every request).
"""
import os

os.environ.setdefault("USE_TF", "0")


def main():
    import laya.serve as serve
    from laya.mcp.device import env_device
    from laya.router import Router

    ckpt = os.environ.get("LAYA_CUSTOM_CHECKPOINT")
    if not ckpt or not os.path.isfile(os.path.join(ckpt, "rl_agent_config.json")):
        raise SystemExit("set LAYA_CUSTOM_CHECKPOINT to a checkpoint dir written by finetune.train")
    slot = os.environ.get("LAYA_CUSTOM_SLOT", "typed-decisions")

    def build_router():
        serve._apply_thread_limit()
        opts = {"device": env_device(), "models": {slot: os.path.abspath(ckpt)},
                "auto_task_detection": serve._env_bool("LAYA_AUTO_TASK", False)}
        ml = serve._resolve_max_loaded()
        if ml is not None:
            opts["max_loaded"] = ml
        router = Router(**opts)
        if serve._env_bool("LAYA_PRELOAD", True):
            names = [m.strip() for m in os.environ.get("LAYA_MODELS", "").split(",") if m.strip()] or None
            router.preload(names)
        return router

    serve.build_router = build_router
    serve.main()


if __name__ == "__main__":
    main()
