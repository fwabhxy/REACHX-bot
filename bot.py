import discord
from discord.ext import commands
import json
import os
from datetime import datetime

TOKEN = os.environ.get("DISCORD_TOKEN")
MOD_ROLES = ["moderator", "commander", "owner"]
PAYOUT_LOG_CHANNEL = "payout-log"
DB_FILE = "wallets.json"

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = discord.Bot(intents=intents)

def load_db():
    if not os.path.exists(DB_FILE):
        return {}
    with open(DB_FILE, "r") as f:
        return json.load(f)

def save_db(data):
    with open(DB_FILE, "w") as f:
        json.dump(data, f, indent=2)

def get_wallet(user_id: str):
    db = load_db()
    if user_id not in db:
        db[user_id] = {"balance": 0, "total_earned": 0, "total_paid": 0, "username": ""}
        save_db(db)
    return db[user_id]

def update_wallet(user_id: str, data: dict):
    db = load_db()
    db[user_id] = data
    save_db(db)

def is_mod(ctx):
    return any(r.name.lower() in MOD_ROLES for r in ctx.author.roles)

@bot.event
async def on_ready():
    print(f"ReachX Bot online as {bot.user}")

@bot.slash_command(name="wallet", description="Check your wallet balance")
async def wallet(ctx):
    uid = str(ctx.author.id)
    w = get_wallet(uid)
    w["username"] = ctx.author.name
    update_wallet(uid, w)
    embed = discord.Embed(title="💰 Your ReachX Wallet", color=0x7C3AED)
    embed.add_field(name="Current Balance", value=f"₹{w['balance']:.2f}", inline=False)
    embed.add_field(name="Total Earned", value=f"₹{w['total_earned']:.2f}", inline=True)
    embed.add_field(name="Total Paid Out", value=f"₹{w['total_paid']:.2f}", inline=True)
    embed.set_footer(text=f"ReachX • {datetime.now().strftime('%d-%m-%Y')}")
    await ctx.respond(embed=embed, ephemeral=True)

@bot.slash_command(name="withdraw", description="Request your payout on payday")
async def withdraw(ctx):
    uid = str(ctx.author.id)
    w = get_wallet(uid)
    if w["balance"] <= 0:
        await ctx.respond("❌ Your wallet balance is ₹0. Nothing to withdraw!", ephemeral=True)
        return
    embed = discord.Embed(
        title="💸 Withdrawal Request",
        description=f"{ctx.author.mention} wants to withdraw **₹{w['balance']:.2f}**\n\nPlease share your UPI ID or Binance ID in this ticket.",
        color=0x7C3AED)
    await ctx.respond(embed=embed)

@bot.slash_command(name="mystats", description="View your earning stats")
async def mystats(ctx):
    uid = str(ctx.author.id)
    w = get_wallet(uid)
    embed = discord.Embed(title=f"📊 Stats — {ctx.author.display_name}", color=0x7C3AED)
    embed.add_field(name="Current Balance", value=f"₹{w['balance']:.2f}", inline=False)
    embed.add_field(name="Total Earned", value=f"₹{w['total_earned']:.2f}", inline=True)
    embed.add_field(name="Total Paid Out", value=f"₹{w['total_paid']:.2f}", inline=True)
    await ctx.respond(embed=embed, ephemeral=True)

@bot.slash_command(name="add", description="[MOD] Add amount to worker wallet")
async def add(ctx, worker: discord.Member, amount: float):
    if not is_mod(ctx):
        await ctx.respond("❌ No permission.", ephemeral=True)
        return
    if amount <= 0:
        await ctx.respond("❌ Amount must be positive.", ephemeral=True)
        return
    uid = str(worker.id)
    w = get_wallet(uid)
    w["username"] = worker.name
    w["balance"] = round(w["balance"] + amount, 2)
    w["total_earned"] = round(w["total_earned"] + amount, 2)
    update_wallet(uid, w)
    embed = discord.Embed(title="✅ Wallet Credited", color=0x22C55E)
    embed.add_field(name="Worker", value=worker.mention, inline=True)
    embed.add_field(name="Added", value=f"₹{amount:.2f}", inline=True)
    embed.add_field(name="New Balance", value=f"₹{w['balance']:.2f}", inline=True)
    embed.set_footer(text=f"By {ctx.author.name} • {datetime.now().strftime('%d-%m-%Y %I:%M %p')}")
    await ctx.respond(embed=embed)

@bot.slash_command(name="sub", description="[MOD] Subtract amount from worker wallet")
async def sub(ctx, worker: discord.Member, amount: float):
    if not is_mod(ctx):
        await ctx.respond("❌ No permission.", ephemeral=True)
        return
    uid = str(worker.id)
    w = get_wallet(uid)
    w["balance"] = round(max(0, w["balance"] - amount), 2)
    update_wallet(uid, w)
    embed = discord.Embed(title="➖ Wallet Deducted", color=0xEF4444)
    embed.add_field(name="Worker", value=worker.mention, inline=True)
    embed.add_field(name="Deducted", value=f"₹{amount:.2f}", inline=True)
    embed.add_field(name="New Balance", value=f"₹{w['balance']:.2f}", inline=True)
    await ctx.respond(embed=embed)

@bot.slash_command(name="worker_stats", description="[MOD] View any worker stats")
async def worker_stats(ctx, worker: discord.Member):
    if not is_mod(ctx):
        await ctx.respond("❌ No permission.", ephemeral=True)
        return
    uid = str(worker.id)
    w = get_wallet(uid)
    embed = discord.Embed(title=f"📊 Stats — {worker.display_name}", color=0x7C3AED)
    embed.add_field(name="Current Balance", value=f"₹{w['balance']:.2f}", inline=False)
    embed.add_field(name="Total Earned", value=f"₹{w['total_earned']:.2f}", inline=True)
    embed.add_field(name="Total Paid Out", value=f"₹{w['total_paid']:.2f}", inline=True)
    await ctx.respond(embed=embed, ephemeral=True)

@bot.slash_command(name="payday", description="[MOD] Mark worker as paid, reset wallet")
async def payday(ctx, worker: discord.Member):
    if not is_mod(ctx):
        await ctx.respond("❌ No permission.", ephemeral=True)
        return
    uid = str(worker.id)
    w = get_wallet(uid)
    if w["balance"] <= 0:
        await ctx.respond(f"❌ {worker.mention} has ₹0 balance.", ephemeral=True)
        return
    amount_paid = w["balance"]
    w["total_paid"] = round(w["total_paid"] + amount_paid, 2)
    w["balance"] = 0
    update_wallet(uid, w)
    log_channel = discord.utils.get(ctx.guild.text_channels, name=PAYOUT_LOG_CHANNEL)
    log_embed = discord.Embed(title="✅ PAYMENT CONFIRMED", color=0x22C55E)
    log_embed.add_field(name="💰 Paid User", value=worker.mention, inline=False)
    log_embed.add_field(name="💵 Amount", value=f"₹{amount_paid:.2f}", inline=True)
    log_embed.add_field(name="📅 Payday", value=datetime.now().strftime('%A %d-%m-%Y'), inline=True)
    log_embed.add_field(name="✅ Approved by", value=ctx.author.mention, inline=False)
    log_embed.set_footer(text="ReachX Payment System")
    if log_channel:
        await log_channel.send(embed=log_embed)
    await ctx.respond(embed=discord.Embed(
        description=f"✅ **₹{amount_paid:.2f}** paid to {worker.mention}. Wallet reset to ₹0.",
        color=0x22C55E))

@bot.slash_command(name="pending_withdrawals", description="[MOD] See all workers with balance")
async def pending_withdrawals(ctx):
    if not is_mod(ctx):
        await ctx.respond("❌ No permission.", ephemeral=True)
        return
    db = load_db()
    pending = [(uid, data) for uid, data in db.items() if data.get("balance", 0) > 0]
    if not pending:
        await ctx.respond("✅ No pending withdrawals!", ephemeral=True)
        return
    pending.sort(key=lambda x: x[1]["balance"], reverse=True)
    embed = discord.Embed(title="💸 Pending Withdrawals", color=0x7C3AED)
    total = 0
    for uid, data in pending:
        embed.add_field(name=data.get("username", uid), value=f"₹{data['balance']:.2f}", inline=True)
        total += data["balance"]
    embed.set_footer(text=f"Total Pending: ₹{total:.2f}")
    await ctx.respond(embed=embed, ephemeral=True)

@bot.slash_command(name="leaderboard", description="Top earners leaderboard")
async def leaderboard(ctx):
    db = load_db()
    if not db:
        await ctx.respond("No data yet!", ephemeral=True)
        return
    sorted_workers = sorted(db.items(), key=lambda x: x[1].get("total_earned", 0), reverse=True)[:10]
    embed = discord.Embed(title="🏆 ReachX Leaderboard", color=0x7C3AED)
    medals = ["🥇", "🥈", "🥉"]
    for i, (uid, data) in enumerate(sorted_workers):
        medal = medals[i] if i < 3 else f"#{i+1}"
        embed.add_field(name=f"{medal} {data.get('username', 'Unknown')}", value=f"₹{data.get('total_earned', 0):.2f}", inline=False)
    await ctx.respond(embed=embed)

bot.run(TOKEN)
