import json
import os

_PATH = os.path.join(os.path.dirname(__file__), "..", "custom_commands.json")
MAX_PER_GUILD = 25


def _load() -> dict:
    try:
        with open(_PATH, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _save(data: dict):
    with open(_PATH, "w") as f:
        json.dump(data, f, indent=2)


def get_commands(guild_id: int) -> dict:
    """Returns {trigger: response} for a guild."""
    return _load().get(str(guild_id), {})


def add_command(guild_id: int, trigger: str, response: str) -> bool:
    """Returns False if limit reached, True if added."""
    data = _load()
    key = str(guild_id)
    if key not in data:
        data[key] = {}
    if len(data[key]) >= MAX_PER_GUILD and trigger.lower() not in data[key]:
        return False
    data[key][trigger.lower()] = response
    _save(data)
    return True


def remove_command(guild_id: int, trigger: str) -> bool:
    """Returns False if trigger not found, True if removed."""
    data = _load()
    key = str(guild_id)
    if key not in data or trigger.lower() not in data[key]:
        return False
    del data[key][trigger.lower()]
    _save(data)
    return True


def check_triggers(guild_id: int, message: str) -> str | None:
    """Check if any sentence in the message starts with a trigger. Returns response or None."""
    commands = get_commands(guild_id)
    # Split into sentences and strip whitespace from each
    sentences = [s.strip() for s in message.replace("!", ".").replace("?", ".").split(".") if s.strip()]
    for trigger, response in commands.items():
        for sentence in sentences:
            if sentence.lower().startswith(trigger):
                return response
    return None
