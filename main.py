import os
import discord
import requests

client = discord.Client()
key = os.environ['DISCORD_KEY']

@client.event
async def on_ready():
  # Async, called when the bot is ready (calls automatically)
  print('We have logged in as {0.user}'.format(client))


@client.event
async def on_message(message):
  # Need to ignore self message
  if message.author == client.user:
    return

  if message.content.startswith('!hello'):
    await message.channel.send('Hello friend!')

client.run(key)

