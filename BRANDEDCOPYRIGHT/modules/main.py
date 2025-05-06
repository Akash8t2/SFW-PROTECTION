from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery, Message
import os, time, psutil, platform, logging, re
from collections import defaultdict, deque
from BRANDEDCOPYRIGHT.helper.utils import time_formatter
from config import OWNER_ID, BOT_USERNAME, LOG_CHANNEL
from BRANDEDCOPYRIGHT import BRANDEDCOPYRIGHT as app

# Configure logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

# Constants
FLOOD_LIMIT = 5          # messages
FLOOD_WINDOW = 10        # seconds

# State variables
enabled_protection = True
STICKER_BLOCK = True
APPROVED_USERS = set()

# Start text
start_txt = """<b>🔱【 𝗦𝐅𝗪 】 𝗦𝗘𝗖𝗨𝗥𝗜𝗧𝗬 𝗥𝗢𝗕𝗢𝗧🔱</b>

Welcome to the ultimate guardian of ミ【 𝗦𝐅𝗪 】𝗖𝗢𝗠𝗠𝗨𝗡𝗜𝗧𝗬 彡 — premium protection at your service.

💎 <b>Features:</b>
• 🛡️ Anti-Spam & Abuse
• 🔗 Anti-Link & Anti-Raid
• 📚 Leak & PDF Protection
• 🤖 Smart Moderation
• ⚡ Fast Issue Resolution

✨ <b>Usage:</b>
• /help - List commands
• /ping - Bot status
"""

# Help text
help_txt = """<b>🛠 Bot Commands:</b>

/start - Show welcome message
/help - Show this help message
/ping - Check bot status
/protect on|off - Enable/Disable protections
/stickerban on|off - Enable/Disable sticker blocking
/approve <user_id|@username> or reply - Allow exemptions
/disapprove <user_id|@username> or reply - Remove exemptions
/approved - List approved users
"""

# Uptime tracking
start_time = time.time()
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

# Help menu via button
@app.on_callback_query(filters.regex("help_menu"))
async def help_menu(_, query: CallbackQuery):
    await query.message.edit_caption(
        help_txt,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Back", callback_data="back_to_start")]
        ])
    )

# Back to start via button
@app.on_callback_query(filters.regex("back_to_start"))
async def back_to_start(_, query: CallbackQuery):
    await start_handler(None, query.message)

# /help command
@app.on_message(filters.command("help"))
async def help_command(_, msg: Message):
    buttons = [[InlineKeyboardButton("🔙 Back", callback_data="back_to_start")]]
    await msg.reply(help_txt, quote=True, reply_markup=InlineKeyboardMarkup(buttons))

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

# Toggle protections
@app.on_message(filters.command("protect") & filters.user(OWNER_ID))
async def toggle_protection(_, msg: Message):
    global enabled_protection
    args = msg.text.split(maxsplit=1)
    if len(args) == 2 and args[1].lower() in ["on", "off"]:
        enabled_protection = args[1].lower() == "on"
        await msg.reply(f"🔔 Protections {'enabled' if enabled_protection else 'disabled'}.")
    else:
        await msg.reply("Usage: /protect on|off")

# Toggle sticker ban
@app.on_message(filters.command("stickerban") & filters.user(OWNER_ID))
async def toggle_sticker(_, msg: Message):
    global STICKER_BLOCK
    args = msg.text.split(maxsplit=1)
    if len(args) == 2 and args[1].lower() in ["on", "off"]:
        STICKER_BLOCK = args[1].lower() == "on"
        await msg.reply(f"🔔 Sticker blocking {'enabled' if STICKER_BLOCK else 'disabled'}.")
    else:
        await msg.reply("Usage: /stickerban on|off")

# Approve users
@app.on_message(filters.command("approve") & filters.user(OWNER_ID))
async def approve_user(_, msg: Message):
    # Determine target
    if len(msg.command) >= 2:
        target = msg.command[1]
    elif msg.reply_to_message:
        target = msg.reply_to_message.from_user.id
    else:
        return await msg.reply("Usage: /approve <user_id|@username> or reply to a user message.")
    # Resolve username
    if isinstance(target, str) and target.startswith("@"):
        try:
            user = await app.get_users(target)
            uid = user.id
        except Exception:
            return await msg.reply("Couldn't resolve that username.")
    else:
        try:
            uid = int(target)
        except ValueError:
            return await msg.reply("Invalid user ID.")
    APPROVED_USERS.add(uid)
    await msg.reply(f"✅ User `{uid}` approved and exempted.")

# Disapprove users
@app.on_message(filters.command("disapprove") & filters.user(OWNER_ID))
async def disapprove_user(_, msg: Message):
    if len(msg.command) >= 2:
        target = msg.command[1]
    elif msg.reply_to_message:
        target = msg.reply_to_message.from_user.id
    else:
        return await msg.reply("Usage: /disapprove <user_id|@username> or reply to a user message.")
    try:
        uid = int(target)
    except ValueError:
        if isinstance(target, str) and target.startswith("@"):
            try:
                user = await app.get_users(target)
                uid = user.id
            except:
                return await msg.reply("Couldn't resolve that username.")
        else:
            return await msg.reply("Invalid user ID.")
    APPROVED_USERS.discard(uid)
    await msg.reply(f"❌ User `{uid}` disapproved.")

# Show approved list
@app.on_message(filters.command("approved") & filters.user(OWNER_ID))
async def show_approved(_, msg: Message):
    text = "\n".join(str(uid) for uid in APPROVED_USERS) or "No approved users yet."
    await msg.reply(f"📝 Approved Users:\n{text}")

# Flood check helper
def check_flood(msg: Message) -> bool:
    dq = _user_messages[msg.from_user.id]
    now = time.time()
    dq.append(now)
    while dq and now - dq[0] > FLOOD_WINDOW:
        dq.popleft()
    return len(dq) > FLOOD_LIMIT

# Core protection handler
@app.on_message(filters.group & (filters.text | filters.caption))
async def protection_handler(_, msg: Message):
    if not enabled_protection:
        return
    if msg.from_user is None or msg.from_user.is_bot or msg.from_user.id in APPROVED_USERS:
        return
    text = (msg.text or msg.caption or "").lower()
    # Keyword filter
    for kw in FORBIDDEN_KEYWORDS:
        if kw in text:
            await msg.delete()
            return await msg.reply(f"{msg.from_user.mention}, forbidden content.")
    # Link filter
    if re.search(r"https?://", text):
        await msg.delete()
        return await msg.reply(f"{msg.from_user.mention}, links are not allowed.")
    # Flood filter
    if check_flood(msg):
        await msg.delete()
        return await msg.reply(f"{msg.from_user.mention}, please slow down.")
    # Forward filter
    if msg.forward_from or msg.forward_date:
        await msg.delete()
        return await msg.reply(f"{msg.from_user.mention}, forwards are disabled.")

# Sticker blocker
@app.on_message(filters.sticker & filters.group)
async def sticker_blocker(_, msg: Message):
    if not STICKER_BLOCK or msg.from_user is None or msg.from_user.is_bot or msg.from_user.id in APPROVED_USERS:
        return
    await msg.delete()

# Edited message blocker
@app.on_edited_message(filters.group)
async def edited_message(_, msg: Message):
    if msg.from_user and msg.from_user.id not in APPROVED_USERS:
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

# Placeholder for other media
@app.on_message(filters.media)
async def media_handler(_, msg: Message):
    pass

if __name__ == "__main__":
    app.run()

                
