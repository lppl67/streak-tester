import discord
from discord.ext.commands import Bot
import os
import asyncpg
import ssl
import json
from decimal import Decimal
import time
# import requests
# from discord.ext import commands
# import secrets
# import asyncio
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


async def update_wager(ctx, member: discord.Member, amount: int, currency: str):
    await update_money(member.id, amount, currency)
    embed = discord.Embed(color=0x0099cc)
    embed.set_author(name=member.display_name, icon_url=member.avatar_url)
    embed.add_field(name=f"Wager Update", value=f"Successfully added {format_from_k(amount)} {currency} to "
                                                f"{member.display_name}'s wager.")
    await ctx.send(embed=embed)


# @commands.check(is_host)
@bot.command()
async def g(ctx, member: discord.Member, amount: int):
    with open('keys.json') as json_file:
        data = json.load(json_file)

    for keys in data["keys"]:
        if keys["prefix"] == ctx.prefix:
            return await update_wager(ctx, member, amount * int(keys["value"]), keys["currency"])


# @commands.check(is_host)
@bot.command()
async def gb(ctx, box: str, amount: int, member: discord.Member):

    if ctx.prefix == "!" and box == "p":
        return await update_wager(ctx, member, amount * 175, "07")

    elif ctx.prefix == "-" and box == "a":
        return await update_wager(ctx, member, amount * 500, "07")

    elif ctx.prefix == ">" and box == "d":
        return await update_wager(ctx, member, amount * 2800, "07")

    elif ctx.prefix == "+" and box == "j":
        await update_wager(ctx, member, amount * 4100, "07")


# @commands.check(is_host)
@bot.command()
async def dd(ctx, first_user: discord.Member, second_user: discord.Member, amount: str):
    if not isinstance(Decimal(amount), Decimal):
        return
    amount = int(format_to_k(amount) / 2)
    await update_money(first_user.id, amount, "07")
    await update_money(second_user.id, amount, "07")
    embed = discord.Embed(color=0x0099cc)
    embed.add_field(name="Wager Update", value=f"{format_from_k(amount)} 07 wager was added to "
                                               f"{first_user.display_name} and {second_user.display_name}.")
    await ctx.send(embed=embed)


bot.load_extension("libneko.extras.superuser")
bot.load_extension("libneko.extras.help")
bot.run(TOKEN)
# https://discordapp.com/oauth2/authorize?client_id=502940842143514633&scope=bot&permissions=0
