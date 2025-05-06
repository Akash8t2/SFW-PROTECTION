from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery, Message
import os, time, psutil, platform, logging, re
from collections import defaultdict, deque
from config import OWNER_ID, BOT_USERNAME, LOG_CHANNEL
from BRANDEDCOPYRIGHT import BRANDEDCOPYRIGHT as app

# Configure logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

# Constants
FLOOD_LIMIT = 5          # messages
FLOOD_WINDOW = 10        # seconds

# start text
start_txt = """<b>🔱【 𝗦𝐅𝗪 】 𝗦𝗘𝗖𝗨𝗥𝗜𝗧𝗬 𝗥𝗢𝗕𝗢𝗧🔱</b>

Welcome to the ultimate guardian of ミ【 𝗦𝐅𝗪 】𝗖𝗢𝗠𝗠𝗨𝗡𝗜𝗧𝗬 彡 — where cutting-edge protection meets premium style.

💎 <b>Our Elite Features:</b>
• 🛡️ 24/7 Anti-Spam & Anti-Abuse Shield  
• 📝 Copyright Protection & Content Safety  
• 🤖 AI-Driven Smart Moderation  
• ⚡ Lightning-Fast Issue Resolution  
• 🔐 Role-Based Access & Audit Logging  

✨ <b>Why Choose Us?</b>
• Zero Downtime, Constant Vigilance  
• Custom Rules & Whitelists  
• VIP Support via @SFW_COMMUNITY @SFW_BotCore
• Built for Security Connoisseurs  

<b>Ready to elevate your group’s security?</b>  
Tap any concern or command — and experience premium peace of mind.  

<b>Powered by ミ【 𝗦𝐅𝗪 】𝗖𝗢𝗠𝗠𝗨𝗡𝗜𝗧𝗬 彡</b>"""

# Uptime tracking
start_time = time.time()

# Flood tracking
_user_messages = defaultdict(lambda: deque())

# Forbidden keywords list
FORBIDDEN_KEYWORDS = [
    "porn", "xxx", "sex", "ncert", "xii", "page", "ans",
    "meiotic", "divisions", "system.in", "scanner", "void",
    "nextint", "fuck", "nude", "class 12", "exam leak"
]

async def log_event(client, text: str):
    try:
        await client.send_message(LOG_CHANNEL, text)
    except Exception as e:
        logging.error(f"Failed to log event: {e}")

# Handlers
@app.on_message(filters.command("start"))
async def start_handler(_, msg: Message):
    buttons = [
        [InlineKeyboardButton("Add Me", url=f"https://t.me/{BOT_USERNAME}?startgroup=true")],
        [InlineKeyboardButton("Help", callback_data="help_menu")]
    ]
    await msg.reply_photo(
        photo="https://te.legra.ph/file/344c96cb9c3ce0777fba3.jpg",
        caption=start_txt,
        reply_markup=InlineKeyboardMarkup(buttons),
        disable_notification=True
    )

@app.on_callback_query(filters.regex("help_menu"))
async def help_menu(_, query: CallbackQuery):
    help_text = """<b>🛠 Bot Commands:</b>

/start - Show welcome
/help - Show help
/ping - Bot status
/protect on|off - Toggle protections
"""
    await query.message.edit_caption(
        help_text,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("Back", callback_data="back_to_start")]
        ])
    )

@app.on_callback_query(filters.regex("back_to_start"))
async def back_to_start(_, query: CallbackQuery):
    await start_handler(None, query.message)

@app.on_message(filters.command("help"))
async def help_command(_, msg: Message):
    await msg.reply(start_txt, quote=True)

@app.on_message(filters.command("ping"))
async def ping_handler(_, msg: Message):
    uptime = time_formatter((time.time() - start_time) * 1000)
    cpu = psutil.cpu_percent()
    storage = psutil.disk_usage('/')
    python_version = platform.python_version()
    reply = (
        f"➪ Uptime: {uptime}\n"
        f"➪ CPU: {cpu}%\n"
        f"➪ Disk Total: {storage.total//(1024**2)} MB\n"
        f"➪ Disk Used: {storage.used//(1024**2)} MB\n"
        f"➪ Disk Free: {storage.free//(1024**2)} MB\n"
        f"➪ Python: {python_version}"
    )
    await msg.reply(reply, quote=True)
    await log_event(app, f"Ping by {msg.from_user.mention}")

# Toggle protection state
enabled_protection = True
@app.on_message(filters.command("protect") & filters.user(OWNER_ID))
async def toggle_protection(_, msg: Message):
    global enabled_protection
    arg = msg.text.split(maxsplit=1)
    if len(arg) == 2 and arg[1].lower() in ["on", "off"]:
        enabled_protection = (arg[1].lower() == "on")
        status = "enabled" if enabled_protection else "disabled"
        await msg.reply(f"Protection {status}.")
    else:
        await msg.reply("Usage: /protect on|off")

# Protection checks
async def check_flood(msg: Message):
    dq = _user_messages[msg.from_user.id]
    now = time.time()
    dq.append(now)
    while dq and now - dq[0] > FLOOD_WINDOW:
        dq.popleft()
    return len(dq) > FLOOD_LIMIT

@app.on_message(filters.group & filters.text)
async def protection_handler(_, msg: Message):
    if not enabled_protection:
        return

    text = (msg.text or msg.caption or "").lower()

    # Keyword block
    for kw in FORBIDDEN_KEYWORDS:
        if kw in text:
            await msg.delete()
            warn = f"{msg.from_user.mention}, forbidden content."
            await msg.reply(warn)
            await log_event(app, f"Keyword '{kw}' blocked from {msg.from_user.mention}")
            return

    # Link block
    if re.search(r"https?://", text):
        await msg.delete()
        await msg.reply(f"{msg.from_user.mention}, links are not allowed.")
        await log_event(app, f"Link blocked from {msg.from_user.mention}")
        return

    # Flood block
    if await check_flood(msg):
        await msg.delete()
        await msg.reply(f"{msg.from_user.mention}, you're sending too fast.")
        await log_event(app, f"Flood detected from {msg.from_user.mention}")
        return

    # Forward block
    if msg.forward_from or msg.forward_date:
        await msg.delete()
        await msg.reply(f"{msg.from_user.mention}, no forwards allowed.")
        await log_event(app, f"Forward blocked from {msg.from_user.mention}")
        return

# Prevent edited messages
@app.on_edited_message(filters.group & ~filters.me)
async def edited_message(_, msg: Message):
    await log_event(app, f"Edited msg deleted from {msg.from_user.mention}")
    await msg.delete()

# Prevent long private messages
def is_long_message(_, msg: Message):
    return msg.text and len(msg.text.split()) > 10

@app.on_message(filters.private & filters.text & is_long_message)
async def long_message(_, msg: Message):
    await msg.delete()
    reply = f"Hey {msg.from_user.mention}, please keep it short!"
    await app.send_message(msg.chat.id, reply)
    await log_event(app, f"Long private msg from {msg.from_user.mention}")

# Block PDF uploads
@app.on_message(filters.document & filters.group)
async def block_pdf(_, msg: Message):
    if msg.document.mime_type == "application/pdf":
        await msg.reply("PDFs are not allowed.")
        await msg.delete()
        await log_event(app, f"PDF blocked from {msg.from_user.mention}")

# Placeholder for media handling
@app.on_message(filters.media)
async def media_handler(_, msg: Message):
    # Optional: scan or log media
    pass

if __name__ == "__main__":
    app.run()

