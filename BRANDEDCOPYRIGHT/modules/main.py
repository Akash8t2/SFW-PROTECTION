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
import re
from collections import defaultdict, deque

from config import OWNER_ID, BOT_USERNAME, LOG_CHANNEL
from BRANDEDCOPYRIGHT import BRANDEDCOPYRIGHT as app
from BRANDEDCOPYRIGHT.helper.utils import time_formatter

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Constants
FLOOD_LIMIT = 5
FLOOD_WINDOW = 10
FORBIDDEN_KEYWORDS = [
    "porn", "xxx", "sex", "ncert", "xii", "page", "ans",
    "meiotic", "divisions", "system.in", "scanner", "void",
    "nextint", "fuck", "nude", "class 12", "exam leak"
]

# State variables
enabled_protection = True
STICKER_BLOCK = True
APPROVED_USERS = defaultdict(set)
start_time = time.time()
_user_messages = defaultdict(lambda: deque())

async def log_event(client: Client, text: str, msg: Message = None):
    log_text = f"📝 {text}"
    if msg:
        log_text += f"\n• User: {msg.from_user.id} ({msg.from_user.mention})"
        log_text += f"\n• Chat: {msg.chat.id} ({msg.chat.title})"
        log_text += f"\n• Content: {msg.text or msg.caption or 'Media'}"
    try:
        await client.send_message(LOG_CHANNEL, log_text)
    except Exception as e:
        logger.error(f"Failed to log event: {e}")

async def is_admin(client: Client, chat_id: int, user_id: int) -> bool:
    """Enhanced admin check with anonymous support"""
    try:
        if user_id == OWNER_ID:
            return True

        member = await client.get_chat_member(chat_id, user_id)
        logger.info(f"Admin Check Result: {member}")
        
        return any([
            member.status in ("creator", "administrator"),
            getattr(member, "is_anonymous", False),
            (member.user and member.user.is_self)
        ])
    except Exception as e:
        logger.error(f"Admin check error: {str(e)}")
        return False

# Start & Help texts
start_txt = """<b>🔱【 𝗦𝐅𝗪 】 𝗣𝗥𝗢𝗧𝗘𝗖𝗧𝗜𝗢𝗡 🔱</b>

Protect your community with premium guard at your service.

💎 <b>Features:</b>
• 🛡️ Anti-Spam & Abuse
• 🔗 Anti-Link & Anti-Raid
• 📚 Leak & PDF Protection
• 🤖 Smart Moderation
"""

help_txt = """<b>🛠 Bot Commands:</b>

/start - Show welcome message
/help - Show this help menu
/ping - Check bot status
/protect on|off - Enable/Disable protections
/stickerban on|off - Enable/Disable sticker blocking
/approve - Allow user in this group
/disapprove - Revoke exemption
/approved - List approved users
"""

# ================= COMMAND HANDLERS ================= #

@app.on_message(filters.command("start"))
async def start_handler(_, msg: Message):
    buttons = [
        [InlineKeyboardButton("➕ Add Me", url=f"https://t.me/{BOT_USERNAME}?startgroup=true")],
        [InlineKeyboardButton("🛠 Help", callback_data="help_menu")]
    ]
    await msg.reply_photo(
        photo="https://te.legra.ph/file/344c96cb9c3ce0777fba3.jpg",
        caption=start_txt,
        reply_markup=InlineKeyboardMarkup(buttons)
    )

@app.on_callback_query(filters.regex("help_menu"))
async def help_menu(_, query: CallbackQuery):
    await query.message.edit_caption(
        help_txt,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Back", callback_data="back_to_start")]
        ])
    )

@app.on_callback_query(filters.regex("back_to_start"))
async def back_to_start(_, query: CallbackQuery):
    await start_handler(None, query.message)

@app.on_message(filters.command("help"))
async def help_command(_, msg: Message):
    await msg.reply(help_txt)

@app.on_message(filters.command("ping"))
async def ping_handler(_, msg: Message):
    uptime = time_formatter((time.time() - start_time) * 1000)
    cpu = psutil.cpu_percent()
    mem = psutil.virtual_memory()
    reply = (
        f"⚡ <b>Bot Status</b>\n"
        f"• Uptime: {uptime}\n"
        f"• CPU: {cpu}%\n"
        f"• RAM: {mem.percent}%\n"
        f"• Protection: {'ON' if enabled_protection else 'OFF'}"
    )
    await msg.reply(reply)
    await log_event(app, "Ping command used", msg)

# ================= ADMIN COMMANDS ================= #

@app.on_message(filters.command("protect") & filters.group)
async def toggle_protection(client: Client, msg: Message):
    global enabled_protection
    
    logger.info(f"Protect command used by {msg.from_user.id} in {msg.chat.id}")
    
    if not await is_admin(client, msg.chat.id, msg.from_user.id):
        logger.warning(f"Unauthorized access attempt by {msg.from_user.id}")
        return await msg.reply("❌ You need admin rights to use this.")
    
    args = msg.text.split()
    if len(args) == 2:
        if args[1].lower() == "on":
            enabled_protection = True
            await msg.reply("🛡️ Protection enabled!")
            await log_event(app, "Protection enabled", msg)
        elif args[1].lower() == "off":
            enabled_protection = False
            await msg.reply("⚠️ Protection disabled!")
            await log_event(app, "Protection disabled", msg)
        else:
            await msg.reply("Usage: /protect on|off")
    else:
        await msg.reply(f"Current status: {'ENABLED' if enabled_protection else 'DISABLED'}\nUsage: /protect on|off")

@app.on_message(filters.command("stickerban") & filters.group)
async def toggle_sticker(client: Client, msg: Message):
    global STICKER_BLOCK
    
    if not await is_admin(client, msg.chat.id, msg.from_user.id):
        return await msg.reply("❌ You need admin rights to use this.")
    
    args = msg.text.split()
    if len(args) == 2:
        if args[1].lower() == "on":
            STICKER_BLOCK = True
            await msg.reply("✅ Sticker blocking enabled!")
        elif args[1].lower() == "off":
            STICKER_BLOCK = False
            await msg.reply("❌ Sticker blocking disabled!")
        else:
            await msg.reply("Usage: /stickerban on|off")
    else:
        await msg.reply(f"Current status: {'ENABLED' if STICKER_BLOCK else 'DISABLED'}\nUsage: /stickerban on|off")

# ================= PROTECTION LOGIC ================= #

def check_flood(user_id: int) -> bool:
    """Check if user is flooding"""
    now = time.time()
    _user_messages[user_id].append(now)
    
    # Remove old messages
    while _user_messages[user_id] and now - _user_messages[user_id][0] > FLOOD_WINDOW:
        _user_messages[user_id].popleft()
    
    return len(_user_messages[user_id]) > FLOOD_LIMIT

@app.on_message(filters.group & (filters.text | filters.caption))
@app.on_edited_message(filters.group & (filters.text | filters.caption))
async def message_protection(client: Client, msg: Message):
    if not enabled_protection or msg.from_user.is_bot:
        return
    
    if msg.from_user.id in APPROVED_USERS[msg.chat.id] or await is_admin(client, msg.chat.id, msg.from_user.id):
        return
    
    # Handle edited messages
    if msg.edit_date:
        await msg.delete()
        await log_event(client, "Deleted edited message", msg)
        return
    
    text = (msg.text or msg.caption or "").lower()
    
    if any(kw in text for kw in FORBIDDEN_KEYWORDS):
        await msg.delete()
        await log_event(client, "Deleted message with forbidden keyword", msg)
        return
    
    if re.search(r"https?://", text):
        await msg.delete()
        await log_event(client, "Deleted message with link", msg)
        return
    
    if check_flood(msg.from_user.id):
        await msg.delete()
        await log_event(client, "Deleted flood message", msg)
        return

@app.on_message(filters.sticker & filters.group)
async def sticker_handler(client: Client, msg: Message):
    if STICKER_BLOCK and msg.from_user.id not in APPROVED_USERS[msg.chat.id]:
        await msg.delete()
        await log_event(client, "Deleted sticker", msg)

if __name__ == "__main__":
    logger.info("Starting protection bot...")
    app.run()
