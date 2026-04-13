# CrewChief Assistant

LLM-powered voice assistant for [CrewChief](https://thecrewchief.org). Say what you need — fuel report, tire status, pit request — and the app triggers the corresponding CrewChief action for you. Uses OpenAI Whisper for speech recognition and GPT for intent mapping, so you can speak naturally instead of memorizing exact phrases.

The app works by emulating a virtual joystick via the [vJoy](https://sourceforge.net/projects/vjoystick/) driver. The vJoy device exposes up to 64 buttons, each mapped to a CrewChief action. When you speak a command, the app presses the right button automatically. A virtual joystick is used instead of keyboard shortcuts so there are no conflicts with your game or sim keybinds.

## Why Not Just Use CrewChief's Built-in Voice Commands?

CrewChief has its own voice recognition, but it relies on Windows Speech Recognition which requires exact phrases and often struggles with accuracy — especially with background noise or non-native accents. This app uses OpenAI's Whisper model, which is significantly more accurate and understands natural language. You don't need to memorize exact commands — just say what you mean and the LLM figures out the intent.

## Requirements

- Python 3.11+
- [vJoy driver](https://sourceforge.net/projects/vjoystick/)
- OpenAI API key

## vJoy Driver

This app uses vJoy to create a virtual joystick that sends button presses to CrewChief. Without it, the app can't trigger any actions.

### Installation

1. Download the latest installer from [vJoy on SourceForge](https://sourceforge.net/projects/vjoystick/).
2. Run the installer and restart your PC if prompted.

### Configuring vJoy

By default, vJoy creates Device 1 with only **8 buttons**. If you want more buttons to work (up to **64 buttons**), you need to expand the vJoy device configuration:

1. Open the Windows Start Menu and search for **Configure vJoy**.
2. Open the application. Make sure **Device 1** is selected at the top.
3. In the **Buttons** section, change the number from `8` to `64` (or whatever maximum you need).
4. Click **Apply**.

## Setup

```bash
pip install poetry
poetry install
```

Set your API key by copying `.env.example` to `.env`, or configure it directly in the app's UI.

## Usage

You have two ways to set up your voice commands:

### Method 1: Manual Keybinds

1. **Launch the Assistant app.** It initializes a single vJoy device.

2. **Rename commands.** Right-click any button in the controller grid to assign a voice command (e.g., "fuel report", "tire status").

3. **Bind actions in CrewChief.** Click each button in the app to simulate the button press, then map it to the corresponding action in CrewChief's UI.

### Method 2: CrewChief Auto-Sync

The sync function automatically maps all available CrewChief keybinds to vJoy buttons.

1. **Launch the Assistant app.** It initializes a single vJoy device.

2. **Register the vJoy device in CrewChief.** Launch CrewChief and click *Scan for controllers* in the controller settings. This writes the vJoy device GUID to CrewChief's config file.

3. **Run the sync.** Back in the Assistant app, click SYNC WITH CREWCHIEF.

4. **Select the CrewChiefs keybind configuration file** when prompted.
   - Default path: `Documents\CrewChiefV4\Profiles\ControllerData\defaultSettings.json`

5. **Sync done.** The app will automatically map all available CrewChief actions to vJoy buttons.

6. **Restart CrewChief.** The sync writes directly to CrewChief's config file. **You must restart CrewChief** for the new bindings to take effect.

### Voice Commands

Once set up, press START in the app, hold your Push-to-Talk key (default: Scroll Lock), and speak naturally:

- "How's my tire wear?"
- "What's my fuel situation?"
- "Request pit stop"
- "Gap to the car ahead"

Any variation works — the LLM understands the intent, not just exact phrases.

### Settings

Configure the application in the SETTINGS panel:

- **OpenAI API Key** — Required for speech recognition and intent routing.
- **Input Device** — Choose your microphone.
- **Push to Talk Key** — Default: Scroll Lock. Only keyboard keys are accepted (no mouse or controller buttons).
- **Audio Feedback** — Plays a beep when voice recording starts/stops.
- **Min. Confidence** — Minimum LLM confidence threshold to accept a command (0-100%).

## Build

To compile a standalone executable:

```bash
poetry run pyinstaller CrewChiefAssistant.spec --clean
```

Output will be located at: `dist/CrewChiefAssistant.exe`

## Config

On first run, `config.default.json` is copied to `config.json`. All user settings and bindings are saved there automatically.

## Disclaimer

This is a personal project. Use at your own risk. Check your simulation's Terms of Service regarding the use of external input automation tools.
