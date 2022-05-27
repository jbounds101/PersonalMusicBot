import os
import discord
import random
import requests
import json
import pytube
import pytube.exceptions
from discord.ext import commands


bot = commands.Bot(command_prefix='!')
audioQueue = []

def getUserVoiceChannel(ctx):
    if ctx.author.voice is None:
        return None
    return ctx.author.voice.channel

def playFromAudioQueue(ctx):



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
    toDownload[0].download('Songs/', filename=(query + '.mp4'))


    source = discord.FFmpegPCMAudio("Songs/" + query + '.mp4')
    try:
        ctx.voice_client.play(source, after=playFromAudioQueue(ctx))
    except discord.ClientException:
        pass
        # TODO add handling for already playing music
    await ctx.send('>>> Now playing: `{}`'.format(video.title))

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
