from nextcord.ext import tasks, commands
import nextcord

import os
import sys
import random
import asyncio

import youtube_dl

# youtube dl setup

youtube_dl.utils.bug_reports_message = lambda: ""

ytdl_format_options = {
    "format": "bestaudio/best",
    "outtmpl": "%(extractor)s-%(id)s-%(title)s.%(ext)s",
    "restrictfilenames": True,
    "noplaylist": True,
    "nocheckcertificate": True,
    "ignoreerrors": False,
    "logtostderr": False,
    "quiet": True,
    "no_warnings": True,
    "default_search": "auto",
    "source_address": "0.0.0.0",  # bind to ipv4 since ipv6 addresses cause issues sometimes
}

ytdl = youtube_dl.YoutubeDL(ytdl_format_options)

ffmpeg_options = {"options": "-vn"}

class YTDLSource(nextcord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)

        self.data = data

        self.title = data.get("title")
        self.url = data.get("url")

    @classmethod
    async def from_url(cls, url, *, loop=None, stream=False):
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=not stream))

        if "entries" in data:
            # take first item from a playlist
            data = data["entries"][0]

        filename = data["url"] if stream else ytdl.prepare_filename(data)
        return cls(nextcord.FFmpegPCMAudio(filename, **ffmpeg_options), data=data)

# initial bot setup

intents = nextcord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="~", intents=intents)


@bot.event
async def on_message(message):
    # debugging
    print(f'[DEBUGGING] {message.author} sended {message.content}')

    await bot.process_commands(message)


# signal that the bot is online
@bot.event
async def on_ready():
    print(f"[INFO] started succesfully!")
    print(f"[INFO] Logged in as {bot.user} (ID: {bot.user.id})")


# ping-pong command
@bot.slash_command(description="Replies with pong!")
async def ping(interaction: nextcord.Interaction):
    await interaction.send("Pong!", ephemeral=True)


# simple hello command
@bot.command()
async def hello(ctx):
    message = ctx.message
    await message.add_reaction('\U0001F44D')  # thumbs up reaction
    await ctx.reply("Hello!")


# restart the bot
@bot.command()
async def restart(ctx):
    if str(ctx.author) == "supermikea#5051":
        if restarted:
            await ctx.reply(f"OK, Restarting again...")
            os.system('python3 restart.py')
            sys.exit(0)
            return 0
        await ctx.reply("OK, Restarting...")
        os.system('python3 restart.py')
        sys.exit(0)
        return 0
    else:
        await ctx.reply("https://tenor.com/view/no-way-dude-no-oh-bugs-bunny-bugs-gif-22941840")


# turn off the bot
@bot.command()
async def shutdown(ctx):
    if str(ctx.author) == "supermikea#5051":
        await ctx.reply("OK, GoodBye!")
        sys.exit(0)
    else:
        await ctx.reply("https://tenor.com/view/no-way-dude-no-oh-bugs-bunny-bugs-gif-22941840")


# roll command
@bot.command()
async def roll(ctx, *limit: str):
    try:
        await ctx.send(random.randint(0, int(limit[0])))
    except IndexError:
        await ctx.send(random.randint(0, 100))


# repeat command
@bot.command()
async def repeat(ctx, times: int, content="repeating..."):
    """Repeats a message multiple times."""
    for _ in range(times):
        await ctx.send(content)


# join voice channel
@bot.command()
async def join(ctx, *more: str):
    """joins voice channel"""

    await ctx.reply("OK, Joining...")

    initiator = ctx.author
    initiator_vc = initiator.voice
    vc = initiator_vc.channel
    try:
        await vc.connect()
    except nextcord.errors.ClientException:
        await ctx.send("I'm already connected u dummy")

    await ctx.reply("OK, Connected!")


# play audio command
@bot.command()
async def play(ctx, *, url):
    """plays something in the voice channel"""
    async with ctx.typing(): # dit waarscheinlijk anders maken cause mike does not understand it completely
        source = await YTDLSource.from_url(url, loop=bot.loop)
        ctx.voice_client.play(
            source, after=lambda e: print(f"Player error: {e}") if e else None
        )

    await ctx.send(f"Now playing: {source.title}")

@bot.command()
async def stop(ctx):
	await ctx.voice_client.stop()
	await ctx.reply("OK, stopped playing audio!")

# bot initiation code
def write_read_f(option, token, location):  # write or read token from token file
    if option == "w":
        file = open(sys.path[0] + location, "w")
        file.write(token)
        file.close()
        return 0
    # if option is not True then this is automatically executed
    file = open(sys.path[0] + location, "r")
    token = file.read()
    file.close()
    return token


token = write_read_f("r", 0, "/token")

try:
    if sys.argv[1] == "Restarted":
        restarted = True
except IndexError:
    restarted = False
    print("[INFO] First turn on!")

print("[INFO] Trying to start bot...")
bot.run(token)

# ctrl+c only exits the bot.run instance, we can assume a exit signal is received and say goodbye!
print("\n[INFO] exit signal received! GOODBYE!")
