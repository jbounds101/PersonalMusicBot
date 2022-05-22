import os
import discord
import requests
import json

client = discord.Client()

key = os.environ['DISCORD_KEY']

def get_quote():
  response = requests.get('https://zenquotes.io/api/random')
  jsonData = json.loads(response.text)
  quote = jsonData[0]['q'] + ' -' + jsonData[0]['a']
  return(quote)

@client.event
async def on_ready():
  # Async, called when the bot is ready (calls automatically)
  print('We have logged in as {0.user}'.format(client))


@client.event
async def on_message(message):
  
  # Need to ignore self message
  if message.author == client.user:
    return

  msg = message.content

  if msg.startswith('!hello'):
    await message.channel.send('Hello friend!')

  if msg.startswith('!inspire'):
    await message.channel.send(get_quote())

  if msg.startswith('!join') or msg.startswith('!connect'):
    await discord.VoiceProtocol(client, discord.VoiceChannel)

client.run(key)

