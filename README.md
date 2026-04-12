# CrewChief Assistant

AI-powered voice assistant for [CrewChief](https://thecrewchief.org). Say what you need — fuel report, tire status, pit request — and the app triggers the corresponding CrewChief action for you. Uses OpenAI Whisper for speech recognition and GPT for intent mapping, so you can speak naturally instead of memorizing exact phrases.

The app works by emulating virtual game controllers (**Xbox 360** or **DualShock 4**) via ViGEmBus. Each controller button is mapped to a CrewChief action. When you speak a command, the app presses the right button automatically. Virtual controllers are used instead of keyboard shortcuts so there are no conflicts with your game or sim keybinds.

> **Tip:** If you race with a physical Xbox controller, the game may also react to the virtual X360 button presses. To avoid this, use **DS4** as your virtual controller type in the app (or vice versa) — pick whichever type you're **not** already using for driving.

## Why Not Just Use CrewChief's Built-in Voice Commands?

CrewChief has its own voice recognition, but it relies on Windows Speech Recognition which requires exact phrases and often struggles with accuracy — especially with background noise or non-native accents. This app uses OpenAI's Whisper model, which is significantly more accurate and understands natural language. You don't need to memorize exact commands — just say what you mean and the AI figures out the intent.

## Requirements

- Python 3.11+
- [ViGEmBus](https://github.com/nefarius/ViGEmBus/releases) driver
- OpenAI API key

## ViGEmBus Driver

This app creates virtual Xbox 360 or DualShock 4 controllers to send button presses to your game. ViGEmBus is the driver that makes this possible — without it, the app can't create virtual gamepads.

If you install via `poetry install`, the ViGEmBus driver is installed automatically (you'll see an installer popup during setup). If you're using the pre-built `.exe`, you need to install it manually:

1. Go to the [ViGEmBus releases page](https://github.com/nefarius/ViGEmBus/releases)
2. Download the latest `ViGEmBus_Setup_x.x.x.exe`
3. Run the installer and restart your PC if prompted

## Setup

```bash
pip install poetry
poetry install
```

Set your API key by copying `.env.example` to `.env`, or configure it directly in the app's UI.

## Usage

You have two ways to set up your voice commands:

### Method 1: Manual Keybinds

1. **Launch the Assistant app.** It initializes 1 virtual X360 controller by default.

2. **Add controllers.** Click ADD CONTROLLER to add up to 3 total. You can choose between X360 and DS4 controller types.

3. **Rename commands.** Right-click any button in the controller grid to rename its voice command (e.g., "fuel report", "tire status").

4. **Bind actions in CrewChief.** Click each button in the app to simulate the keypress, then map it to the corresponding action in CrewChief's UI.

5. **Test.** Press START in the app, hold your Push-To-Talk key, and speak your commands.

### Method 2: CrewChief Auto-Sync

The sync tool automatically maps all available CrewChief actions to your virtual controllers. Follow these steps **in order**:

1. **Launch the Assistant app.** It initializes 1 virtual X360 controller by default.

2. **Add controllers.** Click ADD CONTROLLER to add up to 3 total (X360 or DS4). The more controllers you add, the more actions you can bind.

3. **Launch CrewChief.** Start CrewChief so it can detect your virtual controllers.

4. **Let CrewChief scan the controllers.** In CrewChief, go to *Controller settings*. Press each button on the virtual controllers (click them in the Assistant app) so CrewChief registers the devices and their buttons. This ensures CrewChief writes the correct device GUIDs into its configuration.

5. **Save CrewChief's configuration.** Close CrewChief (or manually save your profile). CrewChief must write the detected controller GUIDs to its config file before the sync can work.

6. **Run the sync.** Back in the Assistant app, click SYNC WITH CREWCHIEF.

7. **Select the configuration file** when prompted.
   - Default path: `Documents\CrewChiefV4\Profiles\ControllerData\defaultSettings.json`

8. **Sync completes.** The app will automatically:
   - Back up the original CrewChief configuration.
   - Map all available CrewChief actions to your virtual controllers.
   - Update button bindings in the app to match.

9. **Restart CrewChief.** The sync writes directly to CrewChief's config file. **You must restart CrewChief** for the new bindings to take effect.

### Voice Commands

Once set up, press START in the app, hold your Push-to-Talk key (default: Scroll Lock), and speak naturally:

- "How's my tire wear?"
- "What's my fuel situation?"
- "Request pit stop"
- "Gap to the car ahead"

Any variation works — the AI understands the intent, not just exact phrases.

### Settings

Configure the application in the SETTINGS panel:

- **OpenAI API Key** — Required for speech recognition and intent routing.
- **Input Device** — Choose your microphone.
- **Push to Talk Key** — Default: Scroll Lock.
- **Audio Feedback** — Plays a beep when voice recording starts/stops.
- **Min. Confidence** — Minimum AI confidence threshold to accept a command (0-100%).

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
