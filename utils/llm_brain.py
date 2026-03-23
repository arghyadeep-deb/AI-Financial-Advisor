import os
import random
from typing import Generator
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage, HumanMessage
from langsmith import traceable

load_dotenv()

# ─── LangSmith Config ────────────────────────────────────────────────────────

os.environ["LANGCHAIN_TRACING_V2"] = os.getenv("LANGCHAIN_TRACING_V2", "true")
os.environ["LANGCHAIN_ENDPOINT"]   = os.getenv(
    "LANGCHAIN_ENDPOINT", "https://api.smith.langchain.com"
)
os.environ["LANGCHAIN_API_KEY"]  = os.getenv("LANGCHAIN_API_KEY", "")
os.environ["LANGCHAIN_PROJECT"]  = os.getenv("LANGCHAIN_PROJECT", "AI-Financial-Advisor")

LANGSMITH_ENABLED = bool(os.getenv("LANGCHAIN_API_KEY"))

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
if LANGSMITH_ENABLED:
    print(f"[LLM] ✓ LangSmith tracing enabled → project: {os.environ['LANGCHAIN_PROJECT']}")


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

    for key in keys:
        for model in GROQ_MODELS:
            if model in DISABLED_GROQ_MODELS:
                continue
            try:
                llm = ChatGroq(
                    api_key     = key,
                    model       = model,
                    max_tokens  = max_tokens,
                    temperature = 0.3,
                    tags        = [agent_name, "groq", model]
                )
                messages = [
                    SystemMessage(content=system_prompt),
                    HumanMessage(content=user_message)
                ]
                response = llm.invoke(messages)
                print(f"[LLM] ✓ Groq/{model} → {agent_name}")
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

    raise Exception("All Groq keys and models exhausted")


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

    for key in keys:
        try:
            llm = ChatGoogleGenerativeAI(
                google_api_key    = key,
                model             = "gemini-1.5-flash",
                max_output_tokens = max_tokens,
                temperature       = 0.3,
                tags              = [agent_name, "gemini"]
            )
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_message)
            ]
            response = llm.invoke(messages)
            print(f"[LLM] ✓ Gemini/gemini-1.5-flash → {agent_name}")
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

    raise Exception("All Gemini keys exhausted")


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

    raise Exception(
        f"[LLM] All providers failed for agent: {agent_name}. "
        f"Check your API keys in .env"
    )


# ─── Streaming LLM ───────────────────────────────────────────────────────────

def stream_llm(
    system_prompt: str,
    user_message:  str,
    max_tokens:    int = 600,
    agent_name:    str = "chat_agent"
) -> Generator[str, None, None]:
    """
    Stream LLM response token by token.

    Yields string chunks as they arrive from the LLM.
    Frontend renders each chunk immediately —
    user sees reply being typed in real time.

    Tries Groq streaming first then Gemini streaming.
    Falls back to non-streaming call_llm if all streaming fails.

    Note: @traceable is not used here because generators
    and LangSmith tracing have async conflicts.
    The individual LLM calls inside are still logged via tags.
    """

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_message)
    ]

    # ── Try Groq Streaming ────────────────────────────────────────────────
    if GROQ_KEYS:
        keys = GROQ_KEYS.copy()
        random.shuffle(keys)

        if agent_name == "chat_agent":
            keys = keys[:1]

        for key in keys:
            for model in GROQ_MODELS:
                if model in DISABLED_GROQ_MODELS:
                    continue
                try:
                    llm = ChatGroq(
                        api_key     = key,
                        model       = model,
                        max_tokens  = max_tokens,
                        temperature = 0.3,
                        streaming   = True
                    )
                    print(f"[LLM] Streaming via Groq/{model} → {agent_name}")

                    for chunk in llm.stream(messages):
                        if chunk.content:
                            yield chunk.content

                    # Successfully streamed — return
                    return

                except Exception as e:
                    err = str(e).lower()
                    if _is_rate_limit_error(err):
                        print(f"[LLM] Groq stream rate limit {model} — trying next...")
                        continue
                    elif _is_invalid_key_error(err):
                        print(f"[LLM] Groq stream invalid key — trying next key...")
                        break
                    elif _is_unavailable_model_error(err):
                        DISABLED_GROQ_MODELS.add(model)
                        print(f"[LLM] Groq stream model unavailable {model} — skipping from now on")
                        continue
                    else:
                        print(f"[LLM] Groq stream error {model}: {e} — trying next...")
                        continue

    # ── Try Gemini Streaming ──────────────────────────────────────────────
    if GOOGLE_KEYS:
        keys = GOOGLE_KEYS.copy()
        random.shuffle(keys)

        if agent_name == "chat_agent":
            keys = keys[:1]

        for key in keys:
            try:
                llm = ChatGoogleGenerativeAI(
                    google_api_key    = key,
                    model             = "gemini-1.5-flash",
                    max_output_tokens = max_tokens,
                    temperature       = 0.3,
                    streaming         = True
                )
                print(f"[LLM] Streaming via Gemini → {agent_name}")

                for chunk in llm.stream(messages):
                    if chunk.content:
                        yield chunk.content

                # Successfully streamed — return
                return

            except Exception as e:
                err = str(e).lower()
                if _is_rate_limit_error(err):
                    print(f"[LLM] Gemini stream quota exceeded — trying next key...")
                    continue
                else:
                    print(f"[LLM] Gemini stream error: {e} — trying next key...")
                    continue

    # ── Last Resort: Non-streaming Fallback ───────────────────────────────
    print(f"[LLM] ⚠️  Streaming unavailable for {agent_name} — falling back to non-streaming")

    # Avoid double retry latency for conversational UX.
    if agent_name == "chat_agent":
        yield "I am facing high traffic on the model providers right now. Based on your latest profile, continue with your planned SIP and emergency fund contribution today, and try again shortly for a detailed breakdown."
        return

    try:
        result = call_llm(
            system_prompt = system_prompt,
            user_message  = user_message,
            max_tokens    = max_tokens,
            agent_name    = agent_name
        )
        # Yield word by word to simulate streaming
        words = result.split(" ")
        for i, word in enumerate(words):
            if i == 0:
                yield word
            else:
                yield " " + word

    except Exception as e:
        print(f"[LLM] ⚠️  Non-streaming fallback also failed: {e}")
        yield "I am having trouble connecting right now. Please try again in a moment."


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