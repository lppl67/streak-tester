import discord
from discord.ext.commands import Bot
import os
import asyncpg
import ssl
import json
from decimal import Decimal
import time
import requests
from discord.ext import commands
import secrets
import asyncio
# from datetime import datetime, timedelta
# from pytz import timezone
# import operator


TOKEN = os.environ['token']  # The token is also substituted for security reasons
DATABASE_URL = os.environ['DATABASE_URL']


bot = Bot(command_prefix=["=", "!", "-", "\\", ">", "+", "(", "#"], case_insensitive=True)
client = discord.Client()


@bot.listen()
async def on_connect():
    await bot.change_presence(activity=discord.Game(name="Use .help"), status=None, afk=False)
    ctx = ssl.create_default_context(cafile='./rds-combined-ca-bundle.pem')
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    bot.db = await asyncpg.create_pool(DATABASE_URL, ssl=ctx)


async def add_member(user_id: int):
    async with bot.db.acquire() as conn:
        await conn.execute('''
        INSERT INTO rsmoney (id,total_rs3_bet,total_osrs_bet,total_osrs_weekly,total_rs3_weekly) 
        VALUES ($1, $2, $3, $4, $5)''', user_id, 0, 0, 0, 0)


async def get_value(user_id: int, value: str):
    async with bot.db.acquire() as conn:
        returned = await conn.fetchrow("SELECT * FROM rsmoney WHERE id=$1", user_id)

    if returned is None:
        await add_member(user_id)
        async with bot.db.acquire() as conn:
            returned = await conn.fetchrow("SELECT * FROM rsmoney WHERE id=$1", user_id)

    return returned[value]


async def update_money(user_id: int, amount: int, currency: str):

    async with bot.db.acquire() as conn:
        returned = await conn.fetchrow("SELECT * FROM rsmoney WHERE id=$1", user_id)

    if returned is None:
        await add_member(user_id)

    async with bot.db.acquire() as conn:
        if currency == "rs3":
            await conn.execute('''UPDATE rsmoney 
                                  SET total_rs3_bet = total_rs3_bet + $1,
                                  total_rs3_weekly = total_rs3_weekly + $2
                                  WHERE id=$3''',
                               amount, amount, user_id)
        elif currency == "07":
            await conn.execute('''UPDATE rsmoney 
                                  SET total_osrs_bet = total_osrs_bet + $1,
                                  total_osrs_weekly = total_osrs_weekly + $2
                                  WHERE id=$3''',
                               amount, amount, user_id)


def format_to_k(amount: str):
    if (amount[-1:]).lower() == "m":
        return int(Decimal(amount[:-1]) * 100)
    elif (amount[-1:]).lower() == "k":
        return int(Decimal(amount[:-1]) / 10)
    elif (amount[-1:]).lower() == "b":
        return int(Decimal(amount[:-1]) * 100_000)
    else:
        return int(Decimal(amount) * 100)


def format_from_k(amount: int):
    amount = round((amount * 0.01), 2)

    if isinstance(amount, Decimal):
        if amount.is_integer():
            amount = int(amount)
    return str(amount)+"M"


def is_host(ctx):
    return any(role.id == 498287046989709322 for role in ctx.author.roles)


def is_ment(ctx):
    return ctx.author.id == 276918858600939520 or ctx.author.id == 311772111255633920 \
           or ctx.author.id == 503176219089436672


# @commands.check(is_host)
@bot.command()
async def addwager(ctx, currency, member: discord.Member, amount: str):
    try:
        if "." in str(Decimal(amount[:-1])) and len(str(Decimal(amount[:-1])).split(".")[1]) > 2:
            return
    except:
        if not isinstance(Decimal(amount), Decimal) and not isinstance(Decimal(amount[-1]), Decimal):
            return
    if currency != "07" and currency != "rs3":
        return
    amount = format_to_k(amount)
    await update_money(member.id, amount, currency)
    embed = discord.Embed(color=0x0099cc)
    embed.set_author(name=ctx.author.display_name, icon_url=ctx.message.author.avatar_url)
    embed.add_field(name=f"Wager Update for {member.display_name}",
                    value=f"{ctx.author.display_name} has successfully added {format_from_k(amount)} {currency} to "
                          f"{member.display_name}'s wager")
    await ctx.send(embed=embed)


@bot.command()
async def wager(ctx, member: discord.Member = None):
    user = ctx.author
    if member is not None:
        user = member

    rs3_bet = await get_value(user.id, "total_rs3_bet")
    osrs_bet = await get_value(user.id, "total_osrs_bet")

    embed = discord.Embed(color=0x0099cc)
    embed.set_author(name=user.display_name, icon_url=ctx.message.author.avatar_url)
    embed.add_field(name="RS3 Wager", value=str(format_from_k(rs3_bet)), inline=True)
    embed.add_field(name="07 Wager", value=str(format_from_k(osrs_bet)), inline=True)
    await ctx.send(embed=embed)


@bot.command()
async def thisweek(ctx, member: discord.Member = None):
    user = ctx.author
    if member is not None:
        user = member

    rs3_bet = await get_value(user.id, "total_rs3_weekly")
    osrs_bet = await get_value(user.id, "total_osrs_weekly")

    embed = discord.Embed(color=0x0099cc)
    embed.set_author(name=user.display_name, icon_url=ctx.message.author.avatar_url)
    embed.add_field(name="RS3 Weekly", value=str(format_from_k(rs3_bet)), inline=True)
    embed.add_field(name="07 Weekly", value=str(format_from_k(osrs_bet)), inline=True)
    await ctx.send(embed=embed)


# @commands.check(is_ment)
@bot.command()
async def weekreset(ctx):
    async with bot.db.acquire() as conn:
        await conn.execute('''UPDATE rsmoney 
        SET total_osrs_weekly = 0,
        total_rs3_weekly = 0''')
    await ctx.send("Weekly wagers have been reset.")


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


# @commands.check(is_host)
@bot.command()
async def g(ctx, member: discord.Member, amount: int):
    with open('keys.json') as json_file:
        data = json.load(json_file)

    for keys in data["keys"]:
        if keys["prefix"] == ctx.prefix:
            amount = amount * int(keys["value"])
            currency = keys["currency"]
    await update_money(member.id, amount, currency)
    embed = discord.Embed(color=0x0099cc)
    embed.set_author(name=member.display_name, icon_url=member.avatar_url)
    embed.add_field(name=f"Wager Update", value=f"Successfully added {format_from_k(amount)} {currency} to "
                                                f"{member.display_name}'s wager.")
    await ctx.send(embed=embed)


# @commands.check(is_host)
@bot.command()
async def dd(ctx, first_user: discord.Member, second_user: discord.Member, amount: str):
    if not isinstance(Decimal(amount), Decimal):
        return
    amount = Decimal(amount)
    await update_money(first_user.id, format_to_k(amount / 2), "07")
    await update_money(second_user.id, format_to_k(amount / 2), "07")
    embed = discord.Embed(color=0x0099cc)
    embed.add_field(name="Wager Update", value=f"{amount / 2} 07 wager was added to {first_user.display_name} and "
                                               f"{second_user.display_name}.")
    await ctx.send(embed=embed)


def xp_99(current_xp: int):
    return 0 if current_xp > 13_034_431 else "{:,}".format(13_034_431 - current_xp)


# @bot.command()
async def xp(ctx, *, username: str):
    url = f'http://services.runescape.com/m=hiscore_oldschool/index_lite.ws?player={username}'
    response = requests.get(url)
    if response.status_code == requests.codes.not_found:
        not_found = "**<:error:513794294763618305> Stats weren't found, the account might not exist / is banned.**"
        await ctx.send(not_found)
    embed = discord.Embed(description="**" + response.text + "**", color=0x00FF00)
    embed.set_author(name=username,
                     icon_url="https://imgb.apk.tools/115/b/c/2/com.jagex.oldscape.android.png")
    embed.set_thumbnail(
        url="https://vignette1.wikia.nocookie.net/ikov-2/images/2/25/Unnamed_%281%29.png/revision/"
            "latest?cb=20170111043504")
    stats = response.text.split(",")
    # print(stats)
    attxp = stats[4]
    attxp1 = attxp.split("\n")
    realattxp = attxp1[0]

    del stats[0]
    del stats[1]
    del stats[2]
    for i in range(0, int(len(stats) / 2)):
        del stats[i]  # +1
    del stats[23]
    del stats[23]
    del stats[23]
    del stats[23]
    del stats[23]
    new_stats = response.text.split(",")
    stats.insert(1, new_stats[3])
    stats = [i.split("\n", 1)[0] for i in stats]

    embed = discord.Embed(description=f"<:Attack:498591810210496515> {xp_99(int(realattxp))}"
                                      f"<:Hitpoints:498591928938397707> {xp_99(int(stats[4]))}"
                                      f"<:Mining:498591929433456642> {xp_99(int(stats[15]))}"
                                      f"\n<:Strength:498592002288517121> {xp_99(int(stats[3]))}"
                                      f"<:Agility:498591795006013471> {xp_99(int(stats[17]))}"
                                      f"<:Smithing:498592002276065281> {xp_99(int(stats[14]))}"
                                      f"\n<:Defence:498591848974254083> {xp_99(int(stats[2]))}"
                                      f"<:Herblore:498591928816893954> {xp_99(int(stats[16]))}" 
                                      f"<:Fishing:498591879852589056> {xp_99(int(stats[11]))}"
                                      f"<:Ranged:498592002129133570> {xp_99(int(stats[5]))}"
                                      f"<:Thieving:498592002435186688> {xp_99(int(stats[18]))}"
                                      f"<:Cooking:498591829357494272> {xp_99(int(stats[8]))}"
                                      f"<:Prayer:498592002276065280> {xp_99(int(stats[6]))}"
                                      f"<:Crafting:498591838652071956> {xp_99(int(stats[13]))}"
                                      f"<:Firemaking:498591866258980916> {xp_99(int(stats[12]))}"
                                      f"\n<:Magic:498591928909299762> {xp_99(int(stats[7]))}"
                                      f"<:Fletching:498591893513306112> {xp_99(int(stats[10]))}"
                                      f"<:Woodcutting:498592002393243648> {xp_99(int(stats[9]))}"
                                      f"\n<:Runecrafting:498592002259156993> {xp_99(int(stats[21]))}"
                                      f"<:Slayer:498592001902510092> {xp_99(int(stats[19]))}"
                                      f"<:Farming:498591858046271498> {xp_99(int(stats[20]))}"
                                      f"<:Construction:498591820477890600> {xp_99(int(stats[23]))}" 
                                      f"<:Hunter:498591928779145217> {xp_99(int(stats[22]))}"
                                      f"<:Warding:498604407496376320>0", color=0xFF0000)
    embed.set_author(name=username,
                     icon_url="https://imgb.apk.tools/115/b/c/2/com.jagex.oldscape.android.png")
    embed.set_thumbnail(
        url="https://vignette1.wikia.nocookie.net/ikov-2/images/2/25/Unnamed_%281%29.png/revision/"
            "latest?cb=20170111043504")
    await ctx.send(embed=embed)


bot.load_extension("libneko.extras.superuser")
bot.load_extension("libneko.extras.help")
bot.run(TOKEN)
# https://discordapp.com/oauth2/authorize?client_id=502940842143514633&scope=bot&permissions=0
