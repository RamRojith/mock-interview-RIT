import json

import requests
from django.conf import settings


class LocalModelError(RuntimeError):
    pass


def configured_model(purpose="interactive"):
    if purpose == "report":
        return settings.MOCK_INTERVIEW.get(
            "OLLAMA_REPORT_MODEL",
            settings.MOCK_INTERVIEW.get("OLLAMA_MODEL", "qwen3:8b"),
        )
    return settings.MOCK_INTERVIEW.get(
        "OLLAMA_INTERACTIVE_MODEL",
        settings.MOCK_INTERVIEW.get("OLLAMA_MODEL", "qwen3:4b"),
    )


def _api_url():
    base_url = settings.MOCK_INTERVIEW.get(
        "OLLAMA_BASE_URL", "http://127.0.0.1:11434"
    ).rstrip("/")
    if base_url.endswith("/v1"):
        return f"{base_url}/chat/completions", "openai"
    return f"{base_url}/api/chat", "ollama"


def chat_json(
    messages,
    schema,
    *,
    temperature=0.2,
    timeout=None,
    model=None,
    context_tokens=None,
    max_output_tokens=None,
):
    url, api_style = _api_url()
    model = model or configured_model()
    timeout = timeout or float(settings.MOCK_INTERVIEW.get("OLLAMA_TIMEOUT", 120))

    if api_style == "ollama":
        payload = {
            "model": model,
            "messages": messages,
            "stream": False,
            "keep_alive": "30m",
            "think": bool(
                settings.MOCK_INTERVIEW.get("OLLAMA_THINK", False)
            ),
            "format": schema,
            "options": {
                "temperature": temperature,
                "num_ctx": int(
                    context_tokens
                    or settings.MOCK_INTERVIEW.get(
                        "OLLAMA_CONTEXT_TOKENS", 4096
                    )
                ),
                "num_predict": int(
                    max_output_tokens
                    or settings.MOCK_INTERVIEW.get(
                        "OLLAMA_MAX_OUTPUT_TOKENS", 1024
                    )
                ),
            },
        }
    else:
        payload = {
            "model": model,
            "messages": messages,
            "stream": False,
            "temperature": temperature,
            "response_format": {"type": "json_object"},
        }

    try:
        response = requests.post(url, json=payload, timeout=timeout)
        response.raise_for_status()
        body = response.json()
        if api_style == "ollama":
            content = body["message"]["content"]
        else:
            content = body["choices"][0]["message"]["content"]
        parsed = json.loads(content) if isinstance(content, str) else content
    except (requests.RequestException, KeyError, TypeError, json.JSONDecodeError) as exc:
        raise LocalModelError(f"Local model request failed: {exc}") from exc

    if not isinstance(parsed, dict):
        raise LocalModelError("Local model did not return a JSON object.")
    return parsed


def health():
    url, api_style = _api_url()
    if api_style == "ollama":
        health_url = url.replace("/api/chat", "/api/tags")
    else:
        health_url = url.replace("/chat/completions", "/models")
    try:
        response = requests.get(health_url, timeout=3)
        return response.ok
    except requests.RequestException:
        return False


def model_available(model=None):
    """Check that the configured model is advertised by the local server."""
    url, api_style = _api_url()
    model = model or configured_model()
    models_url = (
        url.replace("/api/chat", "/api/tags")
        if api_style == "ollama"
        else url.replace("/chat/completions", "/models")
    )
    try:
        response = requests.get(models_url, timeout=3)
        response.raise_for_status()
        body = response.json()
        if api_style == "ollama":
            names = {
                item.get("name")
                for item in body.get("models", [])
                if isinstance(item, dict)
            }
        else:
            names = {
                item.get("id")
                for item in body.get("data", [])
                if isinstance(item, dict)
            }
        return model in names or f"{model}:latest" in names
    except (requests.RequestException, TypeError, ValueError):
        return False
