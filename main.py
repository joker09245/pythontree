import os
import random
import asyncio
from datetime import datetime, timedelta

import discord
from discord.ext import commands
from dotenv import load_dotenv

# Load the bot token from the .env file
load_dotenv()
BOT_TOKEN = os.getenv('BOT_TOKEN')

# Define bot intents and prefix
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix='.', intents=intents)

# In-memory storage (not persistent across restarts)
active_giveaways = {}
ticket_panels = {}
reminder_channels = {}

@bot.event
async def on_ready():
    """
    Called when the bot is connected to Discord.
    """
    print(f'Logged in as {bot.user.name}')
    print('------')

    # Send an online message to all channels that have a reminder set
    for channel_id in reminder_channels.values():
        channel = bot.get_channel(channel_id)
        if channel:
            embed = discord.Embed(
                title='Bot Status: Online',
                description=f'Hello! I am now online and ready to go!',
                color=discord.Color.green()
            )
            await channel.send(embed=embed)

@bot.command(name='embed')
@commands.has_permissions(administrator=True)
async def create_embed_button(ctx):
    """
    Creates an embed with a button.
    This command can only be used by administrators.
    """
    embed = discord.Embed(
        title="Custom Embed with Button",
        description="Click the button below to interact!",
        color=discord.Color.blue()
    )

    view = discord.ui.View()
    style = discord.ButtonStyle.primary
    button_label = "Click Me!"

    # Create the button and its callback function
    async def button_callback(interaction: discord.Interaction):
        await interaction.response.send_message("Button clicked! This is a dynamic message.", ephemeral=True)

    button = discord.ui.Button(label=button_label, style=style)
    button.callback = button_callback
    view.add_item(button)

    await ctx.send(embed=embed, view=view)

@bot.group(name='giveaway', invoke_without_command=True)
@commands.has_permissions(administrator=True)
async def giveaway_group(ctx):
    """
    Parent command for giveaway functions.
    """
    await ctx.send("Invalid giveaway command. Use `.giveaway start` or `.giveaway end`.")

@giveaway_group.command(name='start')
async def giveaway_start(ctx, duration: str, winners: int, *, prize: str):
    """
    Starts a giveaway. Example: `.giveaway start 1h 2 Nitro Classic`
    """
    try:
        # Parse the duration (e.g., 1h, 30m)
        time_unit = duration[-1]
        time_value = int(duration[:-1])
        end_time = datetime.now()

        if time_unit == 's':
            end_time += timedelta(seconds=time_value)
        elif time_unit == 'm':
            end_time += timedelta(minutes=time_value)
        elif time_unit == 'h':
            end_time += timedelta(hours=time_value)
        elif time_unit == 'd':
            end_time += timedelta(days=time_value)
        else:
            await ctx.send("Invalid duration format. Use `s`, `m`, `h`, or `d`.")
            return

    except (ValueError, IndexError):
        await ctx.send("Invalid format. Use `.giveaway start <duration> <winners> <prize>` (e.g., `1h 2 Nitro Classic`).")
        return

    embed = discord.Embed(
        title=f"🎉 GIVEAWAY: {prize} 🎉",
        description=f"React with 🎉 to enter!\n**Ends:** <t:{int(end_time.timestamp())}:R>\n**Winners:** {winners}",
        color=discord.Color.gold()
    )
    giveaway_msg = await ctx.send(embed=embed)
    await giveaway_msg.add_reaction('🎉')

    # Store giveaway info
    active_giveaways[giveaway_msg.id] = {
        'end_time': end_time,
        'winners': winners,
        'prize': prize,
        'channel_id': ctx.channel.id,
    }

    # Schedule the end of the giveaway
    await asyncio.sleep((end_time - datetime.now()).total_seconds())
    await end_giveaway(giveaway_msg)

@giveaway_group.command(name='end')
async def giveaway_end(ctx, message_id: int):
    """
    Manually ends a giveaway using its message ID.
    """
    message_id = int(message_id)
    if message_id in active_giveaways:
        try:
            giveaway_msg = await ctx.channel.fetch_message(message_id)
            await end_giveaway(giveaway_msg)
        except discord.NotFound:
            await ctx.send("Giveaway message not found.")
    else:
        await ctx.send("That giveaway is not active.")

async def end_giveaway(giveaway_msg):
    """
    Selects and announces the winner of a giveaway.
    """
    if giveaway_msg.id not in active_giveaways:
        return

    users = []
    # Fetch all reactions
    for reaction in giveaway_msg.reactions:
        if str(reaction.emoji) == '🎉':
            # Collect all users who reacted
            users = [user async for user in reaction.users() if not user.bot]
            break

    winner_count = active_giveaways[giveaway_msg.id]['winners']
    prize = active_giveaways[giveaway_msg.id]['prize']

    if len(users) < winner_count:
        await giveaway_msg.reply(f"Not enough participants for the giveaway for **{prize}**.")
    else:
        winners = random.sample(users, winner_count)
        winner_mentions = ' '.join([winner.mention for winner in winners])
        await giveaway_msg.reply(f"Congratulations {winner_mentions}! You won **{prize}**!")

    # Clean up the giveaway
    del active_giveaways[giveaway_msg.id]

@bot.command(name='sendonlinemsg')
@commands.has_permissions(administrator=True)
async def send_online_message(ctx, channel: discord.TextChannel):
    """
    Sets a channel to receive an "online" message whenever the bot restarts.
    """
    reminder_channels[ctx.guild.id] = channel.id
    embed = discord.Embed(
        title='Reminder Set',
        description=f'I will now send an "online" message to {channel.mention} after each restart.',
        color=discord.Color.green()
    )
    await ctx.send(embed=embed)

@bot.command(name='sendofflinemsg')
@commands.has_permissions(administrator=True)
async def send_offline_message(ctx, channel: discord.TextChannel):
    """
    This command doesn't actually work as intended because the bot can't send a message after it disconnects.
    It's included to show the technical limitation and to demonstrate how you might handle this.
    """
    embed = discord.Embed(
        title='Warning',
        description='I cannot send a message once I am offline. This command is not functional.',
        color=discord.Color.red()
    )
    await ctx.send(embed=embed)

@bot.command(name='ticketsetup')
@commands.has_permissions(administrator=True)
async def ticket_setup(ctx):
    """
    Sets up a ticket panel with a button.
    """
    embed = discord.Embed(
        title="Create a Ticket",
        description="Click the button below to create a support ticket.",
        color=discord.Color.dark_green()
    )

    view = discord.ui.View()
    style = discord.ButtonStyle.green
    button_label = "Create Ticket"

    # Create the button and its callback function
    async def ticket_callback(interaction: discord.Interaction):
        guild = interaction.guild
        member = interaction.user
        
        # Check if user already has an open ticket
        for panel_id in ticket_panels:
            for ticket_channel_id in ticket_panels[panel_id]:
                ticket_channel = bot.get_channel(ticket_channel_id)
                if ticket_channel and member in ticket_channel.overwrites:
                    await interaction.response.send_message("You already have an open ticket.", ephemeral=True)
                    return

        # Create the ticket channel
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            member: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True),
        }

        ticket_channel = await guild.create_text_channel(
            f"ticket-{member.name}", overwrites=overwrites
        )

        ticket_panels[interaction.message.id].append(ticket_channel.id)

        ticket_embed = discord.Embed(
            title="Ticket Created",
            description=f"Welcome {member.mention}! A staff member will be with you shortly. "
                        "To close this ticket, type `.close`.",
            color=discord.Color.green()
        )
        await ticket_channel.send(embed=ticket_embed)
        await interaction.response.send_message(f"Your ticket has been created at {ticket_channel.mention}", ephemeral=True)

    button = discord.ui.Button(label=button_label, style=style)
    button.callback = ticket_callback
    view.add_item(button)

    ticket_msg = await ctx.send(embed=embed, view=view)
    ticket_panels[ticket_msg.id] = []

@bot.command(name='close')
async def close_ticket(ctx):
    """
    Closes a ticket channel.
    """
    if not ctx.channel.name.startswith("ticket-"):
        return await ctx.send("This is not a ticket channel.")

    await ctx.channel.delete()

bot.run(BOT_TOKEN)

