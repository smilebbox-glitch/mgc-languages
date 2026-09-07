from pathlib import Path
from urllib.parse import urlparse
import ipaddress

import httpx

from app.core.config import get_settings
from app.core.resilience import record_failure, record_success, resilience_snapshot



def validate_inference_url(base_url: str) -> str:
    cfg = get_settings()
    if not cfg.air_gapped_mode:
        return base_url
    parsed = urlparse(base_url)
    host = (parsed.hostname or "").lower()
    if parsed.scheme not in {"http", "https"} or not host:
        raise RuntimeError(f"Invalid local inference URL: {base_url!r}")
    allowed = cfg.local_inference_allowed_host_set
    if host in allowed:
        return base_url
    try:
        if ipaddress.ip_address(host).is_private:
            return base_url
    except ValueError:
        pass
    raise RuntimeError(
        f"AIR_GAPPED_MODE blocks inference host {host!r}. "
        "Add an approved internal hostname to LOCAL_INFERENCE_ALLOWED_HOSTS if required."
    )


def _dir_state(value: str) -> dict:
    path = Path(value)
    exists = path.is_absolute() and path.exists() and path.is_dir()
    files = 0
    if exists:
        try:
            files = sum(1 for x in path.rglob("*") if x.is_file())
        except OSError:
            files = 0
    return {"path": str(path), "exists": exists, "files": files}


async def _server_state(base_url: str, expected_model: str, api_key: str) -> dict:
    if not base_url:
        return {"configured": False, "reachable": False, "expected_model": expected_model}
    headers = {"Authorization": f"Bearer {api_key}"}
    try:
        base_url = validate_inference_url(base_url)
        async with httpx.AsyncClient(timeout=8) as client:
            response = await client.get(base_url.rstrip("/") + "/models", headers=headers)
            response.raise_for_status()
            data = response.json()
        model_ids = [str(x.get("id")) for x in data.get("data", []) if isinstance(x, dict)]
        record_success("local_ai")
        return {
            "configured": True, "reachable": True, "base_url": base_url,
            "expected_model": expected_model, "models": model_ids,
            "expected_model_present": (not expected_model) or expected_model in model_ids,
        }
    except Exception as exc:
        record_failure("local_ai", exc)
        return {
            "configured": True, "reachable": False, "base_url": base_url,
            "expected_model": expected_model, "error": type(exc).__name__,
        }


async def local_ai_status() -> dict:
    cfg = get_settings()
    runtime_features = getattr(cfg, "runtime_features", {"local_llm", "local_vlm", "embeddings", "reranker"})
    if "local_llm" not in runtime_features:
        return {
            "inference_runtime": cfg.inference_runtime,
            "air_gapped_mode": cfg.air_gapped_mode,
            "runtime_downloads_allowed": not cfg.air_gapped_mode,
            "ready": False,
            "disabled_by_profile": True,
            "profile": getattr(cfg, "runtime_profile", "legacy"),
            "llm": {"configured": False, "reachable": False, "disabled": True},
            "vlm": {"configured": False, "reachable": False, "disabled": True},
            "embeddings": {"enabled": False, "disabled": True},
            "reranker": {"enabled": False, "disabled": True},
        }
    llm = await _server_state(cfg.llm_base_url, cfg.llm_model, cfg.llm_api_key)
    if cfg.vlm_base_url == cfg.llm_base_url and cfg.vlm_model == cfg.llm_model:
        vlm = dict(llm)
        vlm["shared_with_llm"] = True
    else:
        vlm = await _server_state(cfg.vlm_base_url, cfg.vlm_model, cfg.vlm_api_key)
    embeddings = _dir_state(cfg.embedding_model)
    reranker = _dir_state(cfg.reranker_model) if cfg.reranker_enabled else {"enabled": False}
    ready = bool(llm.get("reachable") and llm.get("expected_model_present", True) and embeddings.get("exists"))
    if cfg.vlm_model:
        ready = ready and bool(vlm.get("reachable") and vlm.get("expected_model_present", True))
    if cfg.reranker_enabled:
        ready = ready and bool(reranker.get("exists"))
    return {
        "inference_runtime": cfg.inference_runtime,
        "air_gapped_mode": cfg.air_gapped_mode,
        "runtime_downloads_allowed": not cfg.air_gapped_mode,
        "ready": ready,
        "llm": llm,
        "vlm": vlm,
        "embeddings": embeddings,
        "reranker": reranker,
        "resilience": resilience_snapshot(),
    }
