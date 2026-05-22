"""
Ripple orchestrator — runs a primary model then cascades to downstream models.

RIPPLE_GRAPH defines which models trigger which downstream models.
run_with_ripple() executes the cascade and returns results in order.
"""
from .throughput    import ThroughputModel
from .margin        import MarginModel
from .demand_shock  import DemandShockModel
from .labour        import LabourModel
from .waste_recovery import WasteRecoveryModel
from .channel_mix   import ChannelMixModel
from .promotion     import PromotionModel

MODEL_REGISTRY = {
    "ThroughputModel":    ThroughputModel,
    "MarginModel":        MarginModel,
    "DemandShockModel":   DemandShockModel,
    "LabourModel":        LabourModel,
    "WasteRecoveryModel": WasteRecoveryModel,
    "ChannelMixModel":    ChannelMixModel,
    "PromotionModel":     PromotionModel,
}

RIPPLE_GRAPH = {
    "ThroughputModel":    ["LabourModel"],
    "DemandShockModel":   ["MarginModel", "ChannelMixModel"],
    "PromotionModel":     ["MarginModel", "ThroughputModel"],
    "ChannelMixModel":    ["LabourModel", "ThroughputModel"],
    "MarginModel":        [],
    "LabourModel":        [],
    "WasteRecoveryModel": [],
}

# Hand-coded output→input wiring for v1.
# Maps (primary_model, downstream_model) → dict of input kwargs to pass.
# The orchestrator merges this with caller-supplied downstream_inputs.
OUTPUT_WIRING = {
    ("ThroughputModel", "LabourModel"): lambda primary_out: {
        "hourly_demand_curve": None,  # caller must supply; we pass peak as hint
    },
    ("DemandShockModel", "MarginModel"): lambda primary_out: {
        # compression feeds into adjusted food_cost_ratios — caller adjusts
    },
    ("ChannelMixModel", "ThroughputModel"): lambda primary_out: {
        "peak_demand_per_hour": None,  # caller supplies demand from substrate
    },
}


def run_with_ripple(primary_model_name: str, primary_inputs: dict, downstream_inputs: dict = None):
    """
    Run a primary model, then run all downstream models in its ripple graph.

    primary_model_name: one of the keys in MODEL_REGISTRY
    primary_inputs:     kwargs for the primary model
    downstream_inputs:  {model_name: {kwarg: value, ...}} — overrides defaults

    Returns a list of dicts:
      [{"model": name, "role": "primary"|"ripple", "result": {...}}, ...]
    """
    if primary_model_name not in MODEL_REGISTRY:
        raise ValueError(
            f"Unknown model: {primary_model_name}. "
            f"Available: {list(MODEL_REGISTRY.keys())}"
        )

    if downstream_inputs is None:
        downstream_inputs = {}

    results = []

    primary_fn     = MODEL_REGISTRY[primary_model_name]
    primary_result = primary_fn(**primary_inputs)
    results.append({
        "model":  primary_model_name,
        "role":   "primary",
        "result": primary_result,
    })

    downstream = RIPPLE_GRAPH.get(primary_model_name, [])
    visited    = {primary_model_name}

    for downstream_name in downstream:
        if downstream_name in visited:
            continue
        if downstream_name not in MODEL_REGISTRY:
            continue
        visited.add(downstream_name)

        caller_inputs = downstream_inputs.get(downstream_name, {})
        downstream_fn = MODEL_REGISTRY[downstream_name]

        try:
            downstream_result = downstream_fn(**caller_inputs)
            results.append({
                "model":  downstream_name,
                "role":   "ripple",
                "result": downstream_result,
            })
        except Exception as e:
            results.append({
                "model":  downstream_name,
                "role":   "ripple",
                "result": {"error": str(e), "note": "Downstream model failed — supply inputs via downstream_inputs"},
            })

    return results


def format_ripple_output(ripple_results: list) -> str:
    """Format ripple results as a markdown string for display."""
    lines = []
    for entry in ripple_results:
        role  = entry["role"]
        name  = entry["model"]
        result = entry["result"]

        if role == "primary":
            lines.append(f"\n## PRIMARY MODEL: {name}\n")
        else:
            lines.append(f"\n### RIPPLE → {name}\n")

        if "error" in result:
            lines.append(f"*Error: {result['error']}*\n")
            continue

        params  = result.get("parameters", {})
        outputs = result.get("outputs",    {})

        lines.append("**Parameters:**")
        for k, v in params.items():
            lines.append(f"- `{k}`: {v}")

        lines.append("\n**Outputs:**")
        for k, v in outputs.items():
            if isinstance(v, dict):
                lines.append(f"- `{k}`:")
                for kk, vv in v.items():
                    lines.append(f"  - `{kk}`: {vv}")
            elif isinstance(v, list) and len(v) > 10:
                lines.append(f"- `{k}`: [{v[0]}, {v[1]}, ... ({len(v)} items)]")
            else:
                lines.append(f"- `{k}`: {v}")

    return "\n".join(lines)
