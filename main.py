import asyncio
import os
import discord
import requests
import json
import spotipy
import webbrowser
from discord.ext import commands


bot = commands.Bot(command_prefix='!')

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
    #await ctx.voice_client.cleanup()

@bot.command()
async def sound(ctx):
    await ctx.invoke(bot.get_command('join'))
    source = discord.PCMVolumeTransformer(discord.FFmpegPCMAudio('song.mp3'))
    ctx.voice_client.play(source, after=lambda e: print('Player error: %s' % e) if e else None)


bot.run(os.getenv('DISCORD_TOKEN'))
