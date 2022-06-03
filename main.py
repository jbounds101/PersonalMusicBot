import asyncio
import math
import os
import re
import aiohttp
import discord
import random
import requests
import time
import json
import pytube
import pytube.exceptions
import tempfile
import shutil
from discord.ext import commands

bot = commands.Bot(command_prefix='!')
musicPlayer = None
musicCtx = None

class MusicPlayer:
    def __init__(self, ctx):
        self.MAX_VIDEO_LENGTH = 600  # in seconds -> 10 minutes
        self.current = {'filename': None, 'video': None, 'sendGif': False}
        self.source = None
        self.currentStartTime = time.time()
        self.pauseStart = 0
        self.currentPauseTime = 0
        self.queue = []
        self.ctx = ctx
        self.player = self.ctx.voice_client
        self.songsDir = tempfile.mkdtemp()

    def updateCtx(self, ctx):
        self.ctx = ctx

    async def addToQueue(self, sendGif):
        if self.ctx.message.content is None:
            raise commands.CommandError('No media was specified.')
        query = self.ctx.message.content.split(' ', 1)[1]

        toDownload = None
        if MusicPlayer.isURL(query):
            # This is a link to a video
            try:
                video = pytube.YouTube(query)
                stream = pytube.YouTube(video.watch_url)
                toDownload = stream.streams.filter(only_audio=True)
            except (pytube.exceptions.RegexMatchError or pytube.exceptions.VideoPrivate or
                    pytube.exceptions.VideoUnavailable):
                # TODO probably need to catch more errors
                # Check if the query is a playlist
                if 'playlist' in query:
                    try:
                        playlist = pytube.Playlist(query)
                        for video in playlist.videos:
                            filename_ = "".join(
                                [c for c in video.title if c.isalpha() or c.isdigit() or c == ' ']).rstrip()
                            filename_ = re.sub(' +', ' ', filename_)
                            filename_ += '.mp4'
                            print("added {}".format(filename_))
                            self.queue.append(
                                {'filename': filename_, 'video': video, 'sendGif': sendGif})
                        await self.checkQueue()
                        return
                    except (pytube.exceptions.RegexMatchError or pytube.exceptions.VideoPrivate or
                            pytube.exceptions.VideoUnavailable):
                        # Query was a playlist, but didn't return any results (likely incorrect URL)
                        await self.ctx.message.reply('Given playlist link returned no results.')
                        raise commands.CommandError('HANDLED')
                else:
                    # The query wasn't a playlist and the link returned no result
                    await self.ctx.message.reply('Given link returned no results.')
                    raise commands.CommandError('HANDLED')
        else:
            # Search YouTube for the video
            search = pytube.Search(query)
            i = 0
            while True:
                try:
                    video = search.results[i]
                    if (video.length > self.MAX_VIDEO_LENGTH) or (video.length == 0):
                        i += 1
                        continue
                    break
                except IndexError:
                    # Ran out of search results
                    await self.ctx.message.reply('No results were found.')
                    raise commands.CommandError('HANDLED')

        filename_ = "".join([c for c in video.title if c.isalpha() or c.isdigit() or c == ' ']).rstrip()
        filename_ = re.sub(' +', ' ', filename_)
        filename_ += '.mp4'
        await self.ctx.message.reply('Added to queue: `' + video.title + '`')
        self.queue.append(
            {'filename': filename_, 'video': video, 'sendGif': sendGif})
        await self.checkQueue()

    async def checkQueue(self):
        if (self.source is not None) and (not self.player.is_playing()) and (not self.player.is_paused()):
            # Clean up after song end
            self.source.cleanup()
            current_ = self.songsDir + '/' + self.current['filename']
            os.remove(current_)
            self.source = None
        try:
            self.current = self.queue.pop(0)
            self.pauseStart = 0
            self.currentPauseTime = 0
        except IndexError:
            self.source = None
            return await self.destroy()
        await self.playAudio()

    async def playAudio(self):
        video = self.current['video']
        stream = pytube.YouTube(video.watch_url)
        toDownload = stream.streams.filter(only_audio=True)
        fileName = self.current['filename']
        toDownload[0].download(self.songsDir, filename=fileName)
        source = discord.FFmpegPCMAudio(self.songsDir + '/' + fileName)

        self.source = source
        self.currentStartTime = time.time()
        # TODO Error with positional args here
        self.player.play(source, after=lambda: asyncio.run_coroutine_threadsafe(
            self.checkQueue(), bot.loop))
        await self.ctx.send('>>> Now playing: `' + video.title + '`')

        if self.current['sendGif'] is True:
            # Send a gif with 'Now playing: '
            await giphySendGif(self.ctx, video.title)

    async def showQueue(self):
        video = self.current['video']
        assert video is not None
        isAre = 'are'
        sAdd = 's'
        if len(self.queue) == 1:
            isAre = 'is'
            sAdd = ''
        queueString = 'There {} **{}** song{} in the queue.\n'.format(isAre, len(self.queue), sAdd)
        queueString += '```Current: {} | ({} / {})\n\n'.format(video.title, self.getCurrentTimestamp(),
                                                              MusicPlayer.getVideoLength(video))
        i = 1
        for element in self.queue:
            video = element['video']
            toAdd = '{}: {} | ({})\n'.format(i, video.title, MusicPlayer.getVideoLength(video))
            i += 1
            if (len(toAdd) + len(queueString)) > 1950:
                # String is going to be too long with this addition
                queueString += '> and {} more...'.format(len(self.queue) + 2 - i)
                break
            queueString += toAdd
        queueString += '```'
        await self.ctx.message.reply(queueString)

    def pause(self):
        if self.player.is_paused():
            # Unpause when pause is used when already paused
            return self.resume()
        self.player.pause()
        self.pauseStart = time.time()

    def resume(self):
        if self.player.is_playing():
            return
        self.player.resume()
        pauseTime = (time.time() - self.pauseStart)
        self.currentPauseTime += pauseTime
        self.pauseStart = 0

    async def skip(self):
        self.player.stop()
        await self.checkQueue()

    def getCurrentTimestamp(self):
        endTime = time.time()
        if self.pauseStart == 0:
            timeInSeconds = (endTime - self.currentStartTime) - self.currentPauseTime
        else:
            timeInSeconds = (endTime - self.currentStartTime) - (endTime - self.pauseStart) - self.currentPauseTime
        return MusicPlayer.convertToTimeStamp(timeInSeconds)

    def shuffle(self):
        random.shuffle(self.queue)

    #async def

    @staticmethod
    def getVideoLength(video):
        timeInSeconds = video.length
        return MusicPlayer.convertToTimeStamp(timeInSeconds)

    @staticmethod
    def convertToTimeStamp(timeInSeconds):
        minutes = math.floor(timeInSeconds / 60)
        seconds = int(timeInSeconds % 60)
        return "{}:{}".format(str(minutes), str(seconds).zfill(2))  # zfill places leading zeroes in front
        # of string

    @staticmethod
    def isURL(query):
        if '.com' in query or 'http' in query:
            return True
        else:
            return False

    async def destroy(self):
        global musicPlayer
        if musicPlayer is None:
            # Already deleted, return (calls after checkQueue() from audio ending)
            return
        musicPlayer = None
        if self.player.is_playing():
            self.player.stop()
        if os.path.exists(self.songsDir):
            while self.source is not None:
                # Need to ensure that the current source is removed before deleting the file
                time.sleep(.25)
            shutil.rmtree(self.songsDir)
            print('Path {} successfully removed'.format(self.songsDir))
        await self.player.disconnect()


def getUserVoiceChannel(ctx):
    if ctx.author.voice is None:
        return None
    return ctx.author.voice.channel

async def giphySendGif(ctx, query):
    # This needs to include 'query' since ctx.message.content may not be what we need to search (MusicPlayer)
    embed = discord.Embed(colour=discord.Colour.purple())
    session = aiohttp.ClientSession()
    query.replace(' ', '+')
    query = query[:50]  # Max length of a search query is 50 characters
    response = await session.get(
        'http://api.giphy.com/v1/gifs/search?q=' + query + '&api_key=' + os.getenv('GIPHY_API_KEY') + '&limit=10')
    data = json.loads(await response.text())
    gifChoice = random.randint(0, 9)
    embed.set_image(url=data['data'][gifChoice]['images']['original']['url'])
    await session.close()
    if response.ok is False:
        return
    await ctx.channel.send(embed=embed)

@bot.after_invoke
async def reactOnSuccess(ctx):
    if not ctx.command_failed:
        await ctx.message.add_reaction('✅')

@bot.event
async def on_ready():
    print('Logged in as {0.user}'.format(bot))

@bot.event
async def on_command_error(ctx, error):
    await ctx.message.add_reaction('❌')
    if str(error) == 'HANDLED':
        # This is a handled error, just add 'X', this could be the result of something like a search not finding a
        # result, usually reserved for more specific command usage, such as using !play when in a voice channel
        return

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
        await ctx.message.reply('**Invalid command usage!** You must be connected to a voice channel.')
        raise commands.CommandError('HANDLED')
    if ctx.voice_client is not None:
        return await ctx.voice_client.move_to(voiceChannel)
    await voiceChannel.connect()

@bot.command()
async def leave(ctx):
    if musicPlayer is None:
        await ctx.voice_client.disconnect()
    else:
        await musicPlayer.destroy()

# Copy of 'leave'
@bot.command()
async def quit(ctx):
    await ctx.invoke(bot.get_command('leave'))

@bot.command()
async def play(ctx, sendGif_):
    await ctx.invoke(bot.get_command('join'))
    global musicPlayer
    if musicPlayer is None:
        # Create musicPlayer if it doesn't exist
        musicPlayer = MusicPlayer(ctx)

    if sendGif_ is not True:
        sendGif_ = False
        # sendGif_ is the message given by default, over-ridden with playi

    musicPlayer.updateCtx(ctx)
    await musicPlayer.addToQueue(sendGif_)

# Copy of 'play'
@bot.command()
async def p(ctx):
    await ctx.invoke(bot.get_command('play'), False)

@bot.command()
async def playi(ctx):
    await ctx.invoke(bot.get_command('play'), True)

# Copy of 'playi'
@bot.command()
async def pi(ctx):
    await ctx.invoke(bot.get_command('play'), True)

@bot.command()
async def queue(ctx):
    if musicPlayer is None:
        await ctx.message.reply('The queue is empty.')
        return
    musicPlayer.updateCtx(ctx)
    await musicPlayer.showQueue()

# Copy of 'queue'
@bot.command()
async def q(ctx):
    await ctx.invoke(bot.get_command('queue'))

@bot.command()
async def pause(ctx):
    if musicPlayer is None:
        await ctx.message.reply('There is nothing to pause.')
        return
    musicPlayer.pause()

@bot.command()
async def resume(ctx):
    if musicPlayer is None:
        await ctx.message.reply('There is nothing to resume.')
        return
    musicPlayer.resume()

# Copy of 'resume'
@bot.command()
async def unpause(ctx):
    await ctx.invoke(bot.get_command('resume'))

@bot.command()
async def skip(ctx):
    if musicPlayer is None:
        await ctx.message.reply('There is nothing to skip.')
        return
    await musicPlayer.skip()

# Copy of 'skip'
@bot.command()
async def s(ctx):
    await ctx.invoke(bot.get_command('skip'))

@bot.command()
async def shuffle(ctx):
    if musicPlayer is None:
        await ctx.message.reply('There is no queue.')
        return
    musicPlayer.shuffle()


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
