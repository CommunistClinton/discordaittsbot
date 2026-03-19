import asyncio
import importlib
import os
import random
import re
import traceback
import discord
from discord import app_commands
from discord.ext import commands

from utils.config import config
from utils.ai import ask_ai
from utils.tts import speak
from utils.logger import bot_logger, slash_logger
from utils.errors import safe_send, unexpected_error
from utils.music import set_event_loop
from utils.custom_commands import check_triggers
from utils.presence import (
    should_interrupt,
    get_interrupt_prompt,
    get_ping_prompt,
    random_ping_interval
)

GUILD = discord.Object(id=1287755847321260124)

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)


# ================= SLASH COMMAND LOADER =================

def load_slash_commands():
    slash_dir = os.path.join(os.path.dirname(__file__), "slash")
    loaded = 0
    failed = 0
    for filename in sorted(os.listdir(slash_dir)):
        if filename.startswith("_") or not filename.endswith(".py"):
            continue
        module_name = f"slash.{filename[:-3]}"
        try:
            module = importlib.import_module(module_name)
            if hasattr(module, "setup"):
                module.setup(bot, GUILD)
                slash_logger.info(f"Loaded slash: {module_name}")
                loaded += 1
            else:
                slash_logger.warning(f"Skipped slash: {module_name} (no setup function)")
        except Exception as e:
            slash_logger.error(f"Failed to load slash: {module_name} — {e}\n{traceback.format_exc()}")
            failed += 1
    bot_logger.info(f"Slash commands: {loaded} loaded, {failed} failed")


# ================= AI HELPER =================

async def _generate_presence_response(prompt: str) -> str | None:
    """Generate a short Aarshi response for interruptions and pings."""
    from groq import Groq
    import asyncio
    groq_client = Groq(api_key=config["GROQ_API_KEY"])

    def _call():
        return groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            max_tokens=60,
            temperature=0.9,
            messages=[
                {
                    "role": "system",
                    "content": """
You are Aarshi Lodia — dramatic, arrogant, narcissistic.
Respond in ONE short sentence only. Maximum 15 words.
No asterisks. No stage directions. No quotation marks.
Be sharp, dismissive, and self-centred.
"""
                },
                {"role": "user", "content": prompt}
            ]
        )

    try:
        completion = await asyncio.to_thread(_call)
        response = completion.choices[0].message.content.strip()
        response = re.sub(r"\*.*?\*", "", response).strip()
        return response
    except Exception as e:
        bot_logger.error(f"Presence AI error: {e}")
        return None


# ================= RANDOM PING LOOP =================

async def random_ping_loop():
    """Background loop that randomly pings someone every 10-20 minutes."""
    await bot.wait_until_ready()
    bot_logger.info("Random ping loop started")

    while not bot.is_closed():
        interval = random_ping_interval()
        bot_logger.debug(f"Next random ping in {interval // 60}m {interval % 60}s")
        await asyncio.sleep(interval)

        try:
            guild = bot.get_guild(GUILD.id)
            if guild is None:
                continue

            allowed_channel = guild.get_channel(config["ALLOWED_TEXT_CHANNEL_ID"])
            if allowed_channel is None:
                continue

            # Get all members excluding bots
            members = [m for m in guild.members if not m.bot]
            if not members:
                continue

            target = random.choice(members)
            prompt = get_ping_prompt(target.display_name)
            response = await _generate_presence_response(prompt)

            if response:
                await allowed_channel.send(f"{target.mention} {response}")
                bot_logger.info(f"Random ping sent to {target.display_name}")

        except Exception as e:
            bot_logger.error(f"Random ping loop error: {e}")


# ================= GLOBAL ERROR HANDLER =================

@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    command_name = interaction.command.name if interaction.command else "unknown"

    if isinstance(error, app_commands.CommandNotFound):
        bot_logger.warning(f"Unknown command used: {command_name}")
        await safe_send(interaction, "I don't know that command.", ephemeral=True)
    elif isinstance(error, app_commands.MissingPermissions):
        bot_logger.warning(f"Missing permissions for {command_name} by {interaction.user}")
        await safe_send(interaction, "You don't have permission to use this command.", ephemeral=True)
    elif isinstance(error, app_commands.BotMissingPermissions):
        bot_logger.error(f"Bot missing permissions for {command_name}: {error.missing_permissions}")
        await safe_send(interaction, f"I'm missing permissions: `{', '.join(error.missing_permissions)}`", ephemeral=True)
    elif isinstance(error, app_commands.CommandOnCooldown):
        await safe_send(interaction, f"Slow down. Try again in {error.retry_after:.1f}s.", ephemeral=True)
    elif isinstance(error, app_commands.CheckFailure):
        await safe_send(interaction, "You don't have permission to use this command.", ephemeral=True)
    else:
        tb = traceback.format_exc()
        bot_logger.error(f"Unhandled error in /{command_name} by {interaction.user}: {error}\n{tb}")
        await safe_send(
            interaction,
            "Something broke. It's *definitely* not my fault. Try again.",
            ephemeral=True
        )


# ================= EVENTS =================

@bot.event
async def on_ready():
    bot_logger.info(f"Bot online: {bot.user} (ID: {bot.user.id})")
    set_event_loop(asyncio.get_event_loop())
    try:
        synced = await bot.tree.sync(guild=GUILD)
        bot_logger.info(f"Synced {len(synced)} slash command(s): {[c.name for c in synced]}")
    except Exception as e:
        bot_logger.error(f"Failed to sync slash commands: {e}")
    # Start background loops
    bot.loop.create_task(random_ping_loop())


@bot.event
async def on_guild_join(guild: discord.Guild):
    bot_logger.info(f"Joined guild: {guild.name} (ID: {guild.id})")


@bot.event
async def on_guild_remove(guild: discord.Guild):
    bot_logger.info(f"Removed from guild: {guild.name} (ID: {guild.id})")


@bot.event
async def on_voice_state_update(member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
    vc = member.guild.voice_client
    if vc and vc.is_connected():
        if len(vc.channel.members) == 1:
            await vc.disconnect()
            bot_logger.info(f"Auto-disconnected from {vc.channel.name} — no listeners")


@bot.event
async def on_message(message: discord.Message):
    if message.author == bot.user:
        return

    if message.channel.id != config["ALLOWED_TEXT_CHANNEL_ID"]:
        return

    # Check custom triggers
    trigger_response = check_triggers(message.guild.id, message.content)
    if trigger_response:
        await message.channel.send(trigger_response)
        return

    # Conversation interruptions — fires 1 in 5 messages, skips mentions
    if bot.user not in message.mentions and not message.author.bot:
        if should_interrupt(message.guild.id):
            prompt = get_interrupt_prompt(message.content, message.author.display_name)
            response = await _generate_presence_response(prompt)
            if response:
                await message.channel.send(response)
                bot_logger.info(f"Interrupted {message.author.display_name}'s message")
            return

    # Respond to @mentions
    if bot.user not in message.mentions:
        return

    question = message.content.replace(
        f"<@{bot.user.id}>", ""
    ).replace(
        f"<@!{bot.user.id}>", ""
    ).strip()

    if not question:
        await message.channel.send("What do you want?")
        return

    bot_logger.info(f"Mention from {message.author} ({message.author.id}): {question[:60]}")

    async with message.channel.typing():
        try:
            response = await ask_ai(
                message.author.id,
                message.author.name,
                question
            )
            await asyncio.sleep(1)
        except Exception as e:
            bot_logger.error(f"ask_ai failed for {message.author}: {e}\n{traceback.format_exc()}")
            await message.channel.send(
                "Ugh, I can't even right now. Something broke and it's *definitely* not my fault."
            )
            return

    await message.channel.send(response)

    vc = message.guild.voice_client
    if vc and message.author.voice:
        await speak(vc, response, message.author.id)


@bot.event
async def on_error(event: str, *args, **kwargs):
    bot_logger.error(f"Unhandled error in event '{event}':\n{traceback.format_exc()}")


# ================= RUN =================

async def main():
    async with bot:
        load_slash_commands()
        bot_logger.info("Starting bot...")
        try:
            await bot.start(config["DISCORD_TOKEN"])
        except discord.LoginFailure:
            bot_logger.critical("Invalid Discord token — check your config.json")
        except Exception as e:
            bot_logger.critical(f"Fatal error during bot startup: {e}\n{traceback.format_exc()}")


asyncio.run(main())
