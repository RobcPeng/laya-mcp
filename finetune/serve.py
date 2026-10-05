#!/usr/bin/env python3
"""Serve a fine-tuned checkpoint, or base + a LoRA adapter, through laya's own HTTP server
(`laya.serve`, /v1/systemone).

Two ways in, one per kind of artifact:

  LAYA_LORA_ADAPTER=<adapter dir>        base + adapter, combined in memory at load time. The base is the
                                         stock checkpoint named in the adapter's config (read from the Hub
                                         cache, never modified); the adapter is a few tens of MB. This is
                                         the path for `strategy: "lora"` recipes.
  LAYA_CUSTOM_CHECKPOINT=<checkpoint dir> a full checkpoint (`full` / `head` / `calibrate` strategies).

Either goes into one slot (LAYA_CUSTOM_SLOT, default `typed-decisions`, which only answers requests
that ask for it by name), so the stock english/multilingual auto-routing is unchanged:

    LAYA_LORA_ADAPTER=runs/ridgeback-guard/<run>/checkpoint \\
    LAYA_HOST=127.0.0.1 LAYA_PORT=7492 LAYA_MODELS=typed-decisions python -m finetune.serve

  request {"model": "typed-decisions", ...}  -> base + adapter
  request with no model                       -> the stock auto-routing

LAYA_CUSTOM_SLOT=english makes the adapted model answer every English request (a dedicated server).
Every other laya.serve env var (LAYA_DEVICE, LAYA_API_KEY, LAYA_MAX_LOADED, ...) works unchanged.
"""
import os

os.environ.setdefault("USE_TF", "0")


def main():
    import laya.serve as serve
    from laya.mcp.device import env_device
    from laya.router import Router

    adapter = os.environ.get("LAYA_LORA_ADAPTER")
    ckpt = os.environ.get("LAYA_CUSTOM_CHECKPOINT")
    slot = os.environ.get("LAYA_CUSTOM_SLOT", "typed-decisions")
    if adapter:
        from finetune import lora
        if not lora.is_adapter(adapter):
            raise SystemExit(f"LAYA_LORA_ADAPTER={adapter} has no {lora.CONFIG}")
    elif not ckpt or not os.path.isfile(os.path.join(ckpt, "rl_agent_config.json")):
        raise SystemExit("set LAYA_LORA_ADAPTER to an adapter dir, or LAYA_CUSTOM_CHECKPOINT to a checkpoint dir")

    def build_router():
        serve._apply_thread_limit()
        opts = {"device": env_device(), "auto_task_detection": serve._env_bool("LAYA_AUTO_TASK", False)}
        if ckpt and not adapter:
            opts["models"] = {slot: os.path.abspath(ckpt)}
        ml = serve._resolve_max_loaded()
        if ml is not None:
            opts["max_loaded"] = ml
        router = Router(**opts)
        if adapter:
            from finetune import lora
            agent = lora.load_agent(adapter, device=env_device())
            router.attach(slot, agent)
            # Pin it. The router evicts least-recently-used checkpoints past `max_loaded`, and a later
            # request for an evicted slot would rebuild the plain base from the Hub, silently serving
            # without the adapter. Three slots exist, so a cap of 3 means nothing is ever evicted; and
            # the slot's loader always answers with this agent.
            router.max_loaded = max(router.max_loaded, 3)
            from laya.router import normalise_name
            pinned, plain_load = normalise_name(slot), router.load
            router.load = lambda name, _p=pinned, _a=agent, _l=plain_load: _a if normalise_name(name) == _p else _l(name)
            print(f"[serve] {slot} = base {agent.adapter['base']} + adapter {agent.adapter['dir']} "
                  f"({agent.adapter['params']['total']:,} adapter params)", flush=True)
        if serve._env_bool("LAYA_PRELOAD", True):
            names = [m.strip() for m in os.environ.get("LAYA_MODELS", "").split(",") if m.strip()] or None
            router.preload(names)
        return router

    serve.build_router = build_router
    serve.main()


if __name__ == "__main__":
    main()
