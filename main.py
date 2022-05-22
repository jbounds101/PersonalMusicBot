import os
import discord
import requests
import json

client = discord.Client()
voiceClient = client.voice_clients

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

  voiceClient = client.voice_clients

  user = message.author
  userMsg = message.content
  userTextChannel = message.channel
  userID = user.id
  userVoiceClient = None

  print(len(voiceClient))

  for voiceUser in voiceClient:
    if voiceUser.id == userID:
      userVoiceClient = voiceUser
      print('User is in a voice channel')
  
  if userMsg.startswith('!hello'):
    await userTextChannel.send('Hello friend!')

  if userMsg.startswith('!inspire'):
    await userTextChannel.send(get_quote())



client.run(key)

