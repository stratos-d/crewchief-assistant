# CrewChief Assistant

Voice-controlled virtual gamepad for sim racing. Speak commands, get button presses.

## What It Does

1. Hold PTT key → speak a command
2. OpenAI Whisper transcribes your speech
3. GPT-4o-mini maps it to a command
4. Virtual Xbox 360 controller button is pressed

Works with any game that supports gamepad input.

## Requirements

- Python 3.13+
- OpenAI API key
- ViGEmBus driver (for virtual controller)

## Installation

```bash
pip install poetry
poetry install
```

## API Key Setup

Option 1: Copy `.env.example` to `.env` and fill in your key:
```bash
cp .env.example .env
```

Option 2: Set in the app via Settings > Configure

## Usage

```bash
python main.py
```

### Settings

| Setting | Description |
|---------|-------------|
| OpenAI API Key | Required for speech recognition and intent mapping |
| Input Device | Microphone to use for recording |
| Push to Talk Key | Key to hold while speaking |
| Audio Feedback | Play sound when PTT is pressed/released |
| Min. Confidence | Minimum confidence % to trigger a command |

### Virtual Controllers

- Up to 3 virtual Xbox 360 controllers
- Each controller has 14 bindable buttons
- Click **+** to add, **✕** to remove
- Right-click any button to rename the command

### Commands

Commands are natural language. Examples:
- "fuel status" → press A
- "check my tires" → maps to "tire status"
- "box this lap" → maps to "pit request"

The AI understands intent, not exact words.

## Build Executable

```bash
pip install pyinstaller
pyinstaller CrewChiefAssistant.spec --clean
```

Or with Poetry (pyinstaller is a dev dependency):
```bash
poetry install --with dev
poetry run pyinstaller CrewChiefAssistant.spec --clean
```

Or double-click `build.bat`.

Output: `dist/CrewChiefAssistant.exe`

## Config

On first run, `config.default.json` is copied to `config.json` (which is gitignored).
All user settings and bindings are stored in `config.json`:
- `settings` - app configuration
- `controllers` - virtual controller bindings
- `available_buttons` - A, B, X, Y, D-pad, shoulders, thumbs, back, start

## Project Structure

```
├── main.py              # Entry point
├── src/                 # Application source
│   ├── audio.py         # Recording
│   ├── stt.py           # Speech-to-text
│   ├── router.py        # Intent mapping
│   ├── gamepad.py       # Virtual controller
│   ├── config_manager.py# Config handling
│   ├── sounds.py        # Audio feedback
│   └── ui/              # GUI components
│       ├── app.py
│       ├── widgets.py
│       ├── modals.py
│       └── engine.py
├── resources/           # Sound files
├── config.default.json  # Default settings (template)
├── config.json          # User settings (gitignored)
├── .env.example         # Environment variable template
├── build.bat            # Build script
├── LICENSE              # MIT License
└── CrewChiefAssistant.spec
```
