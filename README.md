# CrewChief Assistant

Voice-controlled assistant for [CrewChief](https://thecrewchief.org). Speak a command, and the app presses a virtual Xbox 360 controller button — which you map to CrewChief's key bindings. This lets you trigger CrewChief actions like fuel reports, tire status, or pit requests entirely by voice.

Uses OpenAI Whisper for speech-to-text and GPT for intent mapping. Works with any sim that supports gamepad input alongside CrewChief.

## Why Not Just Use CrewChief's Built-in Voice Commands?

CrewChief has its own voice recognition, but it relies on Windows Speech Recognition which requires exact phrases and often struggles with accuracy — especially with background noise or non-native accents. This app uses OpenAI's Whisper model, which is significantly more accurate and understands natural language. You don't need to memorize exact commands — just say what you mean and the AI figures out the intent.

## Requirements

- Python 3.13+
- [ViGEmBus](https://github.com/nefarius/ViGEmBus/releases) driver
- OpenAI API key

## ViGEmBus Driver

This app creates virtual Xbox 360 controllers to send button presses to your game. ViGEmBus is the driver that makes this possible — without it, the app can't create virtual gamepads.

If you install via `poetry install`, the ViGEmBus driver is installed automatically (you'll see an installer popup during setup). If you're using the pre-built `.exe`, you need to install it manually:

1. Go to the [ViGEmBus releases page](https://github.com/nefarius/ViGEmBus/releases)
2. Download the latest `ViGEmBus_Setup_x.x.x.exe`
3. Run the installer and restart your PC if prompted

## Setup

```bash
pip install poetry
poetry install
```

Set your API key by copying `.env.example` to `.env`, or configure it in the app.

## Usage

```bash
python main.py
```

The app creates up to 3 virtual Xbox 360 controllers with 14 buttons each. In CrewChief's settings, bind its actions (e.g. "fuel report", "tire status") to these virtual controller buttons. Then when you speak a command, the app presses the matching button and CrewChief responds.

Commands are natural language — the AI matches intent, not exact wording. Right-click any button in the GUI to rename its command.

## Build

```bash
poetry run pyinstaller CrewChiefAssistant.spec --clean
```

Output: `dist/CrewChiefAssistant.exe`

## Config

On first run, `config.default.json` is copied to `config.json` (gitignored). All settings and bindings are saved there.

## Disclaimer

This is a personal project. Use at your own risk.
