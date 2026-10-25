# CrewChief Assistant

LLM-powered voice assistant for [CrewChief](https://thecrewchief.org). Say what you need — fuel report, tire status, pit request — and the app triggers the corresponding CrewChief action for you. Uses OpenAI speech-to-text (`gpt-4o-mini-transcribe`) for speech recognition and GPT for intent mapping, so you can speak naturally instead of memorizing exact phrases.

The app works by emulating a virtual joystick via the [vJoy](https://sourceforge.net/projects/vjoystick/) driver. The vJoy device exposes up to 64 buttons, each mapped to a CrewChief action. When you speak a command, the app presses the right button automatically. A virtual joystick is used instead of keyboard shortcuts so there are no conflicts with your game or sim keybinds.

## Use Case

CrewChief has its own voice recognition, but it relies on Windows Speech Recognition which requires exact phrases and often struggles with accuracy — especially with background noise or non-native accents. This app uses OpenAI's speech-to-text models, which are significantly more accurate and understand natural language. You don't need to memorize exact commands — just say what you mean and the LLM figures out the intent.

## Requirements

- Python >=3.13,<3.15
- [vJoy driver](https://sourceforge.net/projects/vjoystick/)
- OpenAI API key

### API key storage

Your OpenAI API key is stored in **Windows Credential Manager**, encrypted with your Windows login. It is not saved in `config.json`; keys saved there by older versions are moved automatically on first launch. You can see or remove it under *Credential Manager → Windows Credentials → CrewChief Assistant*.

This keeps the key out of config files, backups and other Windows accounts, but programs running under your own account can still use it. For extra safety, use a dedicated key with restricted permissions and a monthly budget limit set in your OpenAI project.

## Installation

Download the compiled binary from [Releases](https://github.com/stratos-d/crewchief-assistant/releases)
or build it yourself (see [Setup](#setup) and [Build](#build)).

## vJoy Driver

This app uses vJoy to create a virtual joystick that sends button presses to CrewChief. Without it, the app can't trigger any actions.

### Installing vJoy

1. Download the latest installer from [vJoy on SourceForge](https://sourceforge.net/projects/vjoystick/).
2. Run the installer and restart your PC if prompted.

### Configuring vJoy

By default, vJoy creates Device 1 with only **8 buttons**. If you want more buttons to work (up to **64 buttons**), you need to expand the vJoy device configuration:

1. Open the Windows Start Menu and search for **Configure vJoy**.
2. Open the application. Make sure **Device 1** is selected at the top.
3. In the **Buttons** section, change the number from `8` to `64` (or whatever maximum you need).
4. Click **Apply**.

## Usage

On first launch, a **setup wizard** walks you through vJoy, your OpenAI key, the microphone, the push-to-talk key and CrewChief, then lets you try a command. You can run it again from Home or Settings.

The app has four pages in the sidebar: **Home**, **Commands**, **Settings** and **Activity**. The **Setup** checklist on Home shows what still needs doing (vJoy driver, OpenAI key, microphone, CrewChief sync), each with a button to fix it.

You have two ways to set up your voice commands:

### Method 1: Manual Keybinds

1. **Launch the Assistant app.** It initializes a single vJoy device.

2. **Name commands.** On the **Commands** page, turn on *Show empty buttons*, then click **Assign** (or double-click a row) to give a button a voice command (e.g., "fuel report", "tire status").

3. **Bind actions in CrewChief.** Click **Test** on a command to press its vJoy button, then map it to the corresponding action in CrewChief's UI.

### Method 2: CrewChief Auto-Sync

The sync function automatically maps all available CrewChief keybinds to vJoy buttons.

1. **Launch the Assistant app.** It initializes a single vJoy device.

2. **Register the vJoy device in CrewChief.** Launch CrewChief and click *Scan for controllers* in the controller settings. This writes the vJoy device GUID to CrewChief's config file.

3. **Run the sync.** Back in the Assistant app, click **Sync with CrewChief** on the Commands page (or **Sync** in the Setup checklist).

4. **Select the CrewChiefs keybind configuration file** when prompted.
   - Default path: `Documents\CrewChiefV4\Profiles\ControllerData\defaultSettings.json`

5. **Sync done.** The app will automatically map all available CrewChief actions to vJoy buttons.

6. **Restart CrewChief.** The sync writes directly to CrewChief's config file. **You must restart CrewChief** for the new bindings to take effect.

### Voice Commands

Once set up, click **Start listening**, hold your Push-to-Talk key (default: Scroll Lock), and speak naturally:

- "How's my tire wear?"
- "What's my fuel situation?"
- "Request pit stop"
- "Gap to the car ahead"

Any variation works — the LLM understands the intent, not just exact phrases. **Recent commands** on Home shows what was heard, which command it matched and which button was pressed; the **Activity** page has the full log.

### Settings

Everything on the **Settings** page saves as soon as you change it:

- **Push-to-talk key** — Default: Scroll Lock. Only keyboard keys are accepted (no mouse or controller buttons).
- **Microphone** — Choose your input device.
- **Minimum confidence** — Minimum LLM confidence to press a button (0-100%).
- **Beeps** — Plays a sound when push-to-talk starts and stops, and a falling double beep when a command didn't press a button, so you know to try again without looking.
- **API key** — Required for speech recognition and intent routing. **Test** checks that OpenAI accepts it.
- **Speech-to-text model** and **Command model** — The OpenAI models used for transcription and for picking the command.

## Setup

```bash
pip install poetry
poetry install
```

Set your API key by copying `.env.example` to `.env`, or configure it directly in the app's UI.

## Build

To compile a standalone executable:

```bash
poetry run pyinstaller CrewChiefAssistant.spec --clean
```

Output will be located at: `dist/CrewChiefAssistant.exe`

## Releases

Releases are published automatically. When a pull request is merged into `main`, the **Release on merge** workflow builds the exe, tags the merge commit with the next version and publishes a GitHub Release with `CrewChiefAssistant.exe` attached and notes listing the merged pull requests.

The version bump comes from the pull request's labels:

| Label | Example |
|---|---|
| *(none)* | `v0.5.1` → `v0.5.2` |
| `release:minor` | `v0.5.1` → `v0.6.0` |
| `release:major` | `v0.5.1` → `v1.0.0` |
| `skip-release` | No release for this merge |

You can still release by hand: push a `v*` tag, or run the **Build Windows exe** workflow from the Actions tab with a `release_tag`.

Release builds show their version in the sidebar. On launch they ask GitHub's public releases page whether a newer version exists (nothing about you is sent) and show an **Update** button if so.

## Config

On first run, the app creates `config.json` in the current user's application config directory.

Default location:

- **Windows:** `%APPDATA%\CrewChief Assistant\config.json`

All user settings and bindings are saved there automatically.

## Disclaimer

This is a personal project. Use at your own risk. Check your simulation's Terms of Service regarding the use of external input automation tools.
