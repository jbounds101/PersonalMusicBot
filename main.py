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
musicPlayer = None
musicCtx = None


class MusicPlayer:
    def __init__(self, ctx):
        self.MAX_VIDEO_LENGTH = 600  # in seconds -> 10 minutes
        self.current = None
        self.queue = []
        self.ctx = ctx
        self.player = self.ctx.voice_client

    def updateCtx(self, ctx):
        self.ctx = ctx

    async def addToQueue(self):
        if self.ctx.message.content is None:
            raise commands.CommandError('No media was specified.')
        query = self.ctx.message.content.split(' ', 1)[1]

        # Search YouTube for the video
        search = pytube.Search(query)

        i = 0
        while True:
            try:
                video = search.results[i]
                if video.length > self.MAX_VIDEO_LENGTH:
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

        fileName = "".join([c for c in video.title if c.isalpha() or c.isdigit() or c == ' ']).rstrip()
        " ".join(fileName.split())
        fileName += '.mp4'
        toDownload[0].download('Songs/', filename=fileName)
        self.queue.append((fileName, video))
        self.checkQueue()

    def checkQueue(self):
        if self.player.is_playing():
            return
        try:
            self.current = self.queue.pop()
        except IndexError:
            return self.destroy(self.ctx.guild)

        fileName = self.current[0]
        video = self.current[1]
        source = discord.FFmpegPCMAudio("Songs/" + fileName)
        self.playAudio(source)
        # source.cleanup()

    def playAudio(self, source):
        self.player.play(source, after=lambda x=None: self.checkQueue())

    async def showQueue(self):
        queueString = 'Current queue:\n'
        for elements in self.queue:
            queueString += elements[1].title
            queueString += '\n'
        await self.ctx.message.reply(queueString)

    def destroy(self, guild):
        return self.ctx.cog.cleanup(guild)


def getUserVoiceChannel(ctx):
    if ctx.author.voice is None:
        return None
    return ctx.author.voice.channel


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
    await ctx.invoke(bot.get_command('join'))
    global musicPlayer
    if musicPlayer is None:
        musicPlayer = MusicPlayer(ctx)
    musicPlayer.updateCtx(ctx)
    await musicPlayer.addToQueue()


@bot.command()
async def queue(ctx):
    if musicPlayer is None:
        await ctx.message.reply('The queue is empty.')
        return

    musicPlayer.updateCtx(ctx)
    await musicPlayer.showQueue()


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
