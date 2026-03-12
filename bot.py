import discord
from discord.ext import commands
from discord import app_commands
import json
import os
from datetime import datetime

# ── Config ──
TOKEN = os.environ.get("DISCORD_TOKEN")
MOD_ROLES = ["moderator", "commander", "owner"]  # roles that can use mod commands
PAYOUT_LOG_CHANNEL = "payout-log"  # channel name for payment logs

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

DB_FILE = "wallets.json"

# ── DB helpers ──
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

def is_mod(interaction: discord.Interaction):
    return any(r.name.lower() in MOD_ROLES for r in interaction.user.roles)

# ── Bot Ready ──
@bot.event
async def on_ready():
    await tree.sync()
    print(f"ReachX Bot online as {bot.user}")

# ════════════════════════════════
# WORKER COMMANDS
# ════════════════════════════════

@tree.command(name="wallet", description="Check your wallet balance")
async def wallet(interaction: discord.Interaction):
    uid = str(interaction.user.id)
    w = get_wallet(uid)
    w["username"] = interaction.user.name
    update_wallet(uid, w)

    embed = discord.Embed(
        title="💰 Your ReachX Wallet",
        color=0x7C3AED
    )
    embed.add_field(name="Current Balance", value=f"₹{w['balance']:.2f}", inline=False)
    embed.add_field(name="Total Earned", value=f"₹{w['total_earned']:.2f}", inline=True)
    embed.add_field(name="Total Paid Out", value=f"₹{w['total_paid']:.2f}", inline=True)
    embed.set_footer(text=f"ReachX • {datetime.now().strftime('%d-%m-%Y')}")
    await interaction.response.send_message(embed=embed, ephemeral=True)


@tree.command(name="withdraw", description="Request your payout on payday")
async def withdraw(interaction: discord.Interaction):
    uid = str(interaction.user.id)
    w = get_wallet(uid)

    if w["balance"] <= 0:
        await interaction.response.send_message(
            "❌ Your wallet balance is ₹0. Nothing to withdraw!", ephemeral=True)
        return

    embed = discord.Embed(
        title="💸 Withdrawal Request",
        description=f"{interaction.user.mention} wants to withdraw **₹{w['balance']:.2f}**\n\nPlease share your UPI ID or Binance ID in this ticket to receive payment.",
        color=0x7C3AED
    )
    embed.set_footer(text="ReachX Payout System")
    await interaction.response.send_message(embed=embed)


@tree.command(name="mystats", description="View your earning stats")
async def mystats(interaction: discord.Interaction):
    uid = str(interaction.user.id)
    w = get_wallet(uid)

    embed = discord.Embed(
        title=f"📊 Stats — {interaction.user.display_name}",
        color=0x7C3AED
    )
    embed.add_field(name="Current Balance", value=f"₹{w['balance']:.2f}", inline=False)
    embed.add_field(name="Total Earned", value=f"₹{w['total_earned']:.2f}", inline=True)
    embed.add_field(name="Total Paid Out", value=f"₹{w['total_paid']:.2f}", inline=True)
    embed.set_footer(text=f"ReachX • {datetime.now().strftime('%d-%m-%Y')}")
    await interaction.response.send_message(embed=embed, ephemeral=True)


# ════════════════════════════════
# MOD COMMANDS
# ════════════════════════════════

@tree.command(name="add", description="[MOD] Add amount to worker's wallet")
@app_commands.describe(worker="The worker to credit", amount="Amount in INR to add")
async def add(interaction: discord.Interaction, worker: discord.Member, amount: float):
    if not is_mod(interaction):
        await interaction.response.send_message("❌ You don't have permission to use this command.", ephemeral=True)
        return
    if amount <= 0:
        await interaction.response.send_message("❌ Amount must be positive.", ephemeral=True)
        return

    uid = str(worker.id)
    w = get_wallet(uid)
    w["username"] = worker.name
    w["balance"] = round(w["balance"] + amount, 2)
    w["total_earned"] = round(w["total_earned"] + amount, 2)
    update_wallet(uid, w)

    embed = discord.Embed(
        title="✅ Wallet Credited",
        color=0x22C55E
    )
    embed.add_field(name="Worker", value=worker.mention, inline=True)
    embed.add_field(name="Added", value=f"₹{amount:.2f}", inline=True)
    embed.add_field(name="New Balance", value=f"₹{w['balance']:.2f}", inline=True)
    embed.set_footer(text=f"Approved by {interaction.user.name} • {datetime.now().strftime('%d-%m-%Y %I:%M %p')}")
    await interaction.response.send_message(embed=embed)


@tree.command(name="sub", description="[MOD] Subtract amount from worker's wallet")
@app_commands.describe(worker="The worker to deduct from", amount="Amount in INR to subtract")
async def sub(interaction: discord.Interaction, worker: discord.Member, amount: float):
    if not is_mod(interaction):
        await interaction.response.send_message("❌ You don't have permission to use this command.", ephemeral=True)
        return
    if amount <= 0:
        await interaction.response.send_message("❌ Amount must be positive.", ephemeral=True)
        return

    uid = str(worker.id)
    w = get_wallet(uid)
    w["username"] = worker.name
    w["balance"] = round(max(0, w["balance"] - amount), 2)
    update_wallet(uid, w)

    embed = discord.Embed(
        title="➖ Wallet Deducted",
        color=0xEF4444
    )
    embed.add_field(name="Worker", value=worker.mention, inline=True)
    embed.add_field(name="Deducted", value=f"₹{amount:.2f}", inline=True)
    embed.add_field(name="New Balance", value=f"₹{w['balance']:.2f}", inline=True)
    embed.set_footer(text=f"By {interaction.user.name} • {datetime.now().strftime('%d-%m-%Y %I:%M %p')}")
    await interaction.response.send_message(embed=embed)


@tree.command(name="worker_stats", description="[MOD] View any worker's stats")
@app_commands.describe(worker="The worker to check")
async def worker_stats(interaction: discord.Interaction, worker: discord.Member):
    if not is_mod(interaction):
        await interaction.response.send_message("❌ No permission.", ephemeral=True)
        return

    uid = str(worker.id)
    w = get_wallet(uid)

    embed = discord.Embed(
        title=f"📊 Stats — {worker.display_name}",
        color=0x7C3AED
    )
    embed.add_field(name="Current Balance", value=f"₹{w['balance']:.2f}", inline=False)
    embed.add_field(name="Total Earned", value=f"₹{w['total_earned']:.2f}", inline=True)
    embed.add_field(name="Total Paid Out", value=f"₹{w['total_paid']:.2f}", inline=True)
    embed.set_footer(text=f"Checked by {interaction.user.name} • {datetime.now().strftime('%d-%m-%Y')}")
    await interaction.response.send_message(embed=embed, ephemeral=True)


@tree.command(name="payday", description="[MOD] Mark worker as paid and reset wallet")
@app_commands.describe(worker="The worker who has been paid")
async def payday(interaction: discord.Interaction, worker: discord.Member):
    if not is_mod(interaction):
        await interaction.response.send_message("❌ No permission.", ephemeral=True)
        return

    uid = str(worker.id)
    w = get_wallet(uid)

    if w["balance"] <= 0:
        await interaction.response.send_message(
            f"❌ {worker.mention} has ₹0 balance — nothing to pay.", ephemeral=True)
        return

    amount_paid = w["balance"]
    w["total_paid"] = round(w["total_paid"] + amount_paid, 2)
    w["balance"] = 0
    update_wallet(uid, w)

    # Post to payout-log channel
    log_channel = discord.utils.get(interaction.guild.text_channels, name=PAYOUT_LOG_CHANNEL)

    log_embed = discord.Embed(
        title="✅ PAYMENT CONFIRMED",
        color=0x22C55E
    )
    log_embed.add_field(name="💰 Paid User", value=worker.mention, inline=False)
    log_embed.add_field(name="💵 Amount", value=f"₹{amount_paid:.2f}", inline=True)
    log_embed.add_field(name="📅 Payday", value=datetime.now().strftime('%A %d-%m-%Y'), inline=True)
    log_embed.add_field(name="✅ Approved by", value=interaction.user.mention, inline=False)
    log_embed.set_footer(text="ReachX Payment System")

    if log_channel:
        await log_channel.send(embed=log_embed)

    await interaction.response.send_message(
        embed=discord.Embed(
            description=f"✅ **₹{amount_paid:.2f}** paid to {worker.mention}. Wallet reset to ₹0.",
            color=0x22C55E
        )
    )


@tree.command(name="pending_withdrawals", description="[MOD] See all workers with pending balance")
async def pending_withdrawals(interaction: discord.Interaction):
    if not is_mod(interaction):
        await interaction.response.send_message("❌ No permission.", ephemeral=True)
        return

    db = load_db()
    pending = [(uid, data) for uid, data in db.items() if data.get("balance", 0) > 0]

    if not pending:
        await interaction.response.send_message("✅ No pending withdrawals!", ephemeral=True)
        return

    pending.sort(key=lambda x: x[1]["balance"], reverse=True)

    embed = discord.Embed(title="💸 Pending Withdrawals", color=0x7C3AED)
    total = 0
    for uid, data in pending:
        embed.add_field(
            name=data.get("username", uid),
            value=f"₹{data['balance']:.2f}",
            inline=True
        )
        total += data["balance"]

    embed.set_footer(text=f"Total Pending: ₹{total:.2f} • {datetime.now().strftime('%d-%m-%Y')}")
    await interaction.response.send_message(embed=embed, ephemeral=True)


@tree.command(name="leaderboard", description="Top earners leaderboard")
async def leaderboard(interaction: discord.Interaction):
    db = load_db()
    if not db:
        await interaction.response.send_message("No data yet!", ephemeral=True)
        return

    sorted_workers = sorted(db.items(), key=lambda x: x[1].get("total_earned", 0), reverse=True)[:10]

    embed = discord.Embed(title="🏆 ReachX Leaderboard — Top Earners", color=0x7C3AED)
    medals = ["🥇", "🥈", "🥉"]
    for i, (uid, data) in enumerate(sorted_workers):
        medal = medals[i] if i < 3 else f"#{i+1}"
        embed.add_field(
            name=f"{medal} {data.get('username', 'Unknown')}",
            value=f"Total Earned: ₹{data.get('total_earned', 0):.2f}",
            inline=False
        )
    embed.set_footer(text=f"ReachX • {datetime.now().strftime('%d-%m-%Y')}")
    await interaction.response.send_message(embed=embed)


bot.run(TOKEN)
