import logging
import sqlite3
import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from dotenv import load_dotenv
import os

load_dotenv()
TOKEN = os.getenv("TELEGRAM_TOKEN")

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

conn = sqlite3.connect("wallets.db")
c = conn.cursor()
c.execute("""CREATE TABLE IF NOT EXISTS wallets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                address TEXT,
                network TEXT
            )""")
conn.commit()

def get_balance(network, address):
    try:
        if network.lower() == "btc":
            r = requests.get(f"https://api.blockcypher.com/v1/btc/main/addrs/{address}/balance")
            data = r.json()
            return data.get("final_balance", 0)/1e8
        elif network.lower() == "eth":
            r = requests.get(f"https://api.etherscan.io/api?module=account&action=balance&address={address}&tag=latest&apikey=")
            data = r.json()
            return int(data.get("result",0))/1e18
        else:
            return None
    except:
        return None

from time import time
def calculate_abandonment_score(transactions_count, last_tx_timestamp):
    if transactions_count==0:
        return 1
    days_since_last_tx=(time()-last_tx_timestamp)/86400
    score=min(days_since_last_tx/365,1)
    return round(score,2)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Welcome to Wallet Finder Bot! Use /help to see commands.")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg="/add_address <network> <wallet_address> - Add wallet\n"
    msg+="/list_wallets - List your wallets\n"
    msg+="/scan_address <network> <wallet_address> - Scan a wallet\n"
    msg+="/delete_wallet <wallet_id> - Remove a wallet"
    await update.message.reply_text(msg)

async def add_address(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_id=update.message.from_user.id
        network=context.args[0].upper()
        address=context.args[1]
        c.execute("INSERT INTO wallets (user_id,address,network) VALUES (?,?,?)",(user_id,address,network))
        conn.commit()
        await update.message.reply_text(f"✅ Wallet {address} on {network} added!")
    except:
        await update.message.reply_text("❌ Usage: /add_address <network> <wallet_address>")

async def list_wallets(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id=update.message.from_user.id
    c.execute("SELECT id,network,address FROM wallets WHERE user_id=?",(user_id,))
    rows=c.fetchall()
    if not rows:
        await update.message.reply_text("You have no wallets saved.")
        return
    msg="💼 Your wallets:\n"
    for row in rows:
        msg+=f"{row[0]}. [{row[1]}] {row[2]}\n"
    await update.message.reply_text(msg)

async def delete_wallet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        wallet_id=int(context.args[0])
        c.execute("DELETE FROM wallets WHERE id=?",(wallet_id,))
        conn.commit()
        await update.message.reply_text(f"🗑 Wallet {wallet_id} deleted.")
    except:
        await update.message.reply_text("❌ Usage: /delete_wallet <wallet_id>")

async def scan_address(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        network=context.args[0].upper()
        address=context.args[1]
        balance=get_balance(network,address)
        transactions_count=0
        last_tx_timestamp=0
        abandonment_score=calculate_abandonment_score(transactions_count,last_tx_timestamp)
        msg=f"📊 Wallet Report:\nNetwork: {network}\nAddress: {address}\nBalance: {balance}\nTransactions: {transactions_count}\nAbandonment Score: {abandonment_score}"
        await update.message.reply_text(msg)
    except:
        await update.message.reply_text("❌ Usage: /scan_address <network> <wallet_address>")

from telegram.ext import ApplicationBuilder, CommandHandler

app=ApplicationBuilder().token(TOKEN).build()
app.add_handler(CommandHandler("start",start))
app.add_handler(CommandHandler("help",help_command))
app.add_handler(CommandHandler("add_address",add_address))
app.add_handler(CommandHandler("list_wallets",list_wallets))
app.add_handler(CommandHandler("delete_wallet",delete_wallet))
app.add_handler(CommandHandler("scan_address",scan_address))

print("Bot started...")
app.run_polling()
