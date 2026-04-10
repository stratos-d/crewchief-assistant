"""
CrewChief Assistant - Entry Point

Usage:
    python main.py         # Launch GUI (default)
    python main.py --cli   # Launch CLI mode
"""
import sys


def main_gui():
    """Launch the graphical user interface."""
    import tkinter as tk
    from src.ui import CrewChiefGUI

    root = tk.Tk()
    CrewChiefGUI(root)
    root.mainloop()


def main_cli():
    """Launch command-line interface mode."""
    import time
    from src.audio import record_command
    from src.stt import transcribe_audio
    from src.router import get_intent
    from src.gamepad import trigger_action
    from src.config_manager import get_setting

    ptt_key = get_setting("ptt_key", "scroll lock")

    print("=======================================")
    print(" CrewChief Assistant Started! ")
    print("=======================================\n")
    print(f"PTT Key: {ptt_key.upper()}")
    print("Press Ctrl+C to exit.\n")

    while True:
        try:
            audio_buffer = record_command(ptt_key)

            if not audio_buffer:
                continue

            t0 = time.perf_counter()
            transcribed_text = transcribe_audio(audio_buffer)
            t1 = time.perf_counter()

            if not transcribed_text:
                continue

            result = get_intent(transcribed_text)
            intent = result.get("intent", "unknown")
            confidence = result.get("confidence", 0)
            t2 = time.perf_counter()

            threshold = get_setting("confidence_threshold", 50)
            if intent != "unknown" and confidence >= threshold:
                trigger_action(intent)
            else:
                print("Unrecognized command. Ignoring.")

            t3 = time.perf_counter()

            print(f"\n--- Performance ---")
            print(f"  STT:     {t1 - t0:.3f}s")
            print(f"  Router:  {t2 - t1:.3f}s")
            print(f"  Execute: {t3 - t2:.3f}s")
            print(f"  Total:   {t3 - t0:.3f}s\n")

        except KeyboardInterrupt:
            print("\nShutting down. See you on the track!")
            break

        except Exception as e:
            print(f"\nError: {e}")
            time.sleep(1)


def main():
    if "--cli" in sys.argv:
        main_cli()
    else:
        main_gui()


if __name__ == "__main__":
    main()