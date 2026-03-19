# Discord AI Bot

A fully featured Discord bot with a dramatic, narcissistic AI personality. The bot responds to mentions, interrupts conversations unprompted, randomly pings server members, plays music, and handles full server moderation — all while staying in character.

---

## Features

### AI Personality
- Responds to @mentions with in-character AI responses powered by Groq (Llama 3.3 70B)
- Interrupts conversations unprompted — fires on 1 in every 5 messages
- Randomly pings server members every 10–20 minutes with unsolicited mocks
- Remembers each user's conversation history and builds a persona profile over time
- Text-to-speech responses via ElevenLabs when in a voice channel

### Music
- YouTube playback via yt-dlp — no API key required
- Queue system with pagination, shuffle, loop
- Playlist support via YouTube playlist URLs
- Interactive queue and now playing panels with playback controls
- Commands: `/play`, `/pause`, `/resume`, `/skip`, `/stop`, `/queue`, `/nowplaying`, `/shuffle`, `/loop`, `/volume`

### Moderation
- Warning system with persistent storage per guild
- Mute (timeout), kick, ban with confirmation panels
- Purge messages, unban by user ID
- All moderation commands require assigned mod or admin roles
- Commands: `/warn`, `/warnings`, `/mute`, `/unmute`, `/kick`, `/ban`, `/unban`, `/purge`

### Role Management
- Assign mod and admin roles per guild via interactive dropdown panel
- Roles persist across restarts via `roles.json`
- Only Discord administrators can assign admin roles
- Commands: `/modroles`, `/setmodrole`, `/setadminrole`

### Custom Triggers
- Mods can set custom trigger words and responses
- Fires when a trigger word appears at the start of any sentence
- Up to 25 triggers per server
- Commands: `/customcommand add`, `/customcommand remove`, `/customcommand list`

### Fun & Personality
- `/opinion` — Aarshi's dramatic hot take on any topic
- `/mood` — her current mood for the session
- `/beef @user` — publicly calls someone out
- `/roast @user` — personalised roast based on user memory
- `/profile @user` — Aarshi's opinion and persona card for a user with inline roast button

### Developer Commands
All dev commands are locked to the configured `DEV_ID` and are ephemeral.
- `/devstatus` — full bot status panel across all guilds
- `/devmemory` — inspect any user's memory or global stats
- `/devclearall` — wipe all memory with confirmation
- `/devping` — latency check
- `/devsetallowedchannel` — change the allowed text channel live
- `/devannounce` — send a message to the allowed channel as the bot

---

## Project Structure

```
discord_ai_bot/
├── bot.py                  — Entry point, event handlers, presence system
├── config.json             — Local config (never committed)
├── config.example.json     — Template for config.json
├── requirements.txt        — Python dependencies
├── Procfile                — Railway deployment
├── runtime.txt             — Python version for Railway
├── nixpacks.toml           — FFmpeg installation for Railway
├── slash/                  — All slash commands (auto-discovered)
│   ├── play.py, queue.py, nowplaying.py, skip.py ...
│   ├── warn.py, kick.py, ban.py, mute.py ...
│   ├── opinion.py, mood.py, beef.py, roast.py ...
│   ├── customcommand.py
│   └── dev.py
└── utils/
    ├── ai.py               — Groq API, ask_ai(), update_persona()
    ├── tts.py              — ElevenLabs TTS, cache management
    ├── music.py            — yt-dlp queue system, playback
    ├── memory.py           — Per-user conversation memory
    ├── roles.py            — Per-guild mod/admin role storage
    ├── warnings.py         — Per-guild warning storage
    ├── custom_commands.py  — Custom trigger system
    ├── presence.py         — Interruption and random ping logic
    ├── config.py           — Config loader (env vars + config.json)
    ├── errors.py           — Standard error responses, safe_send()
    └── logger.py           — File and console logging
```

---

## Setup — Local

### Requirements
- Python 3.11+
- FFmpeg installed and added to PATH

### Installation

```bash
git clone https://github.com/CommunistClinton/discordaittsbot.git
cd discordaittsbot
pip install -r requirements.txt
```

### Configuration

Copy the example config and fill in your values:

```bash
cp config.example.json config.json
```

Edit `config.json`:

```json
{
  "DISCORD_TOKEN": "your_discord_bot_token",
  "GROQ_API_KEY": "your_groq_api_key",
  "ELEVENLABS_API_KEY": "your_elevenlabs_api_key",
  "VOICE_ID": "your_elevenlabs_voice_id",
  "ALLOWED_TEXT_CHANNEL_ID": 123456789,
  "MEMORY_FILE": "memory.json",
  "MAX_TTS_LENGTH": 180,
  "VOICE_COOLDOWN_SECONDS": 20,
  "TTS_CACHE_MAX_SIZE": 50,
  "DEV_ID": your_discord_user_id
}
```

### Create empty data files

```bash
echo "{}" > memory.json
echo "{}" > roles.json
echo "{}" > warnings.json
echo "{}" > custom_commands.json
```

### Run

```bash
python bot.py
```

---

## Setup — Railway

### 1. Fork or clone this repo to your GitHub

### 2. Create a new project on Railway
- Go to [railway.app](https://railway.app)
- New Project → Deploy from GitHub repo
- Select this repo

### 3. Add environment variables
In your Railway service → Variables tab, add:

| Variable | Value |
|---|---|
| `DISCORD_TOKEN` | Your Discord bot token |
| `GROQ_API_KEY` | Your Groq API key |
| `ELEVENLABS_API_KEY` | Your ElevenLabs API key |
| `VOICE_ID` | Your ElevenLabs voice ID |
| `ALLOWED_TEXT_CHANNEL_ID` | Channel ID where Aarshi responds |
| `DEV_ID` | Your Discord user ID |
| `MEMORY_FILE` | `memory.json` |
| `MAX_TTS_LENGTH` | `180` |
| `VOICE_COOLDOWN_SECONDS` | `20` |
| `TTS_CACHE_MAX_SIZE` | `50` |

### 4. Set service type to Worker
Railway → Service Settings → change from Web Service to **Worker**

### 5. Deploy
Railway will build and deploy automatically. Check the Logs tab to confirm:
```
Bot online: yourbot#xxxx
Synced 34 slash command(s)
```

> **Note:** `memory.json`, `roles.json`, `warnings.json`, and `custom_commands.json` reset on every Railway redeploy. For persistent storage across deploys, a database migration is required.

---

## API Keys

| Service | Purpose | Free Tier |
|---|---|---|
| [Discord Developer Portal](https://discord.com/developers) | Bot token | Free |
| [Groq](https://console.groq.com) | AI responses (Llama 3.3 70B) | Free |
| [ElevenLabs](https://elevenlabs.io) | Text to speech | Limited free tier |

---

## Bot Permissions

When adding the bot to a server, ensure it has:
- Read Messages / View Channels
- Send Messages
- Embed Links
- Manage Messages (for purge)
- Kick Members
- Ban Members
- Moderate Members (for timeout/mute)
- Connect (voice)
- Speak (voice)

---

## Commands Reference

### Music
| Command | Description |
|---|---|
| `/play [query]` | Play a song or YouTube playlist |
| `/pause` | Pause playback |
| `/resume` | Resume playback |
| `/skip` | Skip current track |
| `/stop` | Stop and clear queue |
| `/queue` | View queue with controls |
| `/nowplaying` | Current track with controls |
| `/shuffle` | Shuffle the queue |
| `/loop` | Toggle loop |
| `/volume [0-100]` | Set volume |

### Voice
| Command | Description |
|---|---|
| `/join` | Join your voice channel |
| `/leave` | Leave voice channel |
| `/say [text]` | Make Aarshi say something |

### Memory & Persona
| Command | Description |
|---|---|
| `/memory` | Your stored memory and persona |
| `/clear` | Wipe your memory |
| `/profile @user` | Aarshi's profile of a user |
| `/roast @user` | Roast someone |

### Fun
| Command | Description |
|---|---|
| `/opinion [topic]` | Aarshi's hot take |
| `/mood` | Her current mood |
| `/beef @user` | Public callout |

### Moderation
| Command | Description |
|---|---|
| `/warn @user [reason]` | Warn a user |
| `/warnings @user` | View warnings |
| `/mute @user [minutes]` | Timeout a user |
| `/unmute @user` | Remove timeout |
| `/kick @user` | Kick with confirmation |
| `/ban @user` | Ban with confirmation |
| `/unban [user_id]` | Unban by ID |
| `/purge [amount]` | Delete messages |

### Admin
| Command | Description |
|---|---|
| `/modroles` | Manage mod/admin roles |
| `/setmodrole @role` | Add a mod role |
| `/setadminrole @role` | Add an admin role |

### Custom Commands
| Command | Description |
|---|---|
| `/customcommand add [trigger] [response]` | Add a trigger |
| `/customcommand remove [trigger]` | Remove a trigger |
| `/customcommand list` | View all triggers |

### Utility
| Command | Description |
|---|---|
| `/help` | Browse all commands by category |
| `/status` | Bot status and your memory stats |

---

## Notes

- The bot only responds to messages in the channel set as `ALLOWED_TEXT_CHANNEL_ID`
- Random pings fire every 10–20 minutes to any non-bot server member
- Conversation interruptions fire on roughly 1 in 5 messages
- Voice receive (wake word system) is disabled pending DAVE E2E encryption support in `discord-ext-voice-recv`
- All slash commands are guild-synced for instant availability
