import json
from src import usage
from src.config_manager import get_openai_client, get_all_commands, get_setting

UNKNOWN_INTENT = "unknown"


def _intent_schema(valid_intents):
    """Structured-output schema that only allows a known command or "unknown"."""
    return {
        "name": "intent",
        "strict": True,
        "schema": {
            "type": "object",
            "properties": {
                "intent": {"type": "string", "enum": valid_intents + [UNKNOWN_INTENT]},
                "confidence": {"type": "integer"}
            },
            "required": ["intent", "confidence"],
            "additionalProperties": False
        }
    }


def _normalize(text):
    """Lowercase and drop punctuation, so "How's my fuel?" matches the command "hows my fuel"."""
    return " ".join("".join(ch for ch in text.lower() if ch.isalnum() or ch.isspace()).split())


def get_intent(transcribed_text):
    # Get all commands across all controllers (deduplicated, since the schema enum must be unique)
    valid_intents = list(dict.fromkeys(c for c in get_all_commands() if c != UNKNOWN_INTENT))
    if not valid_intents:
        return {"intent": UNKNOWN_INTENT, "confidence": 0}

    # Saying a command by name needs no LLM, which saves a whole API round trip
    spoken = _normalize(transcribed_text)
    for command in valid_intents:
        if _normalize(command) == spoken:
            print(f"Mapped Intent: {command} (exact match)")
            return {"intent": command, "confidence": 100, "exact": True}

    print(f"Routing intent for: '{transcribed_text}'...")

    system_prompt = (
        "You are an intelligent sim racing voice assistant. Map the user's command to ONE of: "
        + json.dumps(valid_intents) + ". "
        "If the request does not clearly match any of them, answer \"unknown\". "
        "Return 'intent' (the exact command, or \"unknown\") and 'confidence' (0-100)."
    )

    # API errors propagate so the caller can tell the driver what went wrong
    client = get_openai_client()
    model = get_setting("models.router", "gpt-4o-mini")
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": transcribed_text}
        ],
        response_format={"type": "json_schema", "json_schema": _intent_schema(valid_intents)},
        temperature=0.0
    )
    usage.record(model, getattr(response, "usage", None))

    try:
        result = json.loads(response.choices[0].message.content)
        intent = result.get("intent")
        if intent not in valid_intents:
            intent = UNKNOWN_INTENT
        confidence = max(0, min(100, int(result.get("confidence", 0))))
    except (TypeError, ValueError) as e:
        print(f"Router Error: unexpected reply ({e})")
        return {"intent": UNKNOWN_INTENT, "confidence": 0, "exact": False}
    print(f"Mapped Intent: {intent} ({confidence}%)")
    return {"intent": intent, "confidence": confidence, "exact": False}
