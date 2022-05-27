import asyncio
import os
import discord
import random
import requests
import json
import pytube
import pytube.exceptions
from discord.ext import commands
from async_timeout import timeout

bot = commands.Bot(command_prefix='!')
music = None

class MusicPlayer:
    def __init__(self, ctx):
        self.bot = ctx.bot
        self.guild = ctx.guild
        self.channel = ctx.channel
        self.cog = ctx.cog

        self.queue = asyncio.Queue()
        self.next = asyncio.Event()

        self.np = None  # Now playing message
        self.current = None
        self.audioQueue = None

        ctx.bot.loop.create_task(self.audio_loop())

    async def audio_loop(self):
        await self.bot.wait_until_ready()

        while not self.bot.is_closed():
            self.next.clear()

            try:
                # Wait for the next song. If we timeout cancel the player and disconnect...
                async with timeout(300):  # 5 minutes...
                    temp = self.audioQueue.pop()
            except asyncio.TimeoutError:
                    return self.destroy(self.guild)
            fileName = temp[0]
            video = temp[1]
            source = discord.FFmpegPCMAudio("Songs/" + fileName)

            self.guild.voice_client.play(source, after=lambda _: self.bot.loop.call_soon_threadsafe(self.next.set))
            self.np = await self.channel.send('yo')

            await self.next.wait()

            # Make sure the FFmpeg process is cleaned up.
            source.cleanup()
            self.current = None

    def destroy(self, guild):
        """Disconnect and cleanup the player."""
        return self.bot.loop.create_task(self.cog.cleanup(guild))

def getUserVoiceChannel(ctx):
    if ctx.author.voice is None:
        return None
    return ctx.author.voice.channel

"""async def playFromAudioQueue(ctx):
    if len(audioQueue) <= 0:
        return
    popped = audioQueue.pop()
    fileName = popped[0]
    video = popped[1]
    ctx.voice_client.play(, after=lambda ex: asyncio.get_event_loop().create_task(
        playFromAudioQueue(ctx)))
    await ctx.send('>>> Now playing: `{}`'.format(video.title))"""


@bot.after_invoke
async def reactOnSuccessFail(ctx):
    if ctx.command_failed:
        await ctx.message.add_reaction('❌')
        return
    await ctx.message.add_reaction('✅')

@bot.event
async def on_ready():
    print('Logged in as {0.user}'.format(bot))



@bot.event
async def on_command_error(ctx, error):

    print('***Error*** (' + ctx.message.content + '):\t' + str(error))
    if isinstance(error, commands.CommandNotFound):
        await ctx.message.reply('**Invalid command!** Use __!help__ to list possible commands.')
    else:
        await ctx.message.reply('**Invalid command usage!** Use __!help__ to list proper usage.')


# ---Commands---
@bot.command()
async def echo(ctx, *, arg):

    await ctx.message.reply(arg)

@bot.command()
async def add(ctx, a: int, b: int):  # converts a and b to ints during invoke
    if a == 9 and b == 10:
        a = 11  # 9 + 10 = 21
    await ctx.message.reply(a + b)


@bot.command()
async def whereAmI(ctx):
    if getUserVoiceChannel(ctx) is None:
        return await ctx.message.reply('You are not in a voice channel currently.')
    await ctx.message.reply(getUserVoiceChannel(ctx))


@bot.command()
async def join(ctx):
    voiceChannel = getUserVoiceChannel(ctx)
    if voiceChannel is None:
        raise commands.CommandError('You are not connected to a voice channel.')

    if ctx.voice_client is not None:
        return await ctx.voice_client.move_to(voiceChannel)
    await voiceChannel.connect()

@bot.command()
async def leave(ctx):
    await ctx.voice_client.disconnect()

@bot.command()
async def play(ctx):
    MAX_VIDEO_LENGTH = 600  # in seconds -> 10 minutes
    if ctx.message.content is None:
        raise commands.CommandError('No media was specified.')
    await ctx.invoke(bot.get_command('join'))
    query = ctx.message.content.split(' ', 1)[1]

    # Search YouTube for the video
    search = pytube.Search(query)

    i = 0
    while True:
        try:
            video = search.results[i]
            if video.length > MAX_VIDEO_LENGTH:
                i += 1
                continue
            stream = pytube.YouTube(video.watch_url)
            toDownload = stream.streams.filter(only_audio=True)
            break
        except pytube.exceptions.LiveStreamError:
            # Video is a live stream
            i += 1
        except IndexError:
            # Ran out of search results
            raise commands.CommandError('No results were found.')


    toDownload[0].download('Songs/', filename=(video.title + '.mp4'))
    fileName = video.title + '.mp4'
    global music
    if music is None:
        music = MusicPlayer(ctx)
    music.audioQueue.append((fileName, video))
    await ctx.message.reply('Added to queue: `{}`'.format(video.title))
    #if len(music.audioQueue) == 1 and not ctx.voice_client.is_playing():


@bot.command()
async def randomMsg(ctx):
    messages = await ctx.channel.history(limit=100).flatten()
    selected = random.choice(messages)
    await selected.reply('This message is from ---')
    # TODO overhaul this


@bot.command()
async def fox(ctx):
    response = requests.get('https://randomfox.ca/floof').json()
    await ctx.message.reply(response.get('image'))



bot.run(os.getenv('DISCORD_TOKEN'))
