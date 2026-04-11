# CrewChief Assistant

Voice-controlled assistant for [CrewChief](https://thecrewchief.org). Speak a command, and the app presses a virtual Xbox 360 controller button - which you map to CrewChief's key bindings. This lets you trigger CrewChief actions like fuel reports, tire status, or pit requests entirely by voice.

Uses OpenAI Whisper for speech-to-text and GPT for intent mapping. Works with any sim that supports gamepad input alongside CrewChief.

## Why Not Just Use CrewChief's Built-in Voice Commands?

CrewChief has its own voice recognition, but it relies on Windows Speech Recognition which requires exact phrases and often struggles with accuracy - especially with background noise or non-native accents. This app uses OpenAI's Whisper model, which is significantly more accurate and understands natural language. You don't need to memorize exact commands - just say what you mean and the AI figures out the intent.

## Requirements

- Python 3.11+
- [ViGEmBus](https://github.com/nefarius/ViGEmBus/releases) driver
- OpenAI API key

## ViGEmBus Driver

This app creates virtual Xbox 360 controllers to send button presses to your game. ViGEmBus is the driver that makes this possible - without it, the app can't create virtual gamepads.

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

1. Launch the Assistant app. It initializes 1 virtual controller by default.

2. Initialize controllers. Click ADD CONTROLLER in the VIRTUAL CONTROLLERS section to add up to 3 total, depending on how many commands you need.

3. Rename commands. Right-click any button in the controller grid to rename its voice command (e.g., "fuel report", "tire status").

4. Bind actions in CrewChief. Click each button in the app to simulate the keypress, then map it to the corresponding action in CrewChief's UI.

5. Test. Press START in the app, hold your Push-To-Talk key, and speak your commands.

### Method 2: CrewChief Auto-Sync

1. Launch the Assistant app. It initializes 1 virtual controller by default.

2. Initialize controllers. Click ADD CONTROLLER in the VIRTUAL CONTROLLERS section to add up to 3 total, depending on how many commands you need.

3. Launch CrewChief.

4. Verify hardware. In CrewChief, navigate to Settings > Controller Data to verify the virtual controllers are recognized.

5. Save the configuration. Close CrewChief (or manually save your profile). This forces CrewChief to write the newly discovered controller GUIDs into the configuration file to be synced.

6. Initiate sync. In the Assistant app, click SYNC WITH CREWCHIEF.

7. Select configuration. Choose your CrewChief configuration file when prompted.

   - Default path: `Documents\CrewChiefV4\Profiles\defaultSettings.json`

8. Confirm. The application will automatically:

   - Backup the original CrewChief configuration.
   - Map all "available" CrewChief actions to your active virtual controllers.
   - Save the updated configuration.

### Voice Commands

Once set up, press START in the app, hold your Push-to-Talk key (default: Scroll Lock), and speak naturally:

- "How's my tire wear?"
- "What's my fuel situation?"
- "Request pit stop"
- "Gap to the car ahead"

Any variation works - the AI understands the intent, not just exact phrases.

### Settings

Configure the application in the SETTINGS panel:

- **OpenAI API Key** - Required for speech recognition and intent routing.
- **Input Device** - Choose your microphone.
- **Push to Talk Key** - Default: Scroll Lock.
- **Audio Feedback** - Plays a beep when voice recording starts/stops.
- **Min. Confidence** - Minimum AI confidence threshold to accept a command (0-100%).

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
