"""Local LLM API backends and llama-server lifecycle control.

The experiment layer uses this module through one provider-neutral interface.
Two local OpenAI-compatible backends are supported:

* ``llama_server_sycl``: ``llama-server`` is launched and managed here;
* ``lm_studio``: LM Studio is expected to already be running its
  OpenAI-compatible server and this module only connects to it.

The experiment configuration has one source of truth: the shared ``DEFAULT_*``
constants below. The settings that both backends can actually control are shared.
llama-server translates them into command-line options; LM Studio applies the
supported model-load settings through its native ``/api/v1/models/load`` API and
verifies the resulting loaded-instance configuration before inference starts.
Backend-specific settings remain backend-specific rather than being presented as
portable settings that the other backend cannot enforce.
"""

from __future__ import annotations

import json
import shlex
import subprocess
import time
import urllib.error
import urllib.request
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Final, Literal

from openai import APIError, OpenAI


# ---------------------------------------------------------------------------
# Shared experiment / inference configuration
# ---------------------------------------------------------------------------

LLAMA_SERVER_SYCL: Final[str] = "llama_server_sycl"
LM_STUDIO: Final[str] = "lm_studio"
LLM_API_BACKENDS: Final[tuple[str, ...]] = (LLAMA_SERVER_SYCL, LM_STUDIO)
APIBackend = Literal["llama_server_sycl", "lm_studio"]

DEFAULT_API_BACKEND: Final[APIBackend] = LLAMA_SERVER_SYCL

DEFAULT_MODEL_ID: Final[str] = "gemma-4-e2b-it-qat"
DEFAULT_TEMPERATURE: Final[float] = 0.0
DEFAULT_TOP_P: Final[float] = 1.0
DEFAULT_TOP_K: Final[int | None] = 1
DEFAULT_MAX_TOKENS: Final[int] = 8192
DEFAULT_TIMEOUT_SECONDS: Final[float] = 600.0
DEFAULT_CONCURRENT_PREDICTIONS: Final[int] = 1

# Shared model-load/runtime settings. These are deliberately limited to values
# that both supported backends expose programmatically.
DEFAULT_CONTEXT_SIZE: Final[int] = 32768
DEFAULT_BATCH_SIZE: Final[int] = 2048
DEFAULT_PARALLEL: Final[int] = DEFAULT_CONCURRENT_PREDICTIONS
DEFAULT_KV_OFFLOAD: Final[bool] = True
DEFAULT_FLASH_ATTENTION: Final[bool] = True

# Shared reasoning switch. Each backend translates this boolean to its native
# mechanism so the experiment has one unambiguous reasoning configuration.
DEFAULT_REASONING: Final[bool] = False


# ---------------------------------------------------------------------------
# Backend-specific connection / process settings
# ---------------------------------------------------------------------------

LLAMA_SERVER_BASE_URL: Final[str] = "http://127.0.0.1:1234/v1"
LLAMA_SERVER_API_KEY: Final[str] = "llama-server"
LLAMA_SERVER_MODEL_ID: Final[str] = DEFAULT_MODEL_ID
DEFAULT_LLAMA_SERVER_BASE_URL: Final[str] = LLAMA_SERVER_BASE_URL
DEFAULT_LLAMA_SERVER_API_KEY: Final[str] = LLAMA_SERVER_API_KEY

LM_STUDIO_BASE_URL: Final[str] = "http://127.0.0.1:1234/v1"
LM_STUDIO_API_KEY: Final[str] = "lm-studio"
LM_STUDIO_MODEL_ID: Final[str] = DEFAULT_MODEL_ID
LM_STUDIO_NATIVE_API_BASE_URL: Final[str] = "http://127.0.0.1:1234/api/v1"
# Leave empty when LM Studio authentication is disabled. When authentication is
# enabled, set this to the LM Studio API token.
LM_STUDIO_API_TOKEN: Final[str] = ""
LM_STUDIO_LOAD_TIMEOUT_SECONDS: Final[float] = 600.0
LM_STUDIO_UNLOAD_TIMEOUT_SECONDS: Final[float] = 60.0

# llama-server-only runtime controls. LM Studio does not expose these exact
# llama.cpp settings through its documented native REST load API.
LLAMA_SERVER_UBATCH_SIZE: Final[int] = 2048
LLAMA_SERVER_THREADS: Final[int] = 12
LLAMA_SERVER_THREADS_BATCH: Final[int] = 12
LLAMA_SERVER_GPU_LAYERS: Final[int] = 99
LLAMA_SERVER_CACHE_TYPE_K: Final[str] = "f16"
LLAMA_SERVER_CACHE_TYPE_V: Final[str] = "f16"
LLAMA_SERVER_KV_UNIFIED: Final[bool] = True
LLAMA_SERVER_FIT: Final[str] = "off"
LLAMA_SERVER_JINJA: Final[bool] = True

LLAMA_SERVER_BINARY: Final[Path] = (
    Path.home() / "llama.cpp" / "build" / "bin" / "llama-server"
)
LLAMA_SERVER_MODEL_PATH: Final[Path] = (
    Path.home()
    / ".lmstudio"
    / "models"
    / "lmstudio-community"
    / "gemma-4-E2B-it-qat-q4_0-gguf"
    / "gemma-4-E2B_q4_0-it.gguf"
)
LLAMA_SERVER_WORKING_DIRECTORY: Final[Path] = Path.home() / "llama.cpp"
LLAMA_SERVER_ONEAPI_SET_VARS: Final[Path] = Path("/opt/intel/oneapi/setvars.sh")
LLAMA_SERVER_DEVICE_SELECTOR: Final[str] = "level_zero:gpu"
LLAMA_SERVER_HOST: Final[str] = "127.0.0.1"
LLAMA_SERVER_PORT: Final[int] = 1234
LLAMA_SERVER_STARTUP_TIMEOUT_SECONDS: Final[float] = 180.0
LLAMA_SERVER_TERMINATION_TIMEOUT_SECONDS: Final[float] = 15.0
LLAMA_SERVER_LOG_FILE_NAME: Final[str] = "llama_server.log"


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True, kw_only=True)
class APIConfiguration:
    """Resolved connection settings for an API backend."""

    backend: APIBackend
    base_url: str
    api_key: str
    model: str


@dataclass(frozen=True, slots=True, kw_only=True)
class CompletionResult:
    """Normalized result of one Chat Completion request."""

    raw_response: str | None
    response_error: str | None
    prompt_tokens: int | None
    completion_tokens: int | None
    total_tokens: int | None
    finish_reason: str | None
    request_time_seconds: float


def api_configuration(backend: APIBackend) -> APIConfiguration:
    """Return the fixed connection configuration for ``backend``."""
    if backend == LLAMA_SERVER_SYCL:
        return APIConfiguration(
            backend=backend,
            base_url=LLAMA_SERVER_BASE_URL,
            api_key=LLAMA_SERVER_API_KEY,
            model=DEFAULT_MODEL_ID,
        )
    if backend == LM_STUDIO:
        return APIConfiguration(
            backend=backend,
            base_url=LM_STUDIO_BASE_URL,
            api_key=LM_STUDIO_API_KEY,
            model=DEFAULT_MODEL_ID,
        )
    raise ValueError(
        f"Unknown LLM API backend: {backend!r}. Expected one of {LLM_API_BACKENDS!r}."
    )


def shared_inference_configuration() -> dict[str, object]:
    """Return the shared experiment configuration honored by both backends."""
    return {
        "model": DEFAULT_MODEL_ID,
        "temperature": DEFAULT_TEMPERATURE,
        "top_p": DEFAULT_TOP_P,
        "top_k": DEFAULT_TOP_K,
        "max_tokens": DEFAULT_MAX_TOKENS,
        "timeout_seconds": DEFAULT_TIMEOUT_SECONDS,
        "concurrent_predictions": DEFAULT_CONCURRENT_PREDICTIONS,
        "context_size": DEFAULT_CONTEXT_SIZE,
        "batch_size": DEFAULT_BATCH_SIZE,
        "parallel": DEFAULT_PARALLEL,
        "kv_offload": DEFAULT_KV_OFFLOAD,
        "flash_attention": DEFAULT_FLASH_ATTENTION,
        "reasoning": DEFAULT_REASONING,
    }


def _llama_server_arguments(model_alias: str) -> tuple[str, ...]:
    """Build the llama-server command from shared experiment constants."""
    arguments = [
        "--model",
        str(LLAMA_SERVER_MODEL_PATH),
        "--alias",
        model_alias,
        "--ctx-size",
        str(DEFAULT_CONTEXT_SIZE),
        "--batch-size",
        str(DEFAULT_BATCH_SIZE),
        "--ubatch-size",
        str(LLAMA_SERVER_UBATCH_SIZE),
        "--parallel",
        str(DEFAULT_PARALLEL),
        "--threads",
        str(LLAMA_SERVER_THREADS),
        "--threads-batch",
        str(LLAMA_SERVER_THREADS_BATCH),
        "--n-gpu-layers",
        str(LLAMA_SERVER_GPU_LAYERS),
        "--kv-offload" if DEFAULT_KV_OFFLOAD else "--no-kv-offload",
        "--cache-type-k",
        LLAMA_SERVER_CACHE_TYPE_K,
        "--cache-type-v",
        LLAMA_SERVER_CACHE_TYPE_V,
        "--kv-unified" if LLAMA_SERVER_KV_UNIFIED else "--no-kv-unified",
        "--fit",
        LLAMA_SERVER_FIT,
        "--flash-attn",
        "on" if DEFAULT_FLASH_ATTENTION else "off",
        "--reasoning",
        "on" if DEFAULT_REASONING else "off",
        "--host",
        LLAMA_SERVER_HOST,
        "--port",
        str(LLAMA_SERVER_PORT),
    ]
    if LLAMA_SERVER_JINJA:
        arguments.append("--jinja")
    return tuple(arguments)


def llama_server_configuration(model_alias: str) -> dict[str, object]:
    """Return shared plus llama-server-specific configuration for metadata."""
    return {
        "inference": shared_inference_configuration(),
        "runtime": {
            "ubatch_size": LLAMA_SERVER_UBATCH_SIZE,
            "threads": LLAMA_SERVER_THREADS,
            "threads_batch": LLAMA_SERVER_THREADS_BATCH,
            "gpu_layers": LLAMA_SERVER_GPU_LAYERS,
            "cache_type_k": LLAMA_SERVER_CACHE_TYPE_K,
            "cache_type_v": LLAMA_SERVER_CACHE_TYPE_V,
            "kv_unified": LLAMA_SERVER_KV_UNIFIED,
            "fit": LLAMA_SERVER_FIT,
            "jinja": LLAMA_SERVER_JINJA,
        },
        "binary": str(LLAMA_SERVER_BINARY),
        "model_path": str(LLAMA_SERVER_MODEL_PATH),
        "model_alias": model_alias,
        "working_directory": str(LLAMA_SERVER_WORKING_DIRECTORY),
        "oneapi_setvars": str(LLAMA_SERVER_ONEAPI_SET_VARS),
        "device_selector": LLAMA_SERVER_DEVICE_SELECTOR,
        "host": LLAMA_SERVER_HOST,
        "port": LLAMA_SERVER_PORT,
    }


def lm_studio_configuration(model_id: str) -> dict[str, object]:
    """Return shared plus LM Studio native API configuration for metadata."""
    return {
        "inference": shared_inference_configuration(),
        "native_api_base_url": LM_STUDIO_NATIVE_API_BASE_URL,
        "load_endpoint": "/models/load",
        "unload_endpoint": "/models/unload",
        "model": model_id,
        "server_lifecycle": "external",
        "model_instance_lifecycle": "managed by this experiment",
    }


def api_backend_configuration(
    backend: APIBackend,
    *,
    model: str,
) -> dict[str, object]:
    """Return backend-specific configuration suitable for experiment metadata."""
    if backend == LLAMA_SERVER_SYCL:
        return llama_server_configuration(model)
    if backend == LM_STUDIO:
        return lm_studio_configuration(model)
    raise ValueError(f"Unknown LLM API backend: {backend!r}.")


def llama_server_command(model_alias: str) -> str:
    """Return the shell command used to launch llama-server."""
    arguments = shlex.join(_llama_server_arguments(model_alias))
    return (
        f"source {shlex.quote(str(LLAMA_SERVER_ONEAPI_SET_VARS))} --force "
        ">/dev/null 2>&1 && "
        f"export ONEAPI_DEVICE_SELECTOR={shlex.quote(LLAMA_SERVER_DEVICE_SELECTOR)} "
        "&& "
        f"cd {shlex.quote(str(LLAMA_SERVER_WORKING_DIRECTORY))} && "
        f"exec {shlex.quote(str(LLAMA_SERVER_BINARY))} {arguments}"
    )


def _read_server_log_tail(path: Path, *, line_count: int = 40) -> str:
    """Read the final server log lines for startup diagnostics."""
    if not path.is_file():
        return "<llama-server log is unavailable>"
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    return "\n".join(lines[-line_count:])


def _start_llama_server(
    *,
    model_alias: str,
    log_path: Path,
) -> tuple[subprocess.Popen[bytes], object]:
    """Start llama-server with the fixed local SYCL configuration."""
    for required_path, description in (
        (LLAMA_SERVER_BINARY, "llama-server binary"),
        (LLAMA_SERVER_MODEL_PATH, "GGUF model"),
        (LLAMA_SERVER_ONEAPI_SET_VARS, "oneAPI environment script"),
    ):
        if not required_path.is_file():
            raise FileNotFoundError(f"{description} does not exist: '{required_path}'.")

    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_handle = log_path.open("w", encoding="utf-8")
    process = subprocess.Popen(
        ["bash", "-lc", llama_server_command(model_alias)],
        cwd=LLAMA_SERVER_WORKING_DIRECTORY,
        stdout=log_handle,
        stderr=subprocess.STDOUT,
    )
    return process, log_handle


def _wait_for_llama_server(
    process: subprocess.Popen[bytes],
    *,
    base_url: str,
    log_path: Path,
) -> None:
    """Wait until llama-server exposes its OpenAI-compatible models endpoint."""
    endpoint = f"{base_url.rstrip('/')}/models"
    deadline = time.monotonic() + LLAMA_SERVER_STARTUP_TIMEOUT_SECONDS
    while time.monotonic() < deadline:
        return_code = process.poll()
        if return_code is not None:
            raise RuntimeError(
                "llama-server exited during startup with return code "
                f"{return_code}.\n\nServer log tail:\n"
                f"{_read_server_log_tail(log_path)}"
            )
        try:
            with urllib.request.urlopen(endpoint, timeout=2.0):
                return
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError):
            time.sleep(1.0)

    raise TimeoutError(
        "llama-server did not become ready within "
        f"{LLAMA_SERVER_STARTUP_TIMEOUT_SECONDS:.0f} seconds.\n\n"
        f"Server log tail:\n{_read_server_log_tail(log_path)}"
    )


def _stop_llama_server(process: subprocess.Popen[bytes]) -> None:
    """Stop a running llama-server gracefully, then forcefully if needed."""
    if process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=LLAMA_SERVER_TERMINATION_TIMEOUT_SECONDS)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait()


def _lm_studio_headers() -> dict[str, str]:
    """Return headers for LM Studio's native REST API."""
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
    }
    if LM_STUDIO_API_TOKEN:
        headers["Authorization"] = f"Bearer {LM_STUDIO_API_TOKEN}"
    return headers


def _lm_studio_request(
    *,
    method: str,
    endpoint: str,
    payload: dict[str, object] | None = None,
    timeout_seconds: float,
) -> dict[str, object]:
    """Call LM Studio's native v1 REST API and require a JSON object response."""
    url = f"{LM_STUDIO_NATIVE_API_BASE_URL.rstrip('/')}/{endpoint.lstrip('/')}"
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=body,
        headers=_lm_studio_headers(),
        method=method,
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            raw = response.read()
    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(
            f"LM Studio native API request failed with HTTP {error.code}: {detail}"
        ) from error
    except urllib.error.URLError as error:
        raise RuntimeError(
            "Could not reach LM Studio's native REST API at "
            f"{LM_STUDIO_NATIVE_API_BASE_URL!r}."
        ) from error

    try:
        decoded = json.loads(raw.decode("utf-8"))
    except json.JSONDecodeError as error:
        raise RuntimeError("LM Studio native API returned invalid JSON.") from error
    if not isinstance(decoded, dict):
        raise RuntimeError("LM Studio native API returned a non-object JSON response.")
    if "error" in decoded:
        raise RuntimeError(
            f"LM Studio native API returned an error: {decoded['error']!r}"
        )
    return decoded


def _lm_studio_model_inventory() -> tuple[dict[str, object], ...]:
    """Return LM Studio's current native model inventory."""
    response = _lm_studio_request(
        method="GET",
        endpoint="/models",
        timeout_seconds=DEFAULT_TIMEOUT_SECONDS,
    )
    models = response.get("models")
    if not isinstance(models, list):
        raise RuntimeError("LM Studio /api/v1/models returned no valid 'models' array.")
    return tuple(item for item in models if isinstance(item, dict))


def _lm_studio_loaded_instances(model: str) -> tuple[str, ...]:
    """Return loaded instance identifiers for the requested model key."""
    instance_ids: list[str] = []
    for model_info in _lm_studio_model_inventory():
        key = model_info.get("key")
        if key != model:
            continue
        loaded_instances = model_info.get("loaded_instances")
        if not isinstance(loaded_instances, list):
            continue
        for instance in loaded_instances:
            if isinstance(instance, dict):
                instance_id = instance.get("id")
                if isinstance(instance_id, str) and instance_id:
                    instance_ids.append(instance_id)
    return tuple(instance_ids)


def _unload_lm_studio_instance(instance_id: str) -> None:
    """Unload one LM Studio model instance."""
    _lm_studio_request(
        method="POST",
        endpoint="/models/unload",
        payload={"instance_id": instance_id},
        timeout_seconds=LM_STUDIO_UNLOAD_TIMEOUT_SECONDS,
    )


def _lm_studio_load_configuration() -> dict[str, object]:
    """Return the LM Studio native load configuration controlled by this module."""
    return {
        "context_length": DEFAULT_CONTEXT_SIZE,
        "eval_batch_size": DEFAULT_BATCH_SIZE,
        "parallel": DEFAULT_PARALLEL,
        "flash_attention": DEFAULT_FLASH_ATTENTION,
        "offload_kv_cache_to_gpu": DEFAULT_KV_OFFLOAD,
    }


def _load_lm_studio_model(model: str) -> str:
    """Load the exact LM Studio model configuration and verify what was applied."""
    # Explicitly remove pre-existing instances so an experiment cannot silently
    # inherit different load settings from a manually loaded model instance.
    for instance_id in _lm_studio_loaded_instances(model):
        _unload_lm_studio_instance(instance_id)

    payload = {
        "model": model,
        **_lm_studio_load_configuration(),
        "echo_load_config": True,
    }
    response = _lm_studio_request(
        method="POST",
        endpoint="/models/load",
        payload=payload,
        timeout_seconds=LM_STUDIO_LOAD_TIMEOUT_SECONDS,
    )
    instance_id = response.get("instance_id")
    if not isinstance(instance_id, str) or not instance_id:
        raise RuntimeError(
            "LM Studio model load succeeded without returning a valid instance_id."
        )

    # Verify the authoritative loaded-instance configuration rather than trusting
    # the request body or UI defaults.
    loaded_config = response.get("load_config")
    if isinstance(loaded_config, dict):
        returned_config = loaded_config
    else:
        returned_config = None
        for model_info in _lm_studio_model_inventory():
            if model_info.get("key") != model:
                continue
            loaded_instances = model_info.get("loaded_instances")
            if not isinstance(loaded_instances, list):
                continue
            for instance in loaded_instances:
                if isinstance(instance, dict) and instance.get("id") == instance_id:
                    candidate = instance.get("config")
                    if isinstance(candidate, dict):
                        returned_config = candidate
                    break

    if returned_config is None:
        raise RuntimeError(
            "LM Studio loaded the model but did not expose its applied load configuration."
        )

    expected = _lm_studio_load_configuration()
    mismatches = {
        key: {"expected": value, "actual": returned_config.get(key)}
        for key, value in expected.items()
        if returned_config.get(key) != value
    }
    if mismatches:
        _unload_lm_studio_instance(instance_id)
        raise RuntimeError(
            "LM Studio did not apply the required model-load configuration: "
            f"{mismatches!r}."
        )
    return instance_id


@contextmanager
def running_api(
    *,
    backend: APIBackend,
    model: str,
    base_url: str,
    log_path: Path | None = None,
) -> Iterator[None]:
    """Provide one inference backend for the duration of an experiment."""
    if backend == LLAMA_SERVER_SYCL:
        if log_path is None:
            raise ValueError(
                "A log path is required when using the llama-server backend."
            )
        process, log_handle = _start_llama_server(
            model_alias=model,
            log_path=log_path,
        )
        try:
            _wait_for_llama_server(
                process,
                base_url=base_url,
                log_path=log_path,
            )
            yield
        finally:
            _stop_llama_server(process)
            close = getattr(log_handle, "close", None)
            if close is not None:
                close()
        return

    if backend == LM_STUDIO:
        instance_id = _load_lm_studio_model(model)
        try:
            yield
        finally:
            _unload_lm_studio_instance(instance_id)
        return

    raise ValueError(f"Unknown LLM API backend: {backend!r}.")


@contextmanager
def running_llama_server(
    *,
    model_alias: str,
    base_url: str,
    log_path: Path,
) -> Iterator[None]:
    """Backward-compatible llama-server-specific lifecycle wrapper."""
    with running_api(
        backend=LLAMA_SERVER_SYCL,
        model=model_alias,
        base_url=base_url,
        log_path=log_path,
    ):
        yield


def create_api_client(
    *,
    base_url: str,
    api_key: str,
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
) -> OpenAI:
    """Create an OpenAI client for either supported local backend."""
    return OpenAI(
        base_url=base_url,
        api_key=api_key,
        timeout=timeout_seconds,
        max_retries=0,
    )


def create_llama_server_client(
    *,
    base_url: str = LLAMA_SERVER_BASE_URL,
    api_key: str = LLAMA_SERVER_API_KEY,
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
) -> OpenAI:
    """Backward-compatible llama-server client factory."""
    return create_api_client(
        base_url=base_url,
        api_key=api_key,
        timeout_seconds=timeout_seconds,
    )


def validate_api_model(client: OpenAI, *, model: str, backend: APIBackend) -> None:
    """Verify that the selected local API advertises the requested model."""
    try:
        available_models = client.models.list()
    except APIError as error:
        service_name = "llama-server" if backend == LLAMA_SERVER_SYCL else "LM Studio"
        raise RuntimeError(
            f"Could not query {service_name}'s OpenAI-compatible /v1/models "
            "endpoint. Ensure the selected local server is running and reachable."
        ) from error

    available_ids = {str(item.id) for item in available_models.data}
    if model not in available_ids:
        service_name = "llama-server" if backend == LLAMA_SERVER_SYCL else "LM Studio"
        raise RuntimeError(
            f"Model identifier {model!r} was not advertised by {service_name}. "
            f"Available model identifiers: {tuple(sorted(available_ids))!r}."
        )


def validate_llama_server_model(client: OpenAI, *, model: str) -> None:
    """Backward-compatible llama-server model validation wrapper."""
    validate_api_model(client, model=model, backend=LLAMA_SERVER_SYCL)


def request_completion(
    client: OpenAI,
    *,
    backend: APIBackend,
    model: str,
    temperature: float,
    top_p: float,
    top_k: int | None,
    max_tokens: int,
    system_prompt: str,
    user_prompt: str,
    seed: int,
) -> CompletionResult:
    """Execute one Chat Completion request for either backend."""
    start_time = time.perf_counter()
    try:
        extra_body: dict[str, object] = {"top_k": top_k}
        if backend == LM_STUDIO:
            # LM Studio's OpenAI-compatible endpoint exposes OpenAI-style
            # reasoning_effort values. For this experiment, disabled reasoning
            # is represented by the endpoint's explicit "none" value.
            # The shared boolean therefore remains backend-neutral while the
            # transport-specific representation stays here.
            extra_body["reasoning_effort"] = "high" if DEFAULT_REASONING else "none"

        completion = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=temperature,
            top_p=top_p,
            max_tokens=max_tokens,
            seed=seed,
            stream=False,
            extra_body=extra_body,
        )
    except APIError as error:
        raise RuntimeError(
            "The selected local LLM API returned an API error."
        ) from error

    elapsed = float(time.perf_counter() - start_time)
    if not completion.choices:
        return CompletionResult(
            raw_response=None,
            response_error="empty_choices",
            prompt_tokens=None,
            completion_tokens=None,
            total_tokens=None,
            finish_reason=None,
            request_time_seconds=elapsed,
        )

    choice = completion.choices[0]
    content = choice.message.content
    usage = completion.usage
    return CompletionResult(
        raw_response=content if isinstance(content, str) else None,
        response_error=("empty_response" if content is None else None),
        prompt_tokens=(
            int(usage.prompt_tokens)
            if usage is not None and usage.prompt_tokens is not None
            else None
        ),
        completion_tokens=(
            int(usage.completion_tokens)
            if usage is not None and usage.completion_tokens is not None
            else None
        ),
        total_tokens=(
            int(usage.total_tokens)
            if usage is not None and usage.total_tokens is not None
            else None
        ),
        finish_reason=(
            str(choice.finish_reason) if choice.finish_reason is not None else None
        ),
        request_time_seconds=elapsed,
    )


__all__ = [
    "APIBackend",
    "APIConfiguration",
    "CompletionResult",
    "DEFAULT_API_BACKEND",
    "DEFAULT_BATCH_SIZE",
    "DEFAULT_CONCURRENT_PREDICTIONS",
    "DEFAULT_CONTEXT_SIZE",
    "DEFAULT_FLASH_ATTENTION",
    "DEFAULT_KV_OFFLOAD",
    "DEFAULT_MAX_TOKENS",
    "DEFAULT_MODEL_ID",
    "DEFAULT_PARALLEL",
    "DEFAULT_REASONING",
    "DEFAULT_TEMPERATURE",
    "DEFAULT_TIMEOUT_SECONDS",
    "DEFAULT_TOP_K",
    "DEFAULT_TOP_P",
    "DEFAULT_LLAMA_SERVER_BASE_URL",
    "DEFAULT_LLAMA_SERVER_API_KEY",
    "LLAMA_SERVER_API_KEY",
    "LLAMA_SERVER_BASE_URL",
    "LLAMA_SERVER_BINARY",
    "LLAMA_SERVER_DEVICE_SELECTOR",
    "LLAMA_SERVER_HOST",
    "LLAMA_SERVER_LOG_FILE_NAME",
    "LLAMA_SERVER_MODEL_ID",
    "LLAMA_SERVER_MODEL_PATH",
    "LLAMA_SERVER_ONEAPI_SET_VARS",
    "LLAMA_SERVER_PORT",
    "LLAMA_SERVER_STARTUP_TIMEOUT_SECONDS",
    "LLAMA_SERVER_TERMINATION_TIMEOUT_SECONDS",
    "LLAMA_SERVER_UBATCH_SIZE",
    "LLAMA_SERVER_THREADS",
    "LLAMA_SERVER_THREADS_BATCH",
    "LLAMA_SERVER_GPU_LAYERS",
    "LLAMA_SERVER_CACHE_TYPE_K",
    "LLAMA_SERVER_CACHE_TYPE_V",
    "LLAMA_SERVER_KV_UNIFIED",
    "LLAMA_SERVER_FIT",
    "LLAMA_SERVER_JINJA",
    "LLAMA_SERVER_SYCL",
    "LLAMA_SERVER_WORKING_DIRECTORY",
    "LLM_API_BACKENDS",
    "LM_STUDIO",
    "LM_STUDIO_API_KEY",
    "LM_STUDIO_BASE_URL",
    "LM_STUDIO_NATIVE_API_BASE_URL",
    "LM_STUDIO_API_TOKEN",
    "LM_STUDIO_LOAD_TIMEOUT_SECONDS",
    "LM_STUDIO_UNLOAD_TIMEOUT_SECONDS",
    "LM_STUDIO_MODEL_ID",
    "api_backend_configuration",
    "api_configuration",
    "create_api_client",
    "create_llama_server_client",
    "llama_server_command",
    "llama_server_configuration",
    "lm_studio_configuration",
    "request_completion",
    "running_api",
    "running_llama_server",
    "shared_inference_configuration",
    "validate_api_model",
    "validate_llama_server_model",
]
