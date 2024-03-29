import asyncio
import os
import random
import sys

import nextcord
import youtube_dl
from nextcord.ext import commands, tasks

# variables setup

currently_playing = ""
vc_queue = []
playing = False
object_queue = []
counter = 0

# initial bot setup

intents = nextcord.Intents.default()
intents.message_content = True
activity = nextcord.Activity(name="YOU", type=nextcord.ActivityType.watching, state="watching YOU")
bot = commands.Bot(command_prefix="~", intents=intents, activity=activity)

# Suppress noise about console usage from errors
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

ffmpeg_options = {"options": "-vn"}

ytdl = youtube_dl.YoutubeDL(ytdl_format_options)


# class that mike does not understand YET
class YTDLSource(nextcord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=1):
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


@bot.event
async def on_message(message):
    # debugging
    print(f'[DEBUGGING] {message.author} sent {message.content}')

    await bot.process_commands(message)


# signal that the bot is online
@bot.event
async def on_ready():
    print(f"[INFO] started successfully!")
    print(f"[INFO] Logged in as {bot.user} (ID: {bot.user.id})")
    print(f"[INFO] Activity is: {bot.activity}")


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
        return 0

    await ctx.reply("OK, Connected!")


# play audio command
@bot.command()
async def play(ctx, *, url, ytdl_obj=None):
    """plays(streams) something in the voice channel"""
    global currently_playing, vc_queue, object_qeueu
    if url is None:
        called = True
        source = ytdl_obj
    else:
        called = False
    if not ctx.voice_client.is_playing():
        try:
            async with ctx.typing():
                if not called:
                    source = await YTDLSource.from_url(url, loop=bot.loop, stream=True)

                    ctx.voice_client.play(
                        source, after=lambda e: print(f"Player error: {e}") if e else None
                    )
                else:
                    ctx.voice_client.play(
                        source, after=lambda e: print(f"Player error: {e}") if e else None
                    )

            await ctx.send(f"Now playing: {source.title}")
            await asyncio.sleep(1.2)
            try:
                try:
                    vc_queue_method.stop()
                except RuntimeError:
                    None
                vc_queue_method.start(ctx)
            except RuntimeError:
                try:
                    vc_queue_method.stop()
                    vc_queue_method.start(ctx)
                except RuntimeError:
                    None

        except nextcord.errors.ClientException or not ctx.voice_client.is_playing():
            await ctx.send(f"Already playing: {currently_playing}")
            return 0

    else:
        await ctx.send(f"Already playing: {currently_playing}")
        async with ctx.typing():
            audio = await YTDLSource.from_url(url, loop=bot.loop, stream=True)
            vc_queue.append(audio.title)
            object_queue.append(audio)
            await ctx.send(f"added {audio.title} to queue")
        return 0

    vc_queue.append(source.title)
    currently_playing = source.title
    ctx.voice_client.is_playing()


# stop playing audio
@bot.command()
async def stop(ctx, called=False):
    """STOPS playing ALL audio and clears queue"""
    global playing
    if called:
        called = True
    else:
        called = False
    try:
        await ctx.voice_client.stop()
    except:
        print("[DEBUGGING] stopped playing audio")
    playing = False
    if not called:
        await ctx.reply("OK, stopped playing audio!")


# skip function to the bot
@bot.command()
async def skip(ctx):
    global vc_queue, object_queue
    await stop(context=ctx, called=True)


    await play(context=ctx, url=None, ytdl_obj=object_queue[1])
    object_queue.pop(0)
    vc_queue.pop(0)
    await ctx.reply("OK, skipped the song")

    return 0


@bot.command()
async def pause(ctx):
    if ctx.voice_client.is_paused():
        try:
            await ctx.voice_client.resume()
        except:
            print("[DEBUGGING] resumed playing audio")
    else:
        try:
            await ctx.voice_client.pause()
        except:
            print("[DEBUGGING] paused playing audio")


# queue command
@bot.command()
async def queue(ctx):
    global vc_queue, currently_playing, object_queue
    titles = []
    count = 0
    for i in vc_queue:
        titles.append(f"{i}\n")
        count += 1
    titles.pop(0)

    if str(ctx.author) == "supermikea#5051":
        await ctx.reply(f"[DEBUG] {str(object_queue)}")

    await ctx.reply(f"current queue: {titles}")


@tasks.loop(seconds=1)  # task runs every 2 seconds
async def vc_queue_method(ctx):
    try:
        global object_queue, vc_queue
        if not ctx.voice_client.is_playing():
            try:
                await play(context=ctx, url=None, ytdl_obj=object_queue[0])
            except IndexError:
                return 0

            object_queue.pop(0)
            vc_queue.pop(0)
            return 0
    except RuntimeError as e:  # is expected (this is absolutely horrible)
        None
        ctx.send(f"```[DEBUG] ALERT @supermikea#5051 GOT A RuntimeError, (I`m sorry dude). But anyway here are the details:\n\n\n{e}```")
        return 0


# bot initiation code
def write_read_f(option, token, location):  # write or read token from token file
    if option == "w":
        file = open(sys.path[0] + location, "w")
        file.write(token)
        file.close()
        return 0
    # if option is not True then this is automatically executed
    file = open(sys.path[0] + location, "r")
    r_token = file.read()
    file.close()
    return r_token


token = write_read_f("r", 0, "/token")

try:
    if sys.argv[1] == "Restarted":
        restarted = True
except IndexError:
    restarted = False
    print("[INFO] First turn on!")

print("[INFO] Trying to start bot...")
bot.run(token)

# ctrl+c only exits the bot.run instance, we can assume an exit signal is received and say goodbye!
print("\n[INFO] exit signal received! GOODBYE!")
