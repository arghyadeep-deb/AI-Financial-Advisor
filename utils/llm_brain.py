import os
import random
from typing import Generator
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage, HumanMessage
from backend.core.telemetry import traceable

load_dotenv()

# ─── Tracing ─────────────────────────────────────────────────────────────────
# Raw prompt/response tracing is never enabled here. backend.core.telemetry
# forces payload-hiding flags and exports metadata only when explicitly
# opted in (TELEMETRY_EXPORT_ENABLED=true plus an API key).
import time
import backend.core.telemetry  # noqa: F401  (configures environment on import)
from backend.core.config import config as _cfg

LANGSMITH_ENABLED = backend.core.telemetry.export_enabled()


class ProviderUnavailable(Exception):
    """All configured providers failed (or none are configured)."""


class StreamInterrupted(Exception):
    """A stream failed after some text was already delivered."""


# ─── Load API Keys ────────────────────────────────────────────────────────────

GROQ_KEYS = [k for k in [
    os.getenv("GROQ_API_KEY_1"),
    os.getenv("GROQ_API_KEY_2"),
    os.getenv("GROQ_API_KEY_3"),
    os.getenv("GROQ_API_KEY_4"),
] if k]

GOOGLE_KEYS = [k for k in [
    os.getenv("GOOGLE_API_KEY_1"),
    os.getenv("GOOGLE_API_KEY_2"),
    os.getenv("GOOGLE_API_KEY_3"),
    os.getenv("GOOGLE_API_KEY_4"),
] if k]

GROQ_MODELS = [
    "llama-3.3-70b-versatile",
    "llama-3.1-8b-instant",
]

DISABLED_GROQ_MODELS = set()


def _is_rate_limit_error(err: str) -> bool:
    return "rate" in err or "limit" in err or "quota" in err


def _is_invalid_key_error(err: str) -> bool:
    return "auth" in err or "key" in err or "invalid" in err


def _is_unavailable_model_error(err: str) -> bool:
    markers = [
        "decommissioned",
        "model_not_found",
        "does not exist",
        "unsupported",
        "not found",
    ]
    return any(marker in err for marker in markers)

if not GROQ_KEYS:
    print("[LLM] ⚠️  No Groq keys found in .env")
if not GOOGLE_KEYS:
    print("[LLM] ⚠️  No Google keys found in .env")


# ─── Groq Call ────────────────────────────────────────────────────────────────

@traceable(
    run_type = "llm",
    name     = "groq_call",
    tags     = ["groq", "primary_provider"]
)
def _call_groq(
    system_prompt: str,
    user_message:  str,
    max_tokens:    int,
    agent_name:    str = "unknown"
) -> str:
    """
    Call Groq API with key and model rotation.

    @traceable logs this as a CHILD trace under call_llm in LangSmith.
    Shows: model used, full prompt, response, latency, tokens.

    Rotates through:
    - 4 API keys (random order to distribute load)
    - 3 models (llama 70b → llama 3.1 → mixtral)
    """

    keys = GROQ_KEYS.copy()
    random.shuffle(keys)

    # Keep chat responsiveness high by limiting retries in conversational flow.
    if agent_name == "chat_agent":
        keys = keys[:2]

    deadline = time.monotonic() + _cfg.LLM_TIMEOUT_SECONDS * _cfg.LLM_MAX_ATTEMPTS
    attempts = 0
    for key in keys:
        for model in GROQ_MODELS:
            if model in DISABLED_GROQ_MODELS:
                continue
            if attempts >= _cfg.LLM_MAX_ATTEMPTS or time.monotonic() > deadline:
                raise ProviderUnavailable("Groq attempts exhausted")
            attempts += 1
            try:
                llm = ChatGroq(
                    api_key     = key,
                    model       = model,
                    max_tokens  = max_tokens,
                    temperature = 0.3,
                    timeout     = _cfg.LLM_TIMEOUT_SECONDS,
                    max_retries = 0,
                )
                messages = [
                    SystemMessage(content=system_prompt),
                    HumanMessage(content=user_message)
                ]
                response = llm.invoke(messages)
                print(f"[LLM] Groq/{model} ok -> {agent_name}")
                return response.content

            except Exception as e:
                err = str(e).lower()
                if _is_rate_limit_error(err):
                    print(f"[LLM] Groq rate limit on {model} — trying next...")
                    continue
                elif _is_invalid_key_error(err):
                    print(f"[LLM] Groq invalid key — trying next key...")
                    break
                elif _is_unavailable_model_error(err):
                    DISABLED_GROQ_MODELS.add(model)
                    print(f"[LLM] Groq model unavailable {model} — skipping from now on")
                    continue
                else:
                    print(f"[LLM] Groq error on {model}: {e}")
                    continue

    raise ProviderUnavailable("All Groq keys and models exhausted")


# ─── Gemini Call ──────────────────────────────────────────────────────────────

@traceable(
    run_type = "llm",
    name     = "gemini_call",
    tags     = ["gemini", "fallback_provider"]
)
def _call_gemini(
    system_prompt: str,
    user_message:  str,
    max_tokens:    int,
    agent_name:    str = "unknown"
) -> str:
    """
    Call Gemini API with key rotation.

    @traceable logs this as a CHILD trace under call_llm in LangSmith.
    Used as fallback when all Groq keys fail.
    """

    keys = GOOGLE_KEYS.copy()
    random.shuffle(keys)

    if agent_name == "chat_agent":
        keys = keys[:2]

    attempts = 0
    for key in keys:
        if attempts >= _cfg.LLM_MAX_ATTEMPTS:
            break
        attempts += 1
        try:
            llm = ChatGoogleGenerativeAI(
                google_api_key    = key,
                model             = "gemini-1.5-flash",
                max_output_tokens = max_tokens,
                temperature       = 0.3,
                timeout           = _cfg.LLM_TIMEOUT_SECONDS,
                max_retries       = 0,
            )
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_message)
            ]
            response = llm.invoke(messages)
            print(f"[LLM] Gemini ok -> {agent_name}")
            return response.content

        except Exception as e:
            err = str(e).lower()
            if _is_rate_limit_error(err):
                print(f"[LLM] Gemini quota exceeded — trying next key...")
                continue
            elif _is_invalid_key_error(err):
                print(f"[LLM] Gemini invalid key — trying next key...")
                continue
            else:
                print(f"[LLM] Gemini error: {e} — trying next key...")
                continue

    raise ProviderUnavailable("All Gemini keys exhausted")


# ─── Main LLM Router ─────────────────────────────────────────────────────────

@traceable(
    run_type = "chain",
    name     = "call_llm",
    tags     = ["router", "main_brain"]
)
def call_llm(
    system_prompt: str,
    user_message:  str,
    max_tokens:    int = 2000,
    agent_name:    str = "unknown_agent"
) -> str:
    """
    Smart LLM router with automatic fallback.

    LangSmith trace tree per call:
        call_llm (parent — run_type: chain)
        └── groq_call (child — run_type: llm)    ← if Groq succeeds
         OR
        └── gemini_call (child — run_type: llm)  ← if Groq fails

    Priority:
    1. Groq (fastest, free, 4 keys rotating across 3 models)
    2. Gemini (free fallback, 4 keys rotating)

    Both are @traceable so LangSmith shows every call with:
    - Full system prompt
    - Full user message
    - Full response
    - Latency in ms
    - Token count
    - Which model was used
    - Which agent called it
    """

    # ── Try Groq first ────────────────────────────────────────────────────
    if GROQ_KEYS:
        try:
            return _call_groq(
                system_prompt = system_prompt,
                user_message  = user_message,
                max_tokens    = max_tokens,
                agent_name    = agent_name
            )
        except Exception as e:
            print(f"[LLM] ⚠️  Groq failed for {agent_name}: {e}")
            print(f"[LLM] Switching to Gemini...")

    # ── Fallback to Gemini ────────────────────────────────────────────────
    if GOOGLE_KEYS:
        try:
            return _call_gemini(
                system_prompt = system_prompt,
                user_message  = user_message,
                max_tokens    = max_tokens,
                agent_name    = agent_name
            )
        except Exception as e:
            print(f"[LLM] ⚠️  Gemini also failed for {agent_name}: {e}")

    raise ProviderUnavailable(f"All providers failed for agent: {agent_name}")


# ─── Streaming LLM ───────────────────────────────────────────────────────────

def stream_llm(
    system_prompt: str,
    user_message:  str,
    max_tokens:    int = 600,
    agent_name:    str = "chat_agent"
) -> Generator[str, None, None]:
    """
    Stream an LLM response chunk by chunk.

    Failover to another provider happens ONLY before the first chunk was
    delivered, so the client never sees duplicated or spliced text.  When no
    provider can start a stream ``ProviderUnavailable`` is raised and the
    caller renders a deterministic fallback; if a stream breaks after text was
    delivered ``StreamInterrupted`` is raised.  No financial advice is ever
    synthesised here.
    """
    messages = [SystemMessage(content=system_prompt), HumanMessage(content=user_message)]
    delivered = False
    attempts = 0
    deadline = time.monotonic() + _cfg.LLM_TIMEOUT_SECONDS * _cfg.LLM_MAX_ATTEMPTS * 2

    def _providers():
        if GROQ_KEYS:
            keys = GROQ_KEYS.copy()
            random.shuffle(keys)
            for key in keys:
                for model in GROQ_MODELS:
                    if model not in DISABLED_GROQ_MODELS:
                        yield "groq", key, model
        if GOOGLE_KEYS:
            keys = GOOGLE_KEYS.copy()
            random.shuffle(keys)
            for key in keys:
                yield "gemini", key, "gemini-1.5-flash"

    per_provider = {"groq": 0, "gemini": 0}      # bounded budget per provider so failover stays reachable
    for provider, key, model in _providers():
        if per_provider[provider] >= _cfg.LLM_MAX_ATTEMPTS or time.monotonic() > deadline:
            continue
        per_provider[provider] += 1
        attempts += 1
        try:
            if provider == "groq":
                llm = ChatGroq(api_key=key, model=model, max_tokens=max_tokens, temperature=0.3,
                               streaming=True, timeout=_cfg.LLM_TIMEOUT_SECONDS, max_retries=0)
            else:
                llm = ChatGoogleGenerativeAI(google_api_key=key, model=model, max_output_tokens=max_tokens,
                                             temperature=0.3, streaming=True,
                                             timeout=_cfg.LLM_TIMEOUT_SECONDS, max_retries=0)
            for chunk in llm.stream(messages):
                if chunk.content:
                    delivered = True
                    yield chunk.content
            return
        except Exception as e:
            if delivered:
                raise StreamInterrupted(type(e).__name__) from None
            err = str(e).lower()
            if provider == "groq" and _is_unavailable_model_error(err):
                DISABLED_GROQ_MODELS.add(model)
            continue            # nothing delivered yet: safe to try the next provider

    raise ProviderUnavailable(f"No provider could start a stream for {agent_name}")


# ─── LLM with History ─────────────────────────────────────────────────────────

@traceable(
    run_type = "chain",
    name     = "call_llm_with_history",
    tags     = ["router", "chat_history"]
)
def call_llm_with_history(
    system_prompt: str,
    messages:      list,
    max_tokens:    int = 2000,
    agent_name:    str = "chat_agent"
) -> str:
    """
    Call LLM with full conversation history.

    Flattens history list into a single user message
    and routes through the standard call_llm router.

    @traceable logs this as a separate chain in LangSmith
    with the full history visible in the trace.
    """

    history_text = ""
    for msg in messages:
        role         = msg.get("role", "user").upper()
        content      = msg.get("content", "")
        history_text += f"{role}: {content}\n\n"

    combined = (
        f"Conversation History:\n"
        f"{history_text}\n"
        f"Respond to the last user message."
    )

    return call_llm(
        system_prompt = system_prompt,
        user_message  = combined,
        max_tokens    = max_tokens,
        agent_name    = agent_name
    )