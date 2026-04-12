# ─── judges/models.py ────────────────────────────────────────────────────────
# 4 judge implementations dùng OpenAI-compatible API

from openai import OpenAI, RateLimitError, APIStatusError, APITimeoutError
from judges.base import BaseJudge, QuotaExceededException, TransientException
from config import API_KEYS, MODEL_CONFIG


def _make_client(judge_name: str) -> OpenAI:
    cfg = MODEL_CONFIG[judge_name]
    return OpenAI(
        api_key=API_KEYS[judge_name],
        base_url=cfg["base_url"],
    )


def _call_openai_compatible(client: OpenAI, model: str, prompt: str) -> str:
    """Gọi OpenAI-compatible endpoint, map lỗi sang exception chuẩn."""
    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=2048,
            temperature=0.1,    # thấp để output ổn định
        )
        return resp.choices[0].message.content or ""
    except RateLimitError as e:
        msg = str(e).lower()
        # Phân biệt quota hết hẳn vs rate limit tạm thời
        if any(kw in msg for kw in ("quota", "exceeded", "billing", "insufficient_quota",
                                     "daily limit", "monthly limit", "free tier")):
            raise QuotaExceededException(f"{msg}") from e
        raise TransientException(f"rate_limit_transient: {msg}") from e
    except APITimeoutError as e:
        raise TransientException(f"timeout: {e}") from e
    except APIStatusError as e:
        if e.status_code in (500, 502, 503, 504):
            raise TransientException(f"server_error_{e.status_code}") from e
        raise


# ── 4 Judge classes ───────────────────────────────────────────────────────────

class GeminiJudge(BaseJudge):
    name = "gemini"
    def __init__(self):
        self._client = _make_client("gemini")
        self._model  = MODEL_CONFIG["gemini"]["model"]

    def _call_api(self, prompt: str) -> str:
        return _call_openai_compatible(self._client, self._model, prompt)


class GrokJudge(BaseJudge):
    name = "grok"
    def __init__(self):
        self._client = _make_client("grok")
        self._model  = MODEL_CONFIG["grok"]["model"]

    def _call_api(self, prompt: str) -> str:
        return _call_openai_compatible(self._client, self._model, prompt)


class QwenJudge(BaseJudge):
    name = "qwen"
    def __init__(self):
        self._client = _make_client("qwen")
        self._model  = MODEL_CONFIG["qwen"]["model"]

    def _call_api(self, prompt: str) -> str:
        return _call_openai_compatible(self._client, self._model, prompt)


class DeepSeekJudge(BaseJudge):
    name = "deepseek"
    def __init__(self):
        self._client = _make_client("deepseek")
        self._model  = MODEL_CONFIG["deepseek"]["model"]

    def _call_api(self, prompt: str) -> str:
        return _call_openai_compatible(self._client, self._model, prompt)


# ── Factory ───────────────────────────────────────────────────────────────────
def get_all_judges() -> list[BaseJudge]:
    return [GeminiJudge(), GrokJudge(), QwenJudge(), DeepSeekJudge()]
