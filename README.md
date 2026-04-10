# CrewChief Assistant

Voice-controlled virtual gamepad for sim racing. Hold a push-to-talk key, speak a command, and the app presses the corresponding virtual Xbox 360 controller button. Uses OpenAI Whisper for speech-to-text and GPT for intent mapping.

Works with any game that supports gamepad input.

## Requirements

- Python 3.13+
- [ViGEmBus](https://github.com/nefarius/ViGEmBus/releases) driver
- OpenAI API key

## ViGEmBus Driver

This app creates virtual Xbox 360 controllers to send button presses to your game. ViGEmBus is the driver that makes this possible — without it, the app can't create virtual gamepads.

1. Go to the [ViGEmBus releases page](https://github.com/nefarius/ViGEmBus/releases)
2. Download the latest `ViGEmBus_Setup_x.x.x.exe`
3. Run the installer and restart your PC if prompted

You only need to do this once.

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

You can bind up to 3 virtual controllers with 14 buttons each. Commands are natural language — the AI matches intent, not exact wording. Right-click any button in the GUI to rename its command.

## Build

```bash
poetry run pyinstaller CrewChiefAssistant.spec --clean
```

Output: `dist/CrewChiefAssistant.exe`

## Config

On first run, `config.default.json` is copied to `config.json` (gitignored). All settings and bindings are saved there.

## Disclaimer

This is a personal project. Use at your own risk.
