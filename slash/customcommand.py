import discord
from discord import app_commands
from utils.roles import is_mod
from utils.custom_commands import get_commands, add_command, remove_command
from utils.errors import safe_send

MAX_PER_GUILD = 25


class CustomCommandListView(discord.ui.View):
    def __init__(self, guild: discord.Guild):
        super().__init__(timeout=60)
        self.guild = guild
        commands = get_commands(guild.id)

        if commands:
            options = [
                discord.SelectOption(
                    label=trigger,
                    description=response[:50] + "..." if len(response) > 50 else response,
                    value=trigger
                )
                for trigger, response in list(commands.items())[:25]
            ]
            remove_select = discord.ui.Select(
                placeholder="Remove a trigger...",
                options=options,
                row=0
            )
            remove_select.callback = self.remove_callback
            self.add_item(remove_select)

    def build_embed(self) -> discord.Embed:
        commands = get_commands(self.guild.id)
        embed = discord.Embed(
            title="Custom Commands",
            color=discord.Color.blurple()
        )
        if not commands:
            embed.description = "No custom commands set."
        else:
            for trigger, response in commands.items():
                embed.add_field(
                    name=f"`{trigger}`",
                    value=response[:100] + "..." if len(response) > 100 else response,
                    inline=False
                )
            embed.set_footer(text=f"{len(commands)}/{MAX_PER_GUILD} commands used")
        return embed

    async def remove_callback(self, interaction: discord.Interaction):
        if not is_mod(interaction.user):
            await interaction.response.send_message(
                "You don't have permission to remove triggers.", ephemeral=True
            )
            return
        trigger = interaction.data["values"][0]
        remove_command(self.guild.id, trigger)

        # Rebuild view with updated commands
        new_view = CustomCommandListView(self.guild)
        await interaction.response.edit_message(embed=new_view.build_embed(), view=new_view)
        await interaction.followup.send(f"Trigger `{trigger}` removed.", ephemeral=True)

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True


async def _add(interaction: discord.Interaction, trigger: str, response: str):
    if not is_mod(interaction.user):
        await safe_send(interaction, "You don't have permission to add custom commands.", ephemeral=True)
        return

    if len(trigger) > 50:
        await safe_send(interaction, "Trigger must be 50 characters or less.", ephemeral=True)
        return

    if len(response) > 500:
        await safe_send(interaction, "Response must be 500 characters or less.", ephemeral=True)
        return

    added = add_command(interaction.guild.id, trigger.lower(), response)

    if not added:
        await safe_send(
            interaction,
            f"This server has reached the limit of {MAX_PER_GUILD} custom commands. Remove one first.",
            ephemeral=True
        )
        return

    await safe_send(interaction, f"Trigger `{trigger.lower()}` added.")


async def _remove(interaction: discord.Interaction, trigger: str):
    if not is_mod(interaction.user):
        await safe_send(interaction, "You don't have permission to remove custom commands.", ephemeral=True)
        return

    removed = remove_command(interaction.guild.id, trigger.lower())

    if not removed:
        await safe_send(interaction, f"No trigger called `{trigger.lower()}` found.", ephemeral=True)
        return

    await safe_send(interaction, f"Trigger `{trigger.lower()}` removed.")


async def _list(interaction: discord.Interaction):
    view = CustomCommandListView(interaction.guild)
    embed = view.build_embed()
    await interaction.response.send_message(embed=embed, view=view)


def setup(bot, guild):

    custom_group = app_commands.Group(
        name="customcommand",
        description="Manage custom trigger commands",
        guild_ids=[guild.id]
    )

    @custom_group.command(name="add", description="Add a trigger and response")
    @app_commands.describe(trigger="The word or phrase that triggers the response", response="What the bot says when triggered")
    async def slash_add(interaction: discord.Interaction, trigger: str, response: str):
        await _add(interaction, trigger, response)

    @custom_group.command(name="remove", description="Remove a trigger")
    @app_commands.describe(trigger="The trigger to remove")
    async def slash_remove(interaction: discord.Interaction, trigger: str):
        await _remove(interaction, trigger)

    @custom_group.command(name="list", description="View all custom triggers for this server")
    async def slash_list(interaction: discord.Interaction):
        await _list(interaction)

    bot.tree.add_command(custom_group)
