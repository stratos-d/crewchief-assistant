from src.config_manager import get_openai_client, get_all_commands, get_setting

def transcribe_audio(virtual_audio_file):
    if not virtual_audio_file:
        return None

    print("Sending audio to OpenAI Whisper API...")

    try:
        client = get_openai_client()

        # Build prompt from all commands across all controllers
        commands = get_all_commands()
        prompt = "sim racing, pit stop, box box, fuel, tires, gap ahead, damage report, clear comms, lap time."
        if commands:
            prompt = ", ".join(commands)

        transcription = client.audio.transcriptions.create(
            model=get_setting("models.stt", "whisper-1"),
            file=virtual_audio_file,
            language="en",
            prompt=prompt
        )

        text = transcription.text
        print(f"Transcription complete: '{text}'")
        return text

    except Exception as e:
        print(f"OpenAI API Error: {e}")
        return None