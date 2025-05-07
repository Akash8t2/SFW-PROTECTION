import logging
from pyrogram import Client, filters
from pyrogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    CallbackQuery,
    Message,
)
import time
import psutil
import platform
import logging
import re
from collections import defaultdict, deque

from config import OWNER_ID, BOT_USERNAME, LOG_CHANNEL
from BRANDEDCOPYRIGHT import BRANDEDCOPYRIGHT as app
from BRANDEDCOPYRIGHT.helper.utils import time_formatter

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Constants
FLOOD_LIMIT = 5      # max messages
FLOOD_WINDOW = 10    # seconds window

# State variables
enabled_protection = True
STICKER_BLOCK = True
APPROVED_USERS = defaultdict(set)  # per-chat approved users

# Track uptime & flooding
start_time = time.time()
_user_messages = defaultdict(lambda: deque())

# Forbidden keywords
FORBIDDEN_KEYWORDS = [
    "porn", "xxx", "sex", "ncert", "xii", "page", "ans",
    "meiotic", "divisions", "system.in", "scanner", "void",
    "nextint", "fuck", "nude", "class 12", "exam leak"
]

async def log_event(client: Client, text: str):
    try:
        await client.send_message(LOG_CHANNEL, text)
    except Exception as e:
        logging.error(f"Failed to log event: {e}")

async def is_admin(client: Client, msg: Message) -> bool:
    member = await client.get_chat_member(msg.chat.id, msg.from_user.id)
    return member.status in ("creator", "administrator")

# Start & Help texts
start_txt = """<b>🔱【 𝗦𝐅𝗪 】 𝗣𝗥𝗢𝗧𝗘𝗖𝗧𝗜𝗢𝗡 🔱</b>

Protect your community with ミ【 𝗦𝐅𝗪 】𝗣𝗥𝗢𝗧𝗘𝗖𝗧𝗜𝗢𝗡 — premium guard at your service.

💎 <b>Features:</b>
• 🛡️ Anti-Spam & Abuse
• 🔗 Anti-Link & Anti-Raid
• 📚 Leak & PDF Protection
• 🤖 Smart Moderation
• ⚡ Fast Issue Resolution

✨ <b>Usage:</b>
• /help — List commands
• /ping — Bot status
"""

help_txt = """<b>🛠 Bot Commands:</b>

/start — Show welcome message
/help — Show this help menu
/ping — Check bot status
/protect on|off — Enable/Disable protections
/stickerban on|off — Enable/Disable sticker blocking
/approve <user_id|@username> or reply — Allow user in this group
/disapprove <user_id|@username> or reply — Revoke exemption
/approved — List approved users in this group
"""

# /start handler
@app.on_message(filters.command("start"))
async def start_handler(_, msg: Message):
    buttons = [
        [InlineKeyboardButton("➕ Add Me", url=f"https://t.me/{BOT_USERNAME}?startgroup=true")],
        [InlineKeyboardButton("🛠 Help", callback_data="help_menu")]
    ]
    await msg.reply_photo(
        photo="https://te.legra.ph/file/344c96cb9c3ce0777fba3.jpg",
        caption=start_txt,
        reply_markup=InlineKeyboardMarkup(buttons),
        disable_notification=True
    )

# Help via button
@app.on_callback_query(filters.regex("help_menu"))
async def help_menu(_, query: CallbackQuery):
    await query.message.edit_caption(
        help_txt,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Back", callback_data="back_to_start")]
        ])
    )

# Back to start
@app.on_callback_query(filters.regex("back_to_start"))
async def back_to_start(_, query: CallbackQuery):
    await start_handler(None, query.message)

# /help command
@app.on_message(filters.command("help"))
async def help_command(_, msg: Message):
    buttons = [[InlineKeyboardButton("🔙 Back", callback_data="back_to_start")]]
    await msg.reply(
        help_txt,
        quote=True,
        reply_markup=InlineKeyboardMarkup(buttons)
    )

# /ping command
@app.on_message(filters.command("ping"))
async def ping_handler(_, msg: Message):
    uptime = time_formatter((time.time() - start_time) * 1000)
    cpu = psutil.cpu_percent()
    storage = psutil.disk_usage('/')
    python_version = platform.python_version()
    reply = (
        f"➪ Uptime: {uptime}\n"
        f"➪ CPU: {cpu}%\n"
        f"➪ Disk Total: {storage.total // (1024**2)} MB\n"
        f"➪ Disk Used: {storage.used // (1024**2)} MB\n"
        f"➪ Disk Free: {storage.free // (1024**2)} MB\n"
        f"➪ Python: {python_version}"
    )
    await msg.reply(reply, quote=True)
    await log_event(app, f"Ping by {msg.from_user.mention}")

# /protect : admin or owner
@app.on_message(filters.command("protect") & filters.group)
async def toggle_protection(_, msg: Message):
    global enabled_protection
    if not (msg.from_user.id == OWNER_ID or await is_admin(app, msg)):
        return await msg.reply("❌ You need admin rights to use this.")
    parts = msg.text.split(maxsplit=1)
    if len(parts) == 2 and parts[1].lower() in ("on", "off"):
        enabled_protection = (parts[1].lower() == "on")
        status = "enabled" if enabled_protection else "disabled"
        await msg.reply(f"🔔 Protections {status}.")
    else:
        await msg.reply("Usage: /protect on|off")

# /stickerban : admin or owner
@app.on_message(filters.command("stickerban") & filters.group)
async def toggle_sticker(_, msg: Message):
    global STICKER_BLOCK
    if not (msg.from_user.id == OWNER_ID or await is_admin(app, msg)):
        return await msg.reply("❌ You need admin rights to use this.")
    parts = msg.text.split(maxsplit=1)
    if len(parts) == 2 and parts[1].lower() in ("on", "off"):
        STICKER_BLOCK = (parts[1].lower() == "on")
        status = "enabled" if STICKER_BLOCK else "disabled"
        await msg.reply(f"🔔 Sticker blocking {status}.")
    else:
        await msg.reply("Usage: /stickerban on|off")

# /approve per-group
@app.on_message(filters.command("approve") & filters.group)
async def approve_user(_, msg: Message):
    if not (msg.from_user.id == OWNER_ID or await is_admin(app, msg)):
        return await msg.reply("❌ You need admin rights to use this.")
    # resolve target
    if msg.reply_to_message:
        uid = msg.reply_to_message.from_user.id
    elif len(msg.command) >= 2:
        tgt = msg.command[1]
        if tgt.startswith("@"):
            try:
                user = await app.get_users(tgt)
                uid = user.id
            except:
                return await msg.reply("❌ Cannot resolve that username.")
        else:
            try:
                uid = int(tgt)
            except:
                return await msg.reply("❌ Invalid user ID.")
    else:
        return await msg.reply("Usage: /approve <user_id|@username> or reply.")
    APPROVED_USERS[msg.chat.id].add(uid)
    await msg.reply(f"✅ User `{uid}` approved in this group.")

# /disapprove per-group
@app.on_message(filters.command("disapprove") & filters.group)
async def disapprove_user(_, msg: Message):
    if not (msg.from_user.id == OWNER_ID or await is_admin(app, msg)):
        return await msg.reply("❌ You need admin rights to use this.")
    if msg.reply_to_message:
        uid = msg.reply_to_message.from_user.id
    elif len(msg.command) >= 2:
        try:
            uid = int(msg.command[1])
        except:
            return await msg.reply("❌ Invalid user ID.")
    else:
        return await msg.reply("Usage: /disapprove <user_id|@username> or reply.")
    APPROVED_USERS[msg.chat.id].discard(uid)
    await msg.reply(f"❌ User `{uid}` disapproved in this group.")

# /approved list
@app.on_message(filters.command("approved") & filters.group)
async def show_approved(_, msg: Message):
    if not (msg.from_user.id == OWNER_ID or await is_admin(app, msg)):
        return
    approved = APPROVED_USERS[msg.chat.id]
    txt = "\n".join(str(u) for u in approved) or "No approved users in this group."
    await msg.reply(f"📝 Approved Users for this group:\n{txt}")

# Flood helper
def check_flood(msg: Message) -> bool:
    dq = _user_messages[msg.from_user.id]
    now = time.time()
    dq.append(now)
    while dq and now - dq[0] > FLOOD_WINDOW:
        dq.popleft()
    return len(dq) > FLOOD_LIMIT

# Core protection (ignoring reactions)
@app.on_message(filters.group & (filters.text | filters.caption))
async def protection_handler(_, msg: Message):
    if getattr(msg, "reactions", None) and msg.reactions.total_count > 0:
        return
    if not enabled_protection:
        return
    if msg.from_user.is_bot or msg.from_user.id in APPROVED_USERS[msg.chat.id]:
        return
    text = (msg.text or msg.caption or "").lower()
    # keyword
    for kw in FORBIDDEN_KEYWORDS:
        if kw in text:
            await msg.delete()
            return
    # link
    if re.search(r"https?://", text):
        await msg.delete()
        return
    # flood
    if check_flood(msg):
        await msg.delete()
        return
    # forward
    if msg.forward_from or msg.forward_date:
        await msg.delete()
        return

# Sticker blocker
@app.on_message(filters.sticker & filters.group)
async def sticker_blocker(_, msg: Message):
    if getattr(msg, "reactions", None) and msg.reactions.total_count > 0:
        return
    if not STICKER_BLOCK or msg.from_user.is_bot or msg.from_user.id in APPROVED_USERS[msg.chat.id]:
        return
    await msg.delete()

# Edited message blocker
@app.on_edited_message(filters.group)
async def edited_message(_, msg: Message):
    if getattr(msg, "reactions", None) and msg.reactions.total_count > 0:
        return
    if msg.from_user.id not in APPROVED_USERS[msg.chat.id]:
        await msg.delete()

# Long private message blocker
def is_long_message(_, msg: Message) -> bool:
    return msg.text and len(msg.text.split()) > 10

@app.on_message(filters.private & filters.text & is_long_message)
async def long_message(_, msg: Message):
    await msg.delete()
    await msg.reply(f"Hey {msg.from_user.mention}, please keep it short!")

# PDF blocker
@app.on_message(filters.document & filters.group)
async def block_pdf(_, msg: Message):
    if msg.document.mime_type == "application/pdf":
        await msg.reply("PDFs are not allowed here.")
        return await msg.delete()

if __name__ == "__main__":
    app.run()


