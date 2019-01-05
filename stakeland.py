import discord
from discord.ext.commands import Bot
import os


BOT_PREFIX = os.environ['prefix']  # -Prfix is need to declare a Command in discord ex: !pizza "!" being the Prefix
TOKEN = os.environ['token']  # The token is also substituted for security reasons


bot = Bot(command_prefix=BOT_PREFIX, case_insensitive=True)
client = discord.Client()


bot.load_extension("libneko.extras.superuser")
bot.load_extension("libneko.extras.help")
bot.run(TOKEN)
# https://discordapp.com/oauth2/authorize?client_id=502940842143514633&scope=bot&permissions=0
