from libneko.extras.help import Help


def setup(bot):
    bot.remove_command("help")
    bot.add_cog(Help(dm=True))
