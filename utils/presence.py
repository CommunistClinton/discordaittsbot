import asyncio
import random
from utils.logger import get_logger

presence_logger = get_logger("presence")

# Tracks message count per guild for interruption logic
_message_counters: dict[int, int] = {}

# Interruption prompts — Aarshi reacts to what someone just said
INTERRUPT_PROMPTS = [
    "React to what this person just said in one short mocking sentence. Be dismissive.",
    "Interrupt this conversation with a short self-centred comment. Make it about yourself.",
    "Mock what this person said in one sentence. Be dramatic and condescending.",
    "Dismiss what this person said in one short sentence. Act unbothered.",
    "React to this message like it personally offended you. One sentence only.",
]

# Random ping prompts — unprompted attacks
PING_PROMPTS = [
    "Pick on this person with a short one-sentence mock. No reason needed. Be dramatic.",
    "Send this person a short unsolicited insult. One sentence. Make it personal.",
    "Randomly call out this person in one short sentence. Be condescending.",
    "Send this person a one-sentence reminder that you find them annoying.",
    "Mock this person's existence in one short sentence. Be theatrical.",
]


def should_interrupt(guild_id: int) -> bool:
    """Returns True 1 in 5 times a message is sent."""
    _message_counters[guild_id] = _message_counters.get(guild_id, 0) + 1
    if _message_counters[guild_id] >= 5:
        _message_counters[guild_id] = 0
        return True
    # Also randomly skip sometimes so it doesn't feel perfectly timed
    return random.random() < 0.15


def get_interrupt_prompt(message_content: str, username: str) -> str:
    base = random.choice(INTERRUPT_PROMPTS)
    return f"{base}\n\nUser: {username}\nMessage: {message_content}"


def get_ping_prompt(username: str) -> str:
    base = random.choice(PING_PROMPTS)
    return f"{base}\n\nTarget: {username}"


def random_ping_interval() -> int:
    """Returns a random interval in seconds between 10 and 20 minutes."""
    return random.randint(10 * 60, 20 * 60)
