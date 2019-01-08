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


TOKEN = os.environ['token']  # The token is also substituted for security reasons
DATABASE_URL = os.environ['DATABASE_URL']


bot = Bot(command_prefix=".", case_insensitive=True)
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


@bot.command()
# @commands.has_role("Host")
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


@bot.command()
# @commands.check(is_ment)
async def weekreset(ctx):
    async with bot.db.acquire() as conn:
        await conn.execute('''UPDATE rsmoney 
        SET total_osrs_weekly = 0,
        total_rs3_weekly = 0''')
    await ctx.send("Weekly wagers have been reset.")


bot.load_extension("libneko.extras.superuser")
bot.load_extension("libneko.extras.help")
bot.run(TOKEN)
# https://discordapp.com/oauth2/authorize?client_id=502940842143514633&scope=bot&permissions=0