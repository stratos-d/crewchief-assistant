import json
from src.config_manager import get_openai_client, get_all_commands, get_setting

def get_intent(transcribed_text):
    # Get all commands across all controllers
    valid_intents = get_all_commands()
    if not valid_intents:
        return {"intent": "unknown", "confidence": 0}

    print(f"Routing intent for: '{transcribed_text}'...")

    system_prompt = (
        "You are an intelligent sim racing voice assistant. Map the user's command to ONE of: "
        + str(valid_intents) + ". "
        "Return ONLY a JSON object with 'intent' (the command) and 'confidence' (0-100)."
    )

    try:
        client = get_openai_client()
        response = client.chat.completions.create(
            model=get_setting("models.router", "gpt-4o-mini"),
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": transcribed_text}
            ],
            response_format={"type": "json_object"},
            temperature=0.0
        )

        result = json.loads(response.choices[0].message.content)
        print(f"Mapped Intent: {result.get('intent')} ({result.get('confidence')}%)")
        return result
    except Exception as e:
        print(f"Router Error: {e}")
        return {"intent": "unknown", "confidence": 0}