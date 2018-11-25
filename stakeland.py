import discord
from discord.ext import commands
from discord.ext.commands import Bot
import os
import asyncpg
import ssl
import secrets
import json
from datetime import datetime, timedelta
from pytz import timezone
from decimal import Decimal
import asyncio
import operator
import time
import random_number as hasher
import logging
logging.basicConfig(level='INFO')

# import matplotlib
# matplotlib.use('Agg')
# import matplotlib.pyplot as plt
# from io import BytesIO


BOT_PREFIX = os.environ['prefix']  # -Prfix is need to declare a Command in discord ex: !pizza "!" being the Prefix
TOKEN = os.environ['token']  # The token is also substituted for security reasons
DATABASE_URL = os.environ['DATABASE_URL']
rs3_osrs_rate = Decimal(os.environ['rs3_osrs_rate'])
osrs_rs3_rate = Decimal(os.environ['osrs_rs3_rate'])
back_card = "<:backcard:509135629301579787>"


bot = Bot(command_prefix=BOT_PREFIX, case_insensitive=True)
client = discord.Client()


current_dd_games = []
current_swaps = []
current_flower_games = []
current_bj_games = []
current_high_low_games = []
jackpot_pot = 0
jackpot_users = []
is_current_jackpot = False
jackpot_currency = "07"
more_than_one = False

# real
# stakeland_public = 478073843823673362
# stakeland_seed = 510263062293512192

# test
stakeland_public = 405118958446968839
stakeland_seed = 405118958446968839

cards_json = []
client_seed = ""
server_seed = ""
server_seed_hash = ""
nonce = 0


@bot.listen()
async def on_connect():
    ctx = ssl.create_default_context(cafile='./rds-combined-ca-bundle.pem')
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    bot.db = await asyncpg.create_pool(DATABASE_URL, ssl=ctx)
    # async with bot.db.acquire() as conn:
    #     await conn.execute('''
    #         CREATE TABLE IF NOT EXISTS rsmoney (
    #         id BIGINT PRIMARY KEY,
    #         rs3 BIGINT NOT NULL CHECK (rs3 >= 0),
    #         osrs BIGINT NOT NULL CHECK (osrs >= 0),
    #         total_rs3_bet BIGINT NOT NULL CHECK (total_rs3_bet >= 0),
    #         total_osrs_bet BIGINT NOT NULL CHECK (total_osrs_bet >= 0),
    #         total_osrs_weekly BIGINT NOT NULL CHECK (total_osrs_weekly >= 0),
    #         total_rs3_weekly BIGINT NOT NULL CHECK (total_rs3_weekly >= 0),
    #         bets BIGINT NOT NULL DEFAULT 0 CHECK (bets >= 0),
    #         privacy BOOLEAN NOT NULL
    #         )
    #     ''')
    # async with bot.db.acquire() as conn:
    #     await conn.execute('''
    #         CREATE TABLE IF NOT EXISTS server (
    #         profit_osrs BIGINT NOT NULL DEFAULT 2262,
    #         profit_rs3 BIGINT NOT NULL DEFAULT 116202,
    #         profit_osrs_total BIGINT NOT NULL DEFAULT 2262,
    #         profit_rs3_total BIGINT NOT NULL DEFAULT 116202,
    #         server_seed varchar(128),
    #         server_seed_hash varchar(128),
    #         client_seed varchar(128)
    #         )
    #     ''')


# staky
def is_staky(ctx):
    return ctx.author.id == 424233412673536000 or ctx.author.id == 209081432956600320


def is_stakeland(ctx):
    return ctx.message.guild.id == 419994398122704896


async def add_member(user_id: int, rs3: int, osrs: int):
    async with bot.db.acquire() as conn:
        await conn.execute('''
        INSERT INTO rsmoney (id,rs3,osrs,total_rs3_bet,total_osrs_bet,total_osrs_weekly,total_rs3_weekly,privacy) 
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8)''', user_id, rs3, osrs, 0, 0, 0, 0, False)


async def get_value(user_id: int, value: str):
    if value == "07":
        value = "osrs"
    async with bot.db.acquire() as conn:
        returned = await conn.fetchrow("SELECT * FROM rsmoney WHERE id=$1", user_id)

    if returned is None:
        await add_member(user_id, 0, 10)
        async with bot.db.acquire() as conn:
            returned = await conn.fetchrow("SELECT * FROM rsmoney WHERE id=$1", user_id)

    return returned[value]


async def update_money(user_id: int, amount: int, currency: str):
    if currency == "07":
        currency = "osrs"
    async with bot.db.acquire() as conn:
        returned = await conn.fetchrow("SELECT * FROM rsmoney WHERE id=$1", user_id)

    if returned is None:
        await add_member(user_id, 0, 10)

    async with bot.db.acquire() as conn:
        if currency == "osrs":
            await conn.execute("UPDATE rsmoney SET osrs = osrs + $1 WHERE id=$2", amount, user_id)
        elif currency == "rs3":
            await conn.execute("UPDATE rsmoney SET rs3 = rs3 + $1 WHERE id=$2", amount, user_id)
        elif currency == "total_rs3_bet":
            await conn.execute("UPDATE rsmoney SET total_rs3_bet = total_rs3_bet + $1 WHERE id=$2", amount, user_id)
        elif currency == "total_osrs_bet":
            await conn.execute("UPDATE rsmoney SET total_osrs_bet = total_osrs_bet + $1 WHERE id=$2", amount, user_id)
        elif currency == "total_osrs_weekly":
            await conn.execute("UPDATE rsmoney SET total_osrs_weekly = total_osrs_weekly + $1 WHERE id=$2",
                               amount, user_id)
        elif currency == "total_rs3_weekly":
            await conn.execute("UPDATE rsmoney SET total_rs3_weekly = total_rs3_weekly + $1 WHERE id=$2",
                               amount, user_id)
        elif currency == "profit_osrs":
            await conn.execute("UPDATE server SET profit_osrs = profit_osrs + $1", amount)
            async with bot.db.acquire() as con:
                await con.execute("UPDATE server SET profit_osrs_total = profit_osrs_total + $1", amount)
        elif currency == "profit_rs3":
            await conn.execute("UPDATE server SET profit_rs3 = profit_rs3 + $1", amount)
            async with bot.db.acquire() as con:
                await con.execute("UPDATE server SET profit_rs3_total = profit_rs3_total + $1", amount)
        elif currency == "bets":
            await conn.execute("UPDATE rsmoney SET bets = bets + $1 WHERE id=$2", amount, user_id)


def formatok(amount: str):
    if (amount[-1:]).lower() == "m":
        return int(Decimal(amount[:-1]) * 100)
    elif (amount[-1:]).lower() == "k":
        return int(Decimal(amount[:-1]) / 10)
    elif (amount[-1:]).lower() == "b":
        return int(Decimal(amount[:-1]) * 100_000)
    else:
        return int(Decimal(amount) * 100)


def formatfromk(amount: int):
    amount = round((amount * 0.01), 2)

    if isinstance(amount, Decimal):
        if amount.is_integer():
            amount = int(amount)
    return str(amount)+"M"


def is_enough(amount: int, currency: str):
    if currency != "rs3" and currency != "07":
        return
    if (currency == "rs3" and amount < 100) or (currency == "07" and amount < 10):
        return False
    return True


async def not_enough_funds(ctx, name):
    embed = discord.Embed()
    embed.set_author(name=name)
    embed.add_field(name="Error", value="You don't have enough balance.")
    return await ctx.send(embed=embed)


async def not_enough(ctx, name, currency):
    embed = discord.Embed()
    embed.set_author(name=name)
    if currency == "rs3":
        embed.add_field(name="Error", value="The minimum bet is 1m RS3.")
    elif currency == "07":
        embed.add_field(name="Error", value="The minimum bet is 100k 07.")
    return await ctx.send(embed=embed)


def froll():
    global server_seed, client_seed, nonce
    # async with bot.db.acquire() as conn:
    #     returned = await conn.fetchrow("SELECT * FROM server")
    # async with bot.db.acquire() as conn:
    #     await conn.execute("UPDATE server SET nonce = nonce +1")
    roll_result = hasher.roll_dice(server_seed, f"{client_seed}-{nonce}")
    nonce += 1
    return int(roll_result + 1)


async def dice(ctx, currency: str, amount: str, win_chance: int, payout: Decimal):
    try:
        if "." in str(Decimal(amount[:-1])) and len(str(Decimal(amount[:-1])).split(".")[1]) > 2:
            return
    except:
        if not isinstance(Decimal(amount), Decimal) and not isinstance(Decimal(amount[-1]), Decimal):
            return
    amount = formatok(amount)
    if currency != "07" and currency != "rs3":
        return

    name = ctx.author.display_name

    if not is_enough(amount, currency):
        return await not_enough(ctx, name, currency)

    if await get_value(ctx.author.id, currency) < amount:
        return await not_enough_funds(ctx, name)

    tmp_currency = currency

    if currency == "07":
        tmp_currency = "osrs"

    bets_added = int(amount / 100)
    if currency == "07":
        bets_added = int(amount / 20)
    await update_money(ctx.author.id, bets_added, "bets")
    await update_money(ctx.author.id, amount, f"total_{tmp_currency}_bet")
    await update_money(ctx.author.id, amount, f"total_{tmp_currency}_weekly")

    global server_seed, client_seed, nonce

    value = froll()

    if value > win_chance:
        await update_money(ctx.author.id, -int(amount * (payout - 1)), f"profit_{tmp_currency}")
        await update_money(ctx.author.id, int(amount * (payout - 1)), currency)
        amount = formatfromk(int(amount * payout))

        embed = discord.Embed(color=0x00ff00)
        embed.set_author(name=name)
        embed.add_field(name=f"{win_chance}x{payout} Dicing", value=f"Rolled **{value}** out of 100. You **won** "
                                                                    f"**{amount}** {currency}.")
        embed.set_footer(text=f"Client Seed: {client_seed}\nNonce: {nonce - 1}")
        return await ctx.send(embed=embed)
    else:
        await update_money(ctx.author.id, amount, f"profit_{tmp_currency}")
        await update_money(ctx.author.id, -amount, currency)

        amount = formatfromk(amount)
        embed = discord.Embed(color=0xff0000)
        embed.set_author(name=name)
        embed.add_field(name=f"{win_chance}x{payout} Dicing", value=f"Rolled **{value}** out of 100. You **lost** "
                                                                    f"**{amount}** {currency}.")
        embed.set_footer(text=f"Client Seed: {client_seed}\nNonce: {nonce - 1}")
        return await ctx.send(embed=embed)


async def flower_win(ctx, flower, amount, currency, payout):
    tmp_currency = currency
    if currency == "07":
        tmp_currency = "osrs"
    await update_money(ctx.author.id, -int(amount * (payout - 1)), f"profit_{tmp_currency}")
    await update_money(ctx.author.id, int(amount * payout), currency)
    embed = discord.Embed(color=0x00ff00)
    embed.set_author(name=ctx.author.display_name)
    embed.add_field(name="Hot/Cold", value=f"You picked a {flower['color']} flower and **won** "
                                           f"{formatfromk(amount * payout)}.")
    embed.set_thumbnail(url=flower['url'])
    return await ctx.send(embed=embed)


async def my_background_task():
    global client_seed, server_seed, server_seed_hash, nonce
    await bot.wait_until_ready()
    channel = bot.get_channel(stakeland_public)  # public
    while not bot.is_closed():
        old_hash = server_seed_hash
        old_server_seed = server_seed
        # async with bot.db.acquire() as conn:
        #     returned = await conn.fetchrow("SELECT * from server")
        server_seed = hasher.create_seed()
        server_seed_hash = hasher.hashed_seed(server_seed)
        client_seed = hasher.create_seed()
        nonce = 0
        # async with bot.db.acquire() as conn:
        #     await conn.execute('''UPDATE server SET server_seed = $1, server_seed_hash = $2, client_seed = $3,
        #         nonce = $4''', server_seed, server_seed_hash, client_seed, nonce)
        seeds = bot.get_channel(stakeland_seed)  # seeds
        embed = discord.Embed(color=0x0099cc)
        embed.add_field(name="Provably Fair Seeds", value=f"**Previous hash:** {old_hash}\n"
                                                          f"**Previous Seed:** {old_server_seed}\n"
                                                          f"**Current hash:** {server_seed_hash}")
        await seeds.send(embed=embed)
        giveaway_amount = 20
        async with bot.db.acquire() as conn:
            returned = await conn.fetch("SELECT * FROM rsmoney WHERE bets > 0")
        async with bot.db.acquire() as conn:
            await conn.execute("UPDATE rsmoney SET bets = 0")
        embed = discord.Embed(color=0x0099cc)
        embed.set_author(name="Stake Land Bettor Giveaway")
        if not returned:
            embed.add_field(name="Giveaway Results", value=f"There was no winner!\n\n**Bet 200k 07 or 1m rs3 within "
                                                           f"the next 10 minutes for a chance to win 200k 07!**\nThe "
                                                           f"more you bet the larger chance you have of winning.")
            await channel.send(embed=embed)
        else:
            bets = []
            winner = ""
            for bettor in returned:
                try:
                    bets.extend([bettor['id'] for _ in range(bettor['bets'])])
                except MemoryError:
                    winner = bettor['id']
            if winner == "":
                winner = secrets.choice(bets)
            embed.add_field(name="Giveaway Results", value=f"<@{winner}> won {formatfromk(giveaway_amount)} 07 "
                                                           f"for betting within the last 10 minutes!\n\n"
                                                           f"**Bet 200k 07 or 1m rs3 within the next 10 minutes for a "
                                                           f"chance to win 200k 07!**\nThe more you bet the larger "
                                                           f"chance you have of winning.")
            await channel.send(embed=embed)
            await update_money(winner, giveaway_amount, "07")
        await asyncio.sleep(600)


@bot.listen()
async def on_command_error(ctx, error):
    if isinstance(error, commands.errors.MissingRequiredArgument) or \
            isinstance(error, commands.errors.BadArgument):
        name = ctx.author.display_name
        embed = discord.Embed()
        embed.set_author(name=name)
        embed.add_field(name="Error", value=f'**Command usage:** {ctx.prefix}{ctx.command.signature}')
        await ctx.send(embed=embed)


REACT = 'kappa'
zach_id = 209081432956600320


@bot.listen()
async def on_message(message):
    is_mentioning_owner = False
    if message.guild.get_member(zach_id) in message.mentions:
        is_mentioning_owner = True
    is_not_from_bot = not message.author.bot
    is_in_a_guild = message.guild
    is_guild_with_owner_in = is_in_a_guild and message.guild.get_member(zach_id) is not None

    if (
        is_mentioning_owner
        and is_not_from_bot
        and is_in_a_guild
        and is_guild_with_owner_in
    ):
        react = discord.utils.get(bot.emojis, name=REACT)
        await message.add_reaction(react)


@bot.command()
async def ping(ctx):
    start = time.monotonic()
    msg = await ctx.send('Pinging...')
    millis = (time.monotonic() - start) * 1000

    # Since sharded bots will have more than one latency, this will average them if needed.
    heartbeat = ctx.bot.latency * 1000
    embed = discord.Embed(color=0x0099cc)
    embed.add_field(name="Ping", value=f"💓Heartbeat: {heartbeat:,.2f}ms\t💬ACK: {millis:,.2f}ms.")
    await msg.edit(embed=embed)


@bot.command()
async def roll(ctx, max_roll: int):
    embed = discord.Embed(color=0x0099cc)
    embed.add_field(name="Custom Roll", value=f"{secrets.randbelow(max_roll) + 1}\nRolled a random number between "
                                              f"1-{max_roll}")
    await ctx.send(embed=embed)


@bot.command(aliases=["$", "wallet", "bal", "balance", "£"])
async def w(ctx, member: discord.Member = None):
    user = ctx.author

    if member is not None and member is not ctx.author:
        user = member
        if await get_value(user.id, "privacy") is True and not is_staky(ctx):
            await ctx.send("Sorry, that user has wallet privacy mode enabled.")
            return

    current_osrs = formatfromk(await get_value(user.id, "07"))
    current_rs3 = formatfromk(await get_value(user.id, "rs3"))

    embed = discord.Embed(color=0x0099cc)
    name = user.display_name
    embed.set_author(name=name)
    embed.add_field(name="RS3 Balance", value=str(current_rs3), inline=True)
    embed.add_field(name="07 Balance", value=str(current_osrs), inline=True)

    if await get_value(user.id, "privacy") is True:
        await ctx.author.send(embed=embed)
        await ctx.message.add_reaction('📫')
    else:
        await ctx.send(embed=embed)


@bot.command()
async def privacy(ctx, privacy_value: str):
    if privacy_value != "on" and privacy_value != "off":
        return

    user_id = ctx.author.id
    embed = discord.Embed(color=0x0099cc)
    embed.set_author(name=ctx.author.display_name)

    if privacy_value == "on":
        privacy_message = "Wallet privacy has been enabled."
        async with bot.db.acquire() as conn:
            await conn.execute("UPDATE rsmoney SET privacy=$1 WHERE id=$2", True, user_id)

    else:
        privacy_message = "Wallet privacy has been disabled."
        async with bot.db.acquire() as conn:
            await conn.execute("UPDATE rsmoney SET privacy=$1 WHERE id=$2", False, user_id)

    embed.add_field(name="Wallet Privacy", value=privacy_message)
    await ctx.send(embed=embed)


@bot.command()
@commands.check(is_staky)
async def setrates(ctx, rs3: Decimal, osrs: Decimal):
    global rs3_osrs_rate, osrs_rs3_rate
    os.environ['rs3_osrs_rate'] = str(rs3)
    os.environ['osrs_rs3_rate'] = str(osrs)
    rs3_osrs_rate = rs3
    osrs_rs3_rate = osrs
    await ctx.send("Rates have been changed.")


@bot.command()
@commands.check(is_staky)
async def updateall(ctx, currency: str, amount: str):
    try:
        if "." in str(Decimal(amount[:-1])) and len(str(Decimal(amount[:-1])).split(".")[1]) > 2:
            return
    except:
        if not isinstance(Decimal(amount), Decimal) and not isinstance(Decimal(amount[-1]), Decimal):
            return
    amount = formatok(amount)
    if currency != "07" and currency != "rs3":
        return
    for member in ctx.message.guild.members:
        await update_money(member.id, amount, currency)
    embed = discord.Embed(color=0x0099cc)
    embed.set_author(name=ctx.author.display_name)
    embed.add_field(name="Currency Update", value=f"Successfully added {formatfromk(amount)} {currency} to "
                                                  f"everyone's wallet.")
    embed.set_thumbnail(url="http://i.imgur.com/TkiKjWM.png")
    await ctx.send(embed=embed)


@bot.command()
@commands.check(is_staky)
async def update(ctx, currency: str, members: commands.Greedy[discord.Member], amount: str):
    amount = formatok(amount)
    if len(str(amount)) < 2:
        return

    for member in members:
        await update_money(member.id, amount, currency)
        new_amount = formatfromk(amount)

        embed = discord.Embed(color=0x0099cc)
        embed.set_author(name=ctx.author.display_name)
        embed.add_field(name="Currency Update", value=f"Successfully added {new_amount} {currency} to "
                                                      f"{member.mention}'s wallet.")
        embed.set_thumbnail(url="http://i.imgur.com/TkiKjWM.png")
        await ctx.send(embed=embed)


@bot.command()
async def transfer(ctx, currency: str, members: commands.Greedy[discord.Member], amount: str):
    amount = formatok(amount)
    if amount < 10 or ctx.author is members:
        return

    current = await get_value(ctx.author.id, currency)
    name = ctx.author.display_name

    if not current >= amount * len(members):
        embed = discord.Embed()
        embed.set_author(name=name)
        embed.add_field(name="Error", value="You don't have enough balance.")
        return await ctx.send(embed=embed)

    await update_money(ctx.author.id, -(amount * len(members)), currency)
    message = ""
    new_amount = formatfromk(amount)
    for member in members:
        await update_money(member.id, amount, currency)
        message += f"{member.mention} "

    embed = discord.Embed(color=0x0099cc)
    embed.set_author(name=name)
    embed.add_field(name="Currency Update",
                    value=f"Successfully added {new_amount} {currency} to {message}wallet(s)")
    embed.set_thumbnail(url="http://i.imgur.com/TkiKjWM.png")
    await ctx.send(embed=embed)


@bot.command(name="40")
async def dice_40(ctx, currency: str, amount: str):
    return await dice(ctx, currency, amount, 40, Decimal('1.5'))


@bot.command(name="45")
async def dice_45(ctx, currency: str, amount: str):
    return await dice(ctx, currency, amount, 45, Decimal('1.55'))


@bot.command(name="50")
async def dice_50(ctx, currency: str, amount: str):
    return await dice(ctx, currency, amount, 50, Decimal('1.9'))


@bot.command(name="54")
async def dice_54(ctx, currency: str, amount: str):
    return await dice(ctx, currency, amount, 54, Decimal('2'))


@bot.command(name="75")
async def dice_75(ctx, currency: str, amount: str):
    return await dice(ctx, currency, amount, 75, Decimal('3'))


@bot.command(name="90")
async def dice_90(ctx, currency: str, amount: str):
    return await dice(ctx, currency, amount, 90, Decimal('7'))


@bot.command(name="95")
async def dice_95(ctx, currency: str, amount: str):
    return await dice(ctx, currency, amount, 95, Decimal('10'))


@bot.command(aliases=["under"])
async def over(ctx, currency: str, amount: str):
    try:
        if "." in str(Decimal(amount[:-1])) and len(str(Decimal(amount[:-1])).split(".")[1]) > 2:
            return
    except:
        if not isinstance(Decimal(amount), Decimal) and not isinstance(Decimal(amount[-1]), Decimal):
            return
    amount = formatok(amount)
    if currency != "07" and currency != "rs3":
        return

    name = ctx.author.display_name

    if not is_enough(amount, currency):
        return await not_enough(ctx, name, currency)

    if await get_value(ctx.author.id, currency) < amount:
        return await not_enough_funds(ctx, name)

    tmp_currency = currency

    if currency == "07":
        tmp_currency = "osrs"
    bets_added = int(amount / 100)
    if currency == "07":
        bets_added = int(amount / 20)
    await update_money(ctx.author.id, bets_added, "bets")
    await update_money(ctx.author.id, amount, f"total_{tmp_currency}_bet")
    await update_money(ctx.author.id, amount, f"total_{tmp_currency}_weekly")
    global server_seed, client_seed, nonce

    value = froll()

    if ctx.invoked_with == "over" and value > 50 or ctx.invoked_with == "under" and value < 50:
        await update_money(ctx.author.id, -int(amount * 0.9), f"profit_{tmp_currency}")
        await update_money(ctx.author.id, int(amount * 0.9), currency)
        amount = int(amount * 1.9)
        amount = formatfromk(amount)

        embed = discord.Embed(color=0x00ff00)
        embed.set_author(name=name)
        embed.add_field(name=f"Over/Underx1.9 Dicing", value=f"Rolled {value} out of 100. You **won** {amount} "
                                                             f"{currency}.")
        embed.set_footer(text=f"Client Seed: {client_seed}\nNonce: {nonce - 1}")
        return await ctx.send(embed=embed)

    else:
        await update_money(ctx.author.id, amount, f"profit_{tmp_currency}")
        await update_money(ctx.author.id, -amount, currency)
        amount = formatfromk(amount)

        embed = discord.Embed(color=0xff0000)
        embed.set_author(name=name)
        embed.add_field(name=f"Over/Underx1.9 Dicing", value=f"Rolled {value} out of 100. You **lost** {amount} "
                                                             f"{currency}.")
        embed.set_footer(text=f"Client Seed: {client_seed}\nNonce: {nonce - 1}")
        return await ctx.send(embed=embed)


@bot.command()
async def dd(ctx, currency: str, amount: str):
    if ctx.author.id in current_dd_games:
        return await ctx.send(f"{ctx.author.mention}, please finish your older DiceDuel game.")

    try:
        if "." in str(Decimal(amount[:-1])) and len(str(Decimal(amount[:-1])).split(".")[1]) > 2:
            return
    except:
        if not isinstance(Decimal(amount), Decimal) and not isinstance(Decimal(amount[-1]), Decimal):
            return
    amount = formatok(amount)
    if currency != "07" and currency != "rs3":
        return

    name = ctx.author.display_name

    if not is_enough(amount, currency):
        return await not_enough(ctx, name, currency)

    if await get_value(ctx.author.id, currency) < amount:
        return await not_enough_funds(ctx, name)

    current_dd_games.append(ctx.author.id)
    await update_money(ctx.author.id, -amount, currency)
    tmp_currency = currency
    if currency == "07":
        tmp_currency = "osrs"

    bets_added = int(amount / 100)
    if currency == "07":
        bets_added = int(amount / 20)
    await update_money(ctx.author.id, bets_added, "bets")
    await update_money(ctx.author.id, amount, f"total_{tmp_currency}_bet")
    await update_money(ctx.author.id, amount, f"total_{tmp_currency}_weekly")

    bot_roll = secrets.randbelow(11) + 2
    embed = discord.Embed(color=0x0099cc)
    embed.set_author(name=name)
    embed.add_field(name="DiceDuel", value=f"<@502940842143514633> rolled a **{bot_roll}** on a Two-Six sided "
                                           f"dice.\nTotalPot: **{formatfromk(int(amount * 1.8))}** {currency}\n"
                                           f"Please type **roll** to roll the dice!")
    embed.set_thumbnail(url="http://vignette.wikia.nocookie.net/runescape2/images/f/f2/Dice_bag_detail.png")
    await ctx.send(embed=embed)

    def check(m):
        return m.content.lower() == 'roll' and m.channel == ctx.channel and m.author.id == ctx.author.id

    await bot.wait_for('message', check=check)

    current_dd_games.remove(ctx.author.id)
    user_roll = secrets.randbelow(11) + 2

    embed = discord.Embed(color=0x0099cc)
    embed.add_field(name="DiceDuel", value=f"{ctx.author.mention} rolled a **{user_roll}** on a Two-Six sided "
                                           f"dice.\nTotalPot: **{formatfromk(int(amount * 1.8))}** {currency}")
    embed.set_thumbnail(url="http://vignette.wikia.nocookie.net/runescape2/images/f/f2/Dice_bag_detail.png")
    embed.set_author(name=name)
    await ctx.send(embed=embed)

    if user_roll > bot_roll:
        await update_money(ctx.author.id, -int(amount * 0.8), f"profit_{tmp_currency}")
        await update_money(ctx.author.id, int(amount * 1.8), currency)
        embed = discord.Embed(color=0x00ff00)
        embed.set_author(name=name)
        embed.add_field(name="DiceDuel", value=f"<@502940842143514633> **[{bot_roll}**-**{user_roll}**] "
                                               f"{ctx.author.mention}\n{ctx.author.mention} won "
                                               f"**{formatfromk(int(amount * 1.8))}** {currency}")

    elif user_roll == bot_roll:
        await update_money(ctx.author.id, amount, currency)
        embed = discord.Embed(color=0x0099cc)
        embed.set_author(name=name)
        embed.add_field(name="DiceDuel", value=f"<@502940842143514633> **[{bot_roll}**-**{user_roll}**] "
                                               f"{ctx.author.mention}\nIt was a tie. You were refunded "
                                               f"**{formatfromk(int(amount))}** {currency}")

    else:
        await update_money(ctx.author.id, amount, f"profit_{tmp_currency}")
        embed = discord.Embed(color=0xff0000)
        embed.set_author(name=name)
        embed.add_field(name="DiceDuel", value=f"<@502940842143514633> [**{bot_roll}**-**{user_roll}**] "
                                               f"{ctx.author.mention}\n<@502940842143514633> won **"
                                               f"{formatfromk(int(amount * 1.8))}** {currency}")
    embed.set_thumbnail(url="http://vignette.wikia.nocookie.net/runescape2/images/f/f2/Dice_bag_detail.png")
    await ctx.send(embed=embed)


@bot.command()
@commands.has_role("Host")
async def d(ctx, currency: str, member: discord.Member, amount: str):
    if ctx.author.id in current_dd_games:
        return await ctx.send(f"{ctx.author.mention}, please finish your older DiceDuel game.")
    if member.id in current_dd_games:
        return await ctx.send(f"{ctx.author.mention}, please finish your older DiceDuel game.")
    try:
        if "." in str(Decimal(amount[:-1])) and len(str(Decimal(amount[:-1])).split(".")[1]) > 2:
            return
    except:
        if not isinstance(Decimal(amount), Decimal) and not isinstance(Decimal(amount[-1]), Decimal):
            return
    amount = formatok(amount)
    if currency != "07" and currency != "rs3":
        return
    tmp_currency = currency
    if currency == "07":
        tmp_currency = "osrs"
    bets_added = int(amount / 100)
    if currency == "07":
        bets_added = int(amount / 20)

    await update_money(ctx.author.id, bets_added, "bets")
    await update_money(ctx.author.id, amount, f"total_{tmp_currency}_bet")
    await update_money(ctx.author.id, amount, f"total_{tmp_currency}_weekly")
    await update_money(member.id, bets_added, "bets")
    await update_money(member.id, amount, f"total_{tmp_currency}_bet")
    await update_money(member.id, amount, f"total_{tmp_currency}_weekly")
    current_dd_games.append(ctx.author.id)
    current_dd_games.append(member.id)
    embed = discord.Embed(color=0x0099cc)
    embed.set_author(name=f"{ctx.author.display_name} vs {member.display_name}")
    embed.add_field(name="DiceDuel", value=f"{ctx.author.display_name}, please type **roll** to roll the dice!")
    embed.set_thumbnail(url="http://vignette.wikia.nocookie.net/runescape2/images/f/f2/Dice_bag_detail.png")
    await ctx.send(embed=embed)

    def check(m):
        return m.content.lower() == 'roll' and m.channel == ctx.channel and m.author.id == ctx.author.id

    await bot.wait_for('message', check=check)

    bot_roll = secrets.randbelow(11) + 2
    embed = discord.Embed(color=0x0099cc)
    embed.set_author(name=f"{ctx.author.display_name} vs {member.display_name}")
    embed.add_field(name="DiceDuel", value=f"{ctx.author.display_name} rolled a **{bot_roll}** on a Two-Six "
                                           f" dice.\nTotalPot: **{formatfromk(int(amount * 1.8))}** {currency}"
                                           f"\n{member.display_name} Please type **roll** to roll the dice!")
    embed.set_thumbnail(url="http://vignette.wikia.nocookie.net/runescape2/images/f/f2/Dice_bag_detail.png")
    await ctx.send(embed=embed)

    def check(m):
        return m.content.lower() == 'roll' and m.channel == ctx.channel and m.author.id == member.id
    try:
        await bot.wait_for('message', check=check, timeout=60)
    except asyncio.TimeoutError:
        pass
    user_roll = secrets.randbelow(11) + 2

    embed = discord.Embed(color=0x0099cc)
    embed.add_field(name="DiceDuel",
                    value=f"{member.display_name} rolled a **{user_roll}** on a Two-Six sided dice.\n"
                          f"TotalPot: **{formatfromk(int(amount * 1.8))}** {currency}")
    embed.set_thumbnail(url="http://vignette.wikia.nocookie.net/runescape2/images/f/f2/Dice_bag_detail.png")
    embed.set_author(name=f"{ctx.author.display_name} vs {member.display_name}")
    await ctx.send(embed=embed)
    current_dd_games.remove(ctx.author.id)
    current_dd_games.remove(member.id)

    if user_roll > bot_roll:
        embed = discord.Embed(color=0x00ff00)
        embed.set_author(name=f"{ctx.author.display_name} vs {member.display_name}")
        embed.add_field(name="DiceDuel", value=f"{ctx.author.mention} **[{bot_roll}**-**{user_roll}**] "
                                               f"{member.mention}\n{member.mention} won "
                                               f"**{formatfromk(int(amount * 1.8))}** {currency}")

    elif user_roll == bot_roll:
        await update_money(ctx.author.id, amount, currency)
        embed = discord.Embed(color=0x0099cc)
        embed.set_author(name=f"{ctx.author.display_name} vs {member.display_name}")
        embed.add_field(name="DiceDuel", value=f"{ctx.author.mention} **[{bot_roll}**-**{user_roll}**] "
                                               f"{member.mention}\nIt was a tie. You will be refunded "
                                               f"**{formatfromk(int(amount * 1.8))}** {currency}")

    else:
        embed = discord.Embed(color=0xff0000)
        embed.set_author(name=f"{ctx.author.display_name} vs {member.display_name}")
        embed.add_field(name="DiceDuel", value=f"{ctx.author.mention} [**{bot_roll}**-**{user_roll}**] "
                                               f"{member.mention}\n{ctx.author.mention} won **"
                                               f"{formatfromk(int(amount * 1.8))}** {currency}")
    embed.set_thumbnail(url="http://vignette.wikia.nocookie.net/runescape2/images/f/f2/Dice_bag_detail.png")
    await ctx.send(embed=embed)


@bot.command()
@commands.has_role("Host")
async def f(ctx, currency: str, member: discord.Member, amount: str):
    if ctx.author.id in current_flower_games:
        return await ctx.send(f"{ctx.author.mention}, please finish your older Flower game.")
    if member.id in current_flower_games:
        return await ctx.send(f"{ctx.author.mention}, please finish your older Flower game.")
    try:
        if "." in str(Decimal(amount[:-1])) and len(str(Decimal(amount[:-1])).split(".")[1]) > 2:
            return
    except:
        if not isinstance(Decimal(amount), Decimal) and not isinstance(Decimal(amount[-1]), Decimal):
            return
    amount = formatok(amount)
    if currency != "07" and currency != "rs3":
        return
    tmp_currency = currency
    if currency == "07":
        tmp_currency = "osrs"
    current_flower_games.append(ctx.author.id)
    current_flower_games.append(member.id)
    bets_added = int(amount / 100)
    if currency == "07":
        bets_added = int(amount / 20)
    await update_money(ctx.author.id, bets_added, "bets")
    await update_money(ctx.author.id, amount, f"total_{tmp_currency}_bet")
    await update_money(ctx.author.id, amount, f"total_{tmp_currency}_weekly")
    await update_money(member.id, bets_added, "bets")
    await update_money(member.id, amount, f"total_{tmp_currency}_bet")
    await update_money(member.id, amount, f"total_{tmp_currency}_weekly")

    with open('flowers.json') as json_file:
        data = json.load(json_file)

    def pick_flower():
        return secrets.choice(data["flowers"])

    bot_flowers = {
        "<:blueflower:505851036058124289>": 0,
        "<:orangeflower:505851036322496523>": 0,
        "<:pastelflower:505851036267708417>": 0,
        "<:purpleflower:505851035932426251>": 0,
        "<:rainbowflower:505851036184084481>": 0,
        "<:redflower:505851036330885120>": 0,
        "<:yellowflower:505851036578086922>": 0
                   }
    user_flowers = {
        "<:blueflower:505851036058124289>": 0,
        "<:orangeflower:505851036322496523>": 0,
        "<:pastelflower:505851036267708417>": 0,
        "<:purpleflower:505851035932426251>": 0,
        "<:rainbowflower:505851036184084481>": 0,
        "<:redflower:505851036330885120>": 0,
        "<:yellowflower:505851036578086922>": 0
                   }
    bot_picks = ""
    user_picks = ""
    for x in range(0, 5):
        bot_pick = pick_flower()["emoji"]
        bot_picks += bot_pick
        bot_flowers[bot_pick] = bot_flowers.get(bot_pick, "none") + 1
        user_pick = pick_flower()["emoji"]
        user_picks += user_pick + " "
        user_flowers[user_pick] = user_flowers.get(user_pick, "none") + 1
    # Bust < 1 Pair < 2 Pair < 3 Of A Kind < Full House (3oak & 1 pair) < 4 Of A Kind < 5 Of A Kind.
    bot_flowers = sorted(bot_flowers.items(), key=operator.itemgetter(1), reverse=True)
    user_flowers = sorted(user_flowers.items(), key=operator.itemgetter(1), reverse=True)
    if bot_flowers[0][1] == 5:
        bot_picks += "\nValue: 5 Of A Kind"
        bot_value = 6
    elif bot_flowers[0][1] == 4:
        bot_picks += "\nValue: 4 Of A Kind"
        bot_value = 5
    elif bot_flowers[0][1] == 3 and bot_flowers[1][1] == 2:
        bot_picks += "\nValue: Full House"
        bot_value = 4
    elif bot_flowers[0][1] == 3:
        bot_picks += "\nValue: 3 Of A Kind"
        bot_value = 3
    elif bot_flowers[0][1] == 2 == bot_flowers[1][1]:
        bot_picks += "\nValue: 2 Pairs"
        bot_value = 2
    elif bot_flowers[0][1] == 2:
        bot_picks += "\nValue: 1 Pair"
        bot_value = 1
    else:
        bot_picks += "\nValue: BUST"
        bot_value = 0

    if user_flowers[0][1] == 5:
        user_picks += "\nValue: 5 Of A Kind"
        user_value = 6
    elif user_flowers[0][1] == 4:
        user_picks += "\nValue: 4 Of A Kind"
        user_value = 5
    elif user_flowers[0][1] == 3 and user_flowers[1][1] == 2:
        user_picks += "\nValue: Full House"
        user_value = 4
    elif user_flowers[0][1] == 3:
        user_picks += "\nValue: 3 Of A Kind"
        user_value = 3
    elif user_flowers[0][1] == 2 == user_flowers[1][1]:
        user_picks += "\nValue: 2 Pairs"
        user_value = 2
    elif user_flowers[0][1] == 2:
        user_picks += "\nValue: 1 Pair"
        user_value = 1
    else:
        user_picks += "\nValue: BUST"
        user_value = 0

    seeds = "<:mithril_seeds:507793442928328716>"

    embed = discord.Embed(color=0x0099cc)
    embed.title = f"{ctx.author.display_name} vs {member.display_name}"
    embed.add_field(name=f"{member.display_name}", value=f"{seeds}{seeds}{seeds}{seeds}{seeds}\nValue:")
    embed.add_field(name=f"{ctx.author.display_name}", value=f"{seeds}{seeds}{seeds}{seeds}{seeds}\nValue:")
    game = await ctx.send(embed=embed)

    embed = discord.Embed(color=0x0099cc)
    embed.add_field(name=f"{ctx.author.display_name} vs {member.display_name}", value=f"{ctx.author.display_name}, "
                                                                                      f"please type **plant** to plant "
                                                                                      f"your seeds.")
    plant_message = await ctx.send(embed=embed)

    def check(m):
        return m.content.lower() == 'plant' and m.channel == ctx.channel and m.author.id == ctx.author.id

    await bot.wait_for('message', check=check)

    embed = discord.Embed(color=0x0099cc)
    embed.title = f"{ctx.author.display_name} vs {member.display_name}"
    embed.add_field(name=f"{member.display_name}", value=f"{seeds}{seeds}{seeds}{seeds}{seeds}\nValue:")
    embed.add_field(name=f"{ctx.author.display_name}", value=f"{bot_picks}")
    await game.edit(embed=embed)

    embed = discord.Embed(color=0x0099cc)
    embed.add_field(name=f"{ctx.author.display_name} vs {member.display_name}", value=f"{member.display_name}, "
                                                                                      f"please type **plant** to plant "
                                                                                      f"your seeds.")
    await plant_message.edit(embed=embed)

    def check(m):
        return m.content.lower() == 'plant' and m.channel == ctx.channel and m.author.id == member.id

    try:
        await bot.wait_for('message', check=check, timeout=60)
    except asyncio.TimeoutError:
        pass

    current_flower_games.remove(ctx.author.id)
    current_flower_games.remove(member.id)

    if user_value > bot_value:
        embed = discord.Embed(color=0x00ff00)
        embed.title = "Flower Poker"
        embed.description = f"{member.display_name} **won** the pot of **{formatfromk(int(amount * 1.8))}** {currency}."
    elif user_value == bot_value:
        embed = discord.Embed(color=0x0099cc)
        embed.title = "Flower Poker"
        embed.description = f"It was a **tie**. You will be refunded **{formatfromk(int(amount))}** {currency}."
    else:
        embed = discord.Embed(color=0xff0000)
        embed.title = "Flower Poker"
        embed.description = f"{ctx.author.display_name} **won** the pot of **{formatfromk(int(amount * 1.8))}** " \
                            f"{currency}."
    embed.add_field(name=f"{ctx.author.display_name}", value=f"{bot_picks}")
    embed.add_field(name=f"{member.display_name}", value=f"{user_picks}")
    await game.edit(embed=embed)


@bot.command()
@commands.check(is_staky)
async def weekreset(ctx):
    async with bot.db.acquire() as conn:
        await conn.execute("UPDATE rsmoney SET total_osrs_weekly = 0")
    async with bot.db.acquire() as conn:
        await conn.execute("UPDATE rsmoney SET total_rs3_weekly = 0")
    async with bot.db.acquire() as conn:
        await conn.execute("UPDATE server SET profit_rs3 = 0")
    async with bot.db.acquire() as conn:
        await conn.execute("UPDATE server SET profit_osrs = 0")
    await ctx.send("Weekly wagers and profits have been reset.")


@bot.command(aliases=["cold", "rainbow"])
async def hot(ctx, currency: str, amount: str):
    try:
        if "." in str(Decimal(amount[:-1])) and len(str(Decimal(amount[:-1])).split(".")[1]) > 2:
            return
    except:
        if not isinstance(Decimal(amount), Decimal) and not isinstance(Decimal(amount[-1]), Decimal):
            return
    amount = formatok(amount)
    if currency != "07" and currency != "rs3":
        return
    name = ctx.author.display_name

    if not is_enough(amount, currency):
        return await not_enough(ctx, name, currency)

    if await get_value(ctx.author.id, currency) < amount:
        return await not_enough_funds(ctx, name)

    with open('flowers.json') as json_file:
        data = json.load(json_file)

    tmp_currency = currency
    if currency == "07":
        tmp_currency = "osrs"

    bets_added = int(amount / 100)
    if currency == "07":
        bets_added = int(amount / 20)
    await update_money(ctx.author.id, bets_added, "bets")
    await update_money(ctx.author.id, amount, f"total_{tmp_currency}_bet")
    await update_money(ctx.author.id, amount, f"total_{tmp_currency}_weekly")
    flower = secrets.choice(data['flowers'])

    if ctx.invoked_with == "cold" and flower['value'] == "cold":
        return await flower_win(ctx, flower, amount, currency, 1)

    elif ctx.invoked_with == "hot" and flower['value'] == "hot":
        return await flower_win(ctx, flower, amount, currency, 1)

    elif ctx.invoked_with == "rainbow" and flower['value'] == "rainbow":
        return await flower_win(ctx, flower, amount, currency, 3)

    else:
        await update_money(ctx.author.id, int(amount), f"profit_{tmp_currency}")
        await update_money(ctx.author.id, int(-amount), currency)
        embed = discord.Embed(color=0xff0000)
        embed.set_author(name=name)
        embed.add_field(name="Hot/Cold", value=f"You picked a {flower['color']} flower and **lost** "
                                               f"{formatfromk(amount)} {currency}.")
        embed.set_thumbnail(url=flower['url'])
        await ctx.send(embed=embed)


@bot.command()
async def abc(ctx, currency: str, amount: str):
    if ctx.author.id in current_flower_games:
        return await ctx.send(f"{ctx.author.mention}, please finish your older ABC Flower game.")
    try:
        if "." in str(Decimal(amount[:-1])) and len(str(Decimal(amount[:-1])).split(".")[1]) > 2:
            return
    except:
        if not isinstance(Decimal(amount), Decimal) and not isinstance(Decimal(amount[-1]), Decimal):
            return
    amount = formatok(amount)
    if currency != "07" and currency != "rs3":
        return
    name = ctx.author.display_name

    if not is_enough(amount, currency):
        return await not_enough(ctx, name, currency)

    if await get_value(ctx.author.id, currency) < amount:
        return await not_enough_funds(ctx, name)

    tmp_currency = "rs3"
    if currency == "07":
        tmp_currency = "osrs"

    bets_added = int(amount / 100)
    if currency == "07":
        bets_added = int(amount / 20)
    await update_money(ctx.author.id, bets_added, "bets")
    await update_money(ctx.author.id, amount, f"total_{tmp_currency}_bet")
    await update_money(ctx.author.id, amount, f"total_{tmp_currency}_weekly")
    await update_money(ctx.author.id, -amount, currency)
    current_flower_games.append(ctx.author.id)

    with open('flowers.json') as json_file:
        data = json.load(json_file)

    flower = secrets.choice(data['flowers'])
    embed = discord.Embed(color=0x0099cc)
    embed.add_field(name="ABC Flowers", value=f"<@502940842143514633> picked a {flower['color']} flower.\n"
                                              f"TotalPot: **{formatfromk(int(amount * 1.8))}** {currency}\n"
                                              f"Please type **plant** to plant your flower!")
    embed.set_thumbnail(url=flower['url'])
    await ctx.send(embed=embed)

    def check(m):
        return m.content.lower() == 'plant' and m.channel == ctx.channel and m.author.id == ctx.author.id

    await bot.wait_for('message', check=check)
    current_flower_games.remove(ctx.author.id)

    bot_flower = secrets.choice(data['flowers'])
    embed = discord.Embed(color=0x0099cc)
    embed.add_field(name="ABC Flowers", value=f"{ctx.author.mention} picked a {bot_flower['color']} flower.\n"
                                              f"TotalPot: **{formatfromk(int(amount * 1.8))}** {currency}\n")
    embed.set_thumbnail(url=bot_flower['url'])
    embed.set_author(name=name)
    await ctx.send(embed=embed)

    if flower['color'] > bot_flower['color']:
        await update_money(ctx.author.id, -int(amount * 0.8), f"profit_{tmp_currency}")
        await update_money(ctx.author.id, int(amount * 1.8), currency)
        embed = discord.Embed(color=0x00ff00)
        embed.add_field(name="ABC Flowers", value=f"{ctx.author.mention} picked a {bot_flower['color']} flower and "
                                                  f"<@502940842143514633> picked a {flower['color']} flower.\n"
                                                  f"You have **won {formatfromk(int(amount * 1.8))}** {currency}\n")
        embed.set_author(name=name)
        return await ctx.send(embed=embed)

    elif flower['color'] == bot_flower['color']:
        await update_money(ctx.author.id, int(amount), currency)
        embed = discord.Embed(color=0x00ff00)
        embed.add_field(name="ABC Flowers", value=f"{ctx.author.mention} picked a {bot_flower['color']} flower and "
                                                  f"<@502940842143514633> picked a {flower['color']} flower.\n"
                                                  f"It was a **tie**. You were refunded **{formatfromk(int(amount))}** "
                                                  f"{currency}\n")
        embed.set_author(name=name)
        return await ctx.send(embed=embed)

    else:
        await update_money(ctx.author.id, amount, f"profit_{tmp_currency}")
        embed = discord.Embed(color=0xff0000)
        embed.add_field(name="ABC Flowers", value=f"{ctx.author.mention} picked a {bot_flower['color']} flower and "
                                                  f"<@502940842143514633> picked a {flower['color']} flower.\n"
                                                  f"You have **lost {formatfromk(amount)}** {currency}\n")
        embed.set_author(name=name)
        await ctx.send(embed=embed)


@bot.command()
async def fp(ctx, currency: str, amount: str):
    try:
        if "." in str(Decimal(amount[:-1])) and len(str(Decimal(amount[:-1])).split(".")[1]) > 2:
            return
    except:
        if not isinstance(Decimal(amount), Decimal) and not isinstance(Decimal(amount[-1]), Decimal):
            return
    amount = formatok(amount)
    if currency != "07" and currency != "rs3":
        return
    name = ctx.author.display_name

    if not is_enough(amount, currency):
        return await not_enough(ctx, name, currency)

    if await get_value(ctx.author.id, currency) < amount:
        return await not_enough_funds(ctx, name)

    tmp_currency = "rs3"
    if currency == "07":
        tmp_currency = "osrs"

    bets_added = int(amount / 100)
    if currency == "07":
        bets_added = int(amount / 20)
    await update_money(ctx.author.id, bets_added, "bets")
    await update_money(ctx.author.id, amount, f"total_{tmp_currency}_bet")
    await update_money(ctx.author.id, amount, f"total_{tmp_currency}_weekly")

    with open('flowers.json') as json_file:
        data = json.load(json_file)

    def pick_flower():
        return secrets.choice(data["flowers"])

    bot_flowers = {
        "<:blueflower:505851036058124289>": 0,
        "<:orangeflower:505851036322496523>": 0,
        "<:pastelflower:505851036267708417>": 0,
        "<:purpleflower:505851035932426251>": 0,
        "<:rainbowflower:505851036184084481>": 0,
        "<:redflower:505851036330885120>": 0,
        "<:yellowflower:505851036578086922>": 0
                   }
    user_flowers = {
        "<:blueflower:505851036058124289>": 0,
        "<:orangeflower:505851036322496523>": 0,
        "<:pastelflower:505851036267708417>": 0,
        "<:purpleflower:505851035932426251>": 0,
        "<:rainbowflower:505851036184084481>": 0,
        "<:redflower:505851036330885120>": 0,
        "<:yellowflower:505851036578086922>": 0
                   }
    bot_picks = ""
    user_picks = ""
    for x in range(0, 5):
        bot_pick = pick_flower()["emoji"]
        bot_picks += bot_pick
        bot_flowers[bot_pick] = bot_flowers.get(bot_pick, "none") + 1
        user_pick = pick_flower()["emoji"]
        user_picks += user_pick + " "
        user_flowers[user_pick] = user_flowers.get(user_pick, "none") + 1
    # Bust < 1 Pair < 2 Pair < 3 Of A Kind < Full House (3oak & 1 pair) < 4 Of A Kind < 5 Of A Kind.
    bot_flowers = sorted(bot_flowers.items(), key=operator.itemgetter(1), reverse=True)
    user_flowers = sorted(user_flowers.items(), key=operator.itemgetter(1), reverse=True)
    if bot_flowers[0][1] == 5:
        bot_picks += "\nValue: 5 Of A Kind"
        bot_value = 6
    elif bot_flowers[0][1] == 4:
        bot_picks += "\nValue: 4 Of A Kind"
        bot_value = 5
    elif bot_flowers[0][1] == 3 and bot_flowers[1][1] == 2:
        bot_picks += "\nValue: Full House"
        bot_value = 4
    elif bot_flowers[0][1] == 3:
        bot_picks += "\nValue: 3 Of A Kind"
        bot_value = 3
    elif bot_flowers[0][1] == 2 == bot_flowers[1][1]:
        bot_picks += "\nValue: 2 Pairs"
        bot_value = 2
    elif bot_flowers[0][1] == 2:
        bot_picks += "\nValue: 1 Pair"
        bot_value = 1
    else:
        bot_picks += "\nValue: BUST"
        bot_value = 0

    if user_flowers[0][1] == 5:
        user_picks += "\nValue: 5 Of A Kind"
        user_value = 6
    elif user_flowers[0][1] == 4:
        user_picks += "\nValue: 4 Of A Kind"
        user_value = 5
    elif user_flowers[0][1] == 3 and user_flowers[1][1] == 2:
        user_picks += "\nValue: Full House"
        user_value = 4
    elif user_flowers[0][1] == 3:
        user_picks += "\nValue: 3 Of A Kind"
        user_value = 3
    elif user_flowers[0][1] == 2 == user_flowers[1][1]:
        user_picks += "\nValue: 2 Pairs"
        user_value = 2
    elif user_flowers[0][1] == 2:
        user_picks += "\nValue: 1 Pair"
        user_value = 1
    else:
        user_picks += "\nValue: BUST"
        user_value = 0

    if user_value > bot_value:
        embed = discord.Embed(color=0x00ff00)
        embed.title = "Flower Poker"
        embed.description = f"{ctx.author.display_name} **won** the pot of **{formatfromk(int(amount * 1.8))}** " \
                            f"{currency}."
        await update_money(ctx.author.id, -int(amount * 0.8), f"profit_{tmp_currency}")
        await update_money(ctx.author.id, int(int(amount * 0.8)), currency)
    elif user_value == bot_value:
        embed = discord.Embed(color=0x0099cc)
        embed.title = "Flower Poker"
        embed.description = f"It was a **tie**. You were refunded **{formatfromk(amount)}** {currency}."
    else:
        embed = discord.Embed(color=0xff0000)
        embed.title = "Flower Poker"
        embed.description = f"{ctx.author.display_name} **lost** the pot of **{formatfromk(int(amount * 1.8))}** " \
                            f"{currency}."
        await update_money(ctx.author.id, amount, f"profit_{tmp_currency}")
        await update_money(ctx.author.id, -amount, currency)
    embed.add_field(name=f"{ctx.author.display_name}", value=f"{user_picks}")
    embed.add_field(name=f"Stake Land", value=f"{bot_picks}")
    await ctx.send(embed=embed)


@bot.command()
async def jackpot(ctx, currency: str, amount: str):
    global is_current_jackpot, jackpot_currency, more_than_one, jackpot_pot

    if currency != "07" and currency != "rs3":
        return
    try:
        if "." in str(Decimal(amount[:-1])) and len(str(Decimal(amount[:-1])).split(".")[1]) > 2:
            return
    except:
        if not isinstance(Decimal(amount), Decimal) and not isinstance(Decimal(amount[-1]), Decimal):
            return
    amount = formatok(amount)
    name = ctx.author.display_name

    if not is_enough(amount, currency):
        return await not_enough(ctx, name, currency)

    if await get_value(ctx.author.id, currency) < amount:
        return await not_enough_funds(ctx, name)

    embed = discord.Embed(color=0x0099cc)
    embed.set_author(name=ctx.author.display_name, icon_url=ctx.message.author.avatar_url)

    if not is_current_jackpot:
        is_current_jackpot = True
        jackpot_currency = currency
        await update_money(ctx.author.id, -amount, currency)
        embed.add_field(name="Jackpot Added", value=f"You have successfully created a jackpot game and added "
                                                    f"{formatfromk(amount)} {currency} to the pot.")
        await ctx.send(embed=embed)
        bot.loop.create_task(jackpot_game())

    elif is_current_jackpot and jackpot_currency == currency:
        more_than_one = True
        await update_money(ctx.author.id, -amount, currency)
        embed.add_field(name="Jackpot Added", value=f"You have successfully added {formatfromk(amount)} {currency} to "
                                                    f"the pot.")
        embed.set_footer(text=f"Current Jackpot: {formatfromk(int((jackpot_pot + amount)*0.95))}")
        await ctx.send(embed=embed)

    else:
        embed.add_field(name="Jackpot Added", value=f"Sorry {ctx.author.display_name}, this jackpot is only for "
                                                    f"{jackpot_currency}.")
        await ctx.send(embed=embed)
        return

    if currency == "07":
        bet = int(amount/10)
        jackpot_pot += amount
        jackpot_users.extend(ctx.author.id for _ in range(bet))
    elif currency == "rs3":
        bet = int(amount/100)
        jackpot_pot += amount
        jackpot_users.extend(ctx.author.id for _ in range(bet))


async def jackpot_game():
    global is_current_jackpot, jackpot_currency, more_than_one, jackpot_pot, jackpot_users
    await asyncio.sleep(120)

    is_current_jackpot = False
    embed = discord.Embed(color=0x0099cc)
    channel = bot.get_channel(stakeland_public)

    if not more_than_one:
        await update_money(jackpot_users[0], jackpot_pot, jackpot_currency)
        embed.add_field(name="Jackpot", value=f"There were not enough players to play a jackpot game.  You have been "
                                              f"refunded {formatfromk(jackpot_pot)} {jackpot_currency}")
        jackpot_pot = 0
        return await channel.send(embed=embed)

    tmp_currency = "rs3"
    if jackpot_currency == "07":
        tmp_currency = "osrs"
    more_than_one = False
    winner = secrets.choice(jackpot_users)
    await update_money(winner, int(jackpot_pot * 0.95), jackpot_currency)
    embed.add_field(name="Jackpot", value=f"Congratulations <@{winner}> you have won the jackpot of "
                                          f"{formatfromk(int(jackpot_pot * 0.95))}.")
    await update_money(209081432956600320, int(jackpot_pot * 0.05), f"profit_{tmp_currency}")
    await channel.send(embed=embed)
    jackpot_users = []
    jackpot_pot = 0


@bot.command()
async def bj(ctx, currency: str, amount: str):
    if ctx.author.id in current_bj_games:
        return await ctx.send(f"{ctx.author.mention}, please finish your previous Blackjack game.")
    try:
        if "." in str(Decimal(amount[:-1])) and len(str(Decimal(amount[:-1])).split(".")[1]) > 2:
            return
    except:
        if not isinstance(Decimal(amount), Decimal) and not isinstance(Decimal(amount[-1]), Decimal):
            return
    amount = formatok(amount)
    if currency != "07" and currency != "rs3":
        return
    name = ctx.author.display_name

    if not is_enough(amount, currency):
        return await not_enough(ctx, name, currency)

    if await get_value(ctx.author.id, currency) < amount:
        return await not_enough_funds(ctx, name)

    tmp_currency = "rs3"
    if currency == "07":
        tmp_currency = "osrs"

    bets_added = int(amount / 100)
    if currency == "07":
        bets_added = int(amount / 20)
    await update_money(ctx.author.id, bets_added, "bets")
    await update_money(ctx.author.id, amount, f"total_{tmp_currency}_bet")
    await update_money(ctx.author.id, amount, f"total_{tmp_currency}_weekly")
    await update_money(ctx.author.id, -amount, currency)
    current_bj_games.append(ctx.author.id)

    with open('cards.json') as json_file:
        data = json.load(json_file)

    user_cards = []
    bot_cards = []

    def get_card():
        card = secrets.choice(data["cards"])
        data["cards"].remove(card)
        return card

    def get_hand_value(values: list):
        total = 0
        ace = 0
        for card in values:
            total += int(card['value'])
            if int(card['value']) == 11:
                ace += 1
        while total > 21 and ace > 0:
            for card in values:
                if int(card['value']) == 11:
                    card['value'] = "1"
                    break
            total -= 10
            ace -= 1
        if total > 21:
            total = "BUST"
        return total

    for i in range(0, 2):
        user_cards.append(get_card())

    for i in range(0, 2):
        bot_cards.append(get_card())

    embed = discord.Embed(color=0x0099cc)
    embed.set_author(name=ctx.author.display_name, icon_url=ctx.message.author.avatar_url)
    embed.add_field(name=f"Wager: **{formatfromk(amount)} {currency}**",
                    value="Please type **hit** or **stand**", inline=False)
    embed.add_field(name="**Players Hand**",
                    value=f"{''.join([card['emoji'] for card in user_cards])}\n"
                          f"**{' + '.join([card['value'] for card in user_cards])}**\n"
                          f"Soft Value: **{get_hand_value(user_cards)}**")

    embed.add_field(name="**Dealers Hand**", value=f"{bot_cards[0]['emoji']}{back_card}\n"
                                                   f"**{bot_cards[0]['value']} + ?**\n"
                                                   f"Soft Value: **?**")
    embed.set_thumbnail(url="https://cdn.discordapp.com/icons/419994398122704896/1fed7c1147a17e9e1ed1be55c6801cf7")
    bj_game = await ctx.send(embed=embed)

    def check(m):
        return (m.content.lower() == "hit" or m.content.lower() == "stand") and m.channel == ctx.channel and \
               m.author.id == ctx.author.id

    winner = ""
    if get_hand_value(bot_cards) == 21 and get_hand_value(user_cards) == 21:
        winner = "Tie"
    elif get_hand_value(bot_cards) == 21:
        winner = "Dealer Wins"
    elif get_hand_value(user_cards) == 21:
        winner = "Player Wins"

    while get_hand_value(bot_cards) != "BUST" and get_hand_value(bot_cards) < 17:
        bot_cards.append(get_card())

    while 21 != get_hand_value(user_cards) != "BUST":
        msg = await bot.wait_for('message', check=check)

        if msg.content.lower() == "hit":
            user_cards.append(get_card())
            if get_hand_value(user_cards) == 21 or get_hand_value(user_cards) == "BUST":
                break
            get_hand_value(user_cards)
            embed = discord.Embed(color=0x0099cc)
            embed.set_author(name=ctx.author.display_name, icon_url=ctx.message.author.avatar_url)
            embed.add_field(name="Blackjack", value=f"**Wager: {formatfromk(amount)} {currency}**\n"
                                                    f"Please type **hit** or **stand**", inline=False)
            embed.add_field(name="**Players Hand**",
                            value=f"{''.join([card['emoji'] for card in user_cards])}\n"
                                  f"**{' + '.join([card['value'] for card in user_cards])}**\n"
                                  f"Value: **{get_hand_value(user_cards)}**")

            embed.add_field(name="**Dealers Hand**", value=f"{bot_cards[0]['emoji']}{back_card}\n"
                                                           f"**{bot_cards[0]['value']} + ?**\n"
                                                           f"Soft Value: **?**")
            embed.set_thumbnail(
                url="https://cdn.discordapp.com/icons/419994398122704896/1fed7c1147a17e9e1ed1be55c6801cf7")
            await bj_game.edit(embed=embed)

        elif msg.content.lower() == "stand":
            break
    if winner == "":
        if get_hand_value(user_cards) == "BUST":
            winner = "Dealer Wins"
        elif get_hand_value(user_cards) != "BUST" and get_hand_value(bot_cards) == "BUST":
            winner = "Player Wins"
        elif get_hand_value(bot_cards) == "BUST":
            winner = "Player Wins"
        elif get_hand_value(user_cards) > get_hand_value(bot_cards):
            winner = "Player Wins"
        elif get_hand_value(user_cards) < get_hand_value(bot_cards):
            winner = "Dealer Wins"
        elif get_hand_value(user_cards) == get_hand_value(bot_cards):
            winner = "Tie"
        else:
            winner = "Dealer Wins"

    payout = formatfromk(amount * 2)
    if winner == "Dealer Wins":
        payout = 0
        await update_money(ctx.author.id, int(amount), f"profit_{tmp_currency}")
        embed = discord.Embed(color=0xff0000)
    elif winner == "Tie":
        payout = formatfromk(amount)
        await update_money(ctx.author.id, amount, currency)
        embed = discord.Embed(color=0x0099cc)
    else:
        await update_money(ctx.author.id, -int(amount), f"profit_{tmp_currency}")
        await update_money(ctx.author.id, int(amount * 2), currency)
        embed = discord.Embed(color=0x00ff00)

    embed.set_author(name=ctx.author.display_name, icon_url=ctx.message.author.avatar_url)
    embed.add_field(name="Blackjack", value=f"Results: **{winner}**\n"
                                            f"Wager: **{formatfromk(amount)} {currency}** - "
                                            f"Payout: {payout} {currency}", inline=False)
    embed.add_field(name="**Players Hand**",
                    value=f"{''.join([card['emoji'] for card in user_cards])}\n"
                          f"**{' + '.join([card['value'] for card in user_cards])}**\n"
                          f"Value: **{get_hand_value(user_cards)}**")

    embed.add_field(name="**Dealers Hand**", value=f"{''.join([card['emoji'] for card in bot_cards])}\n"
                                                   f"**{' + '.join([card['value'] for card in bot_cards])}**\n"
                                                   f"Value: **{get_hand_value(bot_cards)}**")
    embed.set_thumbnail(url="https://cdn.discordapp.com/icons/419994398122704896/1fed7c1147a17e9e1ed1be55c6801cf7")
    await bj_game.edit(embed=embed)
    current_bj_games.remove(ctx.author.id)


@bot.command()
async def swap(ctx, currency: str, amount: str):
    if ctx.author.id in current_swaps:
        return await ctx.send(f"{ctx.author.mention}, please finish your older swap request.")

    try:
        if "." in str(Decimal(amount[:-1])) and len(str(Decimal(amount[:-1])).split(".")[1]) > 2:
            return
    except:
        if not isinstance(Decimal(amount), Decimal) and not isinstance(Decimal(amount[-1]), Decimal):
            return
    amount = formatok(amount)
    if currency != "07" and currency != "rs3":
        return

    name = ctx.author.display_name

    if await get_value(ctx.author.id, currency) < amount:
        return await not_enough_funds(ctx, name)

    current_swaps.append(ctx.author.id)
    await update_money(ctx.author.id, -amount, currency)
    original_amount = amount
    other_currency = "07"

    if currency == "07":
        amount *= osrs_rs3_rate
        other_currency = "rs3"

    else:
        amount /= rs3_osrs_rate
    amount = int(amount)

    embed = discord.Embed(color=0x0099cc)
    embed.add_field(name="Swapping", value=f"For {formatfromk(original_amount)} {currency} you will recieve "
                                           f"{formatfromk(amount)} {other_currency}\nType **accept** to confirm or "
                                           f"**decline** to cancel")
    await ctx.send(embed=embed)

    def check(m):
        return (m.content.lower() == "accept" or m.content.lower() == "decline") and m.channel == ctx.channel and \
               m.author.id == ctx.author.id

    msg = await bot.wait_for('message', check=check)
    current_swaps.remove(ctx.author.id)
    if msg.content.lower() == "accept":
        await update_money(ctx.author.id, amount, other_currency)

        embed = discord.Embed()
        embed.set_author(name=name)
        embed.add_field(name="Swapping Request", value=f"You have swapped {formatfromk(original_amount)} {currency} "
                                                       f"for {formatfromk(amount)} {other_currency}.\n")
        await ctx.send(embed=embed)

    elif msg.content.lower() == "decline":
        await update_money(ctx.author.id, original_amount, currency)

        embed = discord.Embed()
        embed.set_author(name=name)
        embed.add_field(name="Swapping Request", value=f"You have declined the request.\n{formatfromk(original_amount)}"
                                                       f" {currency} has been refunded.")
        await ctx.send(embed=embed)


@bot.command(aliases=["stats"])
async def wager(ctx, member: discord.Member = None):
    user = ctx.author
    if member is not None and member is not ctx.author:
        user = member

    total_osrs_bet = formatfromk(await get_value(user.id, "total_osrs_bet"))
    total_rs3_bet = formatfromk(await get_value(user.id, "total_rs3_bet"))

    embed = discord.Embed(color=0x0099cc)
    embed.set_author(name=user.display_name)
    embed.add_field(name="RS3 Wager", value=str(total_rs3_bet), inline=True)
    embed.add_field(name="07 Wager", value=str(total_osrs_bet), inline=True)
    await ctx.send(embed=embed)


@bot.command()
async def thisweek(ctx, member: discord.Member = None):
    user = ctx.author

    if member is not None and member is not ctx.author:
        user = member

    total_osrs_bet = formatfromk(await get_value(user.id, "total_osrs_weekly"))
    total_rs3_bet = formatfromk(await get_value(user.id, "total_rs3_weekly"))

    embed = discord.Embed(color=0x0099cc)
    embed.set_author(name=user.display_name)
    embed.add_field(name="RS3 Wager", value=str(total_rs3_bet), inline=True)
    embed.add_field(name="07 Wager", value=str(total_osrs_bet), inline=True)
    await ctx.send(embed=embed)


@bot.command(aliases=["competitionwager"])
async def topwager(ctx, currency: str):
    if currency != "07" and currency != "rs3":
        return

    tmp_currency = "total_rs3_bet"
    if currency == "07":
        tmp_currency = "total_osrs_bet"

    async with bot.db.acquire() as conn:
        records = await conn.fetch(f"SELECT * FROM rsmoney order by {tmp_currency} desc limit 5")

    count = 0
    users = ""
    values = ""
    tz = timezone('EST')
    today = datetime.now(tz)
    today = datetime.strptime(str(today).split(".")[0], '%Y-%m-%d %H:%M:%S')
    day = str(today.date())
    dt = datetime.strptime(day, '%Y-%m-%d')
    start = dt - timedelta(days=dt.weekday())
    end = start + timedelta(days=6, hours=17)
    difference = str(end - today)
    days = difference.split(",")[0] + " "
    if "," in str(difference):
        if int(str(days).split(" ")[0]) == 0:
            days = ""
        elif int(str(days).split(" ")[0]) < 0:
            days = "6 days"
    else:
        days = ""
    try:
        try:
            hours = difference.split(",")[1].split(":")[0] + " hours "
        except:
            hours = difference.split(":")[0] + " hours "
    except:
        hours = ""
    try:
        minutes = difference.split(":")[1] + " minutes "
    except:
        minutes = ""
    try:
        seconds = difference.split(":")[2] + " seconds "
    except:
        seconds = ""
    difference = f"{days}{hours}{minutes}{seconds}"

    for record in records:
        count += 1
        msg = formatfromk(record[tmp_currency])
        users += f"{count} <@{record['id']}>\n"
        values += f"{msg}\n"
    embed = discord.Embed(color=0x0099cc)
    embed.set_author(name=f"Competition {currency}")
    embed.add_field(name="**User**", value=users, inline=True)
    embed.add_field(name="**Amount Bet**", value=values, inline=True)
    embed.set_footer(text=difference)
    await ctx.send(embed=embed)


@bot.command(aliases=["competition"])
async def top(ctx, currency: str):
    if currency != "07" and currency != "rs3" and currency != "total":
        return

    tz = timezone('EST')
    today = datetime.now(tz)
    today = datetime.strptime(str(today).split(".")[0], '%Y-%m-%d %H:%M:%S')
    day = str(today.date())
    dt = datetime.strptime(day, '%Y-%m-%d')
    start = dt - timedelta(days=dt.weekday())
    end = start + timedelta(days=6, hours=17)
    difference = str(end - today)
    days = difference.split(",")[0] + " "
    if "," in str(difference):
        if int(str(days).split(" ")[0]) == 0:
            days = ""
        elif int(str(days).split(" ")[0]) < 0:
            days = "6 days"
    else:
        days = ""
    try:
        try:
            hours = difference.split(",")[1].split(":")[0] + " hours "
        except:
            hours = difference.split(":")[0] + " hours "
    except:
        hours = ""
    try:
        minutes = difference.split(":")[1] + " minutes "
    except:
        minutes = ""
    try:
        seconds = difference.split(":")[2] + " seconds "
    except:
        seconds = ""
    difference = f"{days}{hours}{minutes}{seconds}"

    if currency == "total":
        currency = "Total"
        top_overall = {}
        async with bot.db.acquire() as conn:
            top_osrs = await conn.fetch(f"SELECT * FROM rsmoney order by total_osrs_weekly desc limit 5")
        async with bot.db.acquire() as conn:
            top_rs3 = await conn.fetch(f"SELECT * FROM rsmoney order by total_rs3_weekly desc limit 5")
        for tops in top_osrs:
            top_overall[tops['id']] = 6 * tops['total_osrs_weekly']
            top_overall[tops['id']] += tops['total_rs3_weekly']
        for tops in top_rs3:
            if tops['id'] not in top_overall:
                top_overall[tops['id']] = 6 * tops['total_osrs_weekly']
                top_overall[tops['id']] += tops['total_rs3_weekly']

        top_overall = sorted(top_overall.items(), key=operator.itemgetter(1), reverse=True)
        count = 0
        users = ""
        values = ""
        for tops in top_overall:
            count += 1
            if count > 5:
                break
            msg = formatfromk(tops[1])
            users += f"{count} <@{tops[0]}>\n"
            values += f"{msg}\n"

    else:
        tmp_currency = "total_rs3_weekly"
        if currency == "07":
            tmp_currency = "total_osrs_weekly"
        async with bot.db.acquire() as conn:
            records = await conn.fetch(f"SELECT * FROM rsmoney order by {tmp_currency} desc limit 5")
        count = 0
        users = ""
        values = ""
        for record in records:
            count += 1
            msg = formatfromk(record[tmp_currency])
            users += f"{count} <@{record['id']}>\n"
            values += f"{msg}\n"
    embed = discord.Embed(color=0x0099cc)
    embed.set_author(name=f"Top Wagers {currency}")
    embed.add_field(name="**User**", value=users, inline=True)
    embed.add_field(name="**Amount Bet**", value=values, inline=True)
    embed.set_footer(text=difference)
    await ctx.send(embed=embed)


@bot.command()
async def rates(ctx):
    await ctx.send(f"RS3 to 07: {rs3_osrs_rate}-1\n07 to RS3: 1-{osrs_rs3_rate}")


@bot.command()
@commands.check(is_staky)
async def profit(ctx):
    async with bot.db.acquire() as conn:
        profits_rs3 = await conn.fetchrow(f"SELECT profit_rs3 FROM server")
    async with bot.db.acquire() as conn:
        profits_osrs = await conn.fetchrow(f"SELECT profit_osrs FROM server")
    embed = discord.Embed(color=0x0099cc)
    embed.set_author(name="Stakeland Profit")
    embed.add_field(name="RS3 Profit", value=formatfromk(profits_rs3["profit_rs3"]))
    embed.add_field(name="07 Profit", value=formatfromk(profits_osrs["profit_osrs"]), inline=True)
    await ctx.send(embed=embed)


@bot.command()
@commands.check(is_staky)
async def bank(ctx):
    async with bot.db.acquire() as conn:
        profits_rs3 = await conn.fetchrow(f"SELECT profit_rs3_total FROM server")
    async with bot.db.acquire() as conn:
        profits_osrs = await conn.fetchrow(f"SELECT profit_osrs_total FROM server")
    embed = discord.Embed(color=0x0099cc)
    embed.set_author(name="Stakeland Profit")
    embed.add_field(name="RS3 Total Profit", value=formatfromk(profits_rs3["profit_rs3_total"]))
    embed.add_field(name="07 Total Profit", value=formatfromk(profits_osrs["profit_osrs_total"]), inline=True)
    await ctx.send(embed=embed)


@bot.command()
async def about(ctx):
    info = await bot.application_info()
    embed = discord.Embed(color=0xffff00)
    embed.set_author(name=f"{info.name}, created by {info.owner.name}#{info.owner.discriminator}")
    embed.add_field(name="HELP", value="My help command created by:\n"
                                       "-Tmpod#0836 https://gitlab.com/Tmpod \n"
                                       "-Aika#7235 https://gitlab.com/koyagami")
    await ctx.send(embed=embed)


@bot.command()
@commands.check(is_staky)
async def t(ctx, *, message: str):
    embed = discord.Embed(color=0xffff00)
    embed.description = message
    await ctx.send(embed=embed)


bot.load_extension("libneko.extras.superuser")
bot.load_extension("libneko.extras.help")
# bot.load_extension("help")
bot.loop.create_task(my_background_task())
bot.run(TOKEN)
# https://discordapp.com/oauth2/authorize?client_id=502940842143514633&scope=bot&permissions=1074261056
