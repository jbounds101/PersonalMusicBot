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

  if message.content.startswith('!hello'):
    await message.channel.send('Hello friend!')

  if message.content.startswith('!inspire'):
    await message.channel.send(get_quote())

client.run(key)

