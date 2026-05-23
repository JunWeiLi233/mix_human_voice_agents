from typing import Any


QWEN_RUNTIME_CONFIG_KEYS = ("model_id", "device_map", "dtype", "attn_implementation")


def resolved_qwen_runtime_config(
    adapter: Any,
    requested_config: dict[str, str | None],
) -> dict[str, str | None]:
    adapter_config = getattr(adapter, "runtime_config", None) or {}
    return {
        key: adapter_config.get(key, requested_config.get(key))
        for key in QWEN_RUNTIME_CONFIG_KEYS
    }
