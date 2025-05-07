import logging
from pyrogram import Client, filters
from pyrogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    CallbackQuery,
    Message,
)
from pyrogram.enums import ChatMemberStatus
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
APPROVED_USERS = defaultdict(set)  # Format: {chat_id: {user1, user2}}
start_time = time.time()
_user_messages = defaultdict(lambda: deque())

# ================= HELPER FUNCTIONS ================= #

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
    """Check if user is admin/owner in the specific group"""
    try:
        if user_id == OWNER_ID:
            return True

        member = await client.get_chat_member(chat_id, user_id)
        return member.status in (ChatMemberStatus.OWNER, ChatMemberStatus.ADMINISTRATOR)
    except Exception as e:
        logger.error(f"Admin check error: {e}")
        return False

async def is_approved_or_admin(client: Client, chat_id: int, user_id: int) -> bool:
    """Check if user is approved or admin in the specific group"""
    return user_id in APPROVED_USERS.get(chat_id, set()) or await is_admin(client, chat_id, user_id)

# ================= COMMAND HANDLERS ================= #

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

@app.on_message(filters.command("start"))
async def start_handler(_, msg: Message):
    buttons = [
        [InlineKeyboardButton("➕ Add Me", url=f"https://t.me/{BOT_USERNAME}?startgroup=true")],
        [InlineKeyboardButton("🛠 Help", callback_data="help_menu")]
    ]
    await msg.reply_photo(
        photo="https://files.catbox.moe/kirzpo.jpg",
        caption=start_txt,
        reply_markup=InlineKeyboardMarkup(buttons)
    )

@app.on_callback_query(filters.regex("help_menu"))
async def help_menu(_, query: CallbackQuery):
    await query.message.edit_caption(
        help_txt,
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="back_to_start")]])
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

@app.on_message(filters.command("approve") & filters.group)
async def approve_user(client: Client, msg: Message):
    try:
        chat_id = msg.chat.id
        if msg.reply_to_message:
            user_id = msg.reply_to_message.from_user.id
        else:
            user = msg.text.split()[1].strip()
            if user.startswith("@"):
                user_obj = await client.get_users(user)
                user_id = user_obj.id
            else:
                user_id = int(user)
        
        APPROVED_USERS[chat_id].add(user_id)
        await msg.reply(f"✅ User {user_id} approved in THIS GROUP!")
        logger.info(f"Approved {user_id} in Chat {chat_id}")
    except Exception as e:
        await msg.reply("❌ Usage: /approve @username or reply to user")

@app.on_message(filters.command("disapprove") & filters.group)
async def disapprove_user(client: Client, msg: Message):
    try:
        chat_id = msg.chat.id
        if msg.reply_to_message:
            user_id = msg.reply_to_message.from_user.id
        else:
            user_id = int(msg.text.split()[1])
        
        APPROVED_USERS[chat_id].discard(user_id)
        await msg.reply(f"❌ User {user_id} disapproved!")
    except Exception as e:
        await msg.reply("❌ Usage: /disapprove @username or reply to user")

@app.on_message(filters.command("approved") & filters.group)
async def show_approved(_, msg: Message):
    chat_id = msg.chat.id
    approved = APPROVED_USERS.get(chat_id, set())
    text = "Approved Users:\n" + "\n".join(str(u) for u in approved) if approved else "No approved users"
    await msg.reply(text)

@app.on_message(filters.command("protect") & filters.group)
async def toggle_protection(client: Client, msg: Message):
    global enabled_protection
    if not await is_admin(client, msg.chat.id, msg.from_user.id):
        return await msg.reply("❌ Admin rights required!")
    
    args = msg.text.split()
    if len(args) == 2:
        enabled_protection = args[1].lower() == "on"
        status = "ENABLED" if enabled_protection else "DISABLED"
        await msg.reply(f"🛡️ Protection {status}!")
        await log_event(client, f"Protection {status}", msg)
    else:
        await msg.reply(f"Current status: {'ENABLED' if enabled_protection else 'DISABLED'}\nUsage: /protect on|off")

@app.on_message(filters.command("stickerban") & filters.group)
async def toggle_sticker(client: Client, msg: Message):
    global STICKER_BLOCK
    if not await is_admin(client, msg.chat.id, msg.from_user.id):
        return await msg.reply("❌ Admin rights required!")
    
    args = msg.text.split()
    if len(args) == 2:
        STICKER_BLOCK = args[1].lower() == "on"
        status = "ENABLED" if STICKER_BLOCK else "DISABLED"
        await msg.reply(f"🛡️ Sticker blocking {status}!")
    else:
        await msg.reply(f"Current status: {'ENABLED' if STICKER_BLOCK else 'DISABLED'}\nUsage: /stickerban on|off")

# ================= PROTECTION LOGIC ================= #

def check_flood(user_id: int) -> bool:
    now = time.time()
    q = _user_messages[user_id]
    q.append(now)
    while now - q[0] > FLOOD_WINDOW:
        q.popleft()
    return len(q) > FLOOD_LIMIT

@app.on_message(filters.group & (filters.text | filters.caption))
async def message_protection(client: Client, msg: Message):
    if not enabled_protection or msg.from_user.is_bot:
        return
    
    chat_id = msg.chat.id
    user_id = msg.from_user.id
    
    if await is_approved_or_admin(client, chat_id, user_id):
        logger.info(f"Skipping approved/admin: {user_id} in {chat_id}")
        return
    
    text = (msg.text or msg.caption or "").lower()
    
    # Keyword check
    if any(kw in text for kw in FORBIDDEN_KEYWORDS):
        await msg.delete()
        await log_event(client, "Deleted forbidden content", msg)
        return
    
    # Link check
    if re.search(r"https?://", text):
        await msg.delete()
        await log_event(client, "Deleted link", msg)
        return
    
    # Flood check
    if check_flood(user_id):
        await msg.delete()
        await log_event(client, "Deleted flood", msg)

@app.on_edited_message(filters.group & (filters.text | filters.caption))
async def edited_message_protection(client: Client, msg: Message):
    if not enabled_protection or msg.from_user.is_bot:
        return
    
    chat_id = msg.chat.id
    user_id = msg.from_user.id
    
    if await is_approved_or_admin(client, chat_id, user_id):
        logger.info(f"Skipping edit from approved/admin: {user_id} in {chat_id}")
        return
    
    await msg.delete()
    await log_event(client, "Deleted edited message", msg)

@app.on_message(filters.sticker & filters.group)
async def sticker_handler(client: Client, msg: Message):
    if STICKER_BLOCK:
        chat_id = msg.chat.id
        user_id = msg.from_user.id
        
        if await is_approved_or_admin(client, chat_id, user_id):
            logger.info(f"Skipping sticker from approved/admin: {user_id} in {chat_id}")
            return
        
        await msg.delete()
        await log_event(client, "Deleted sticker", msg)

if __name__ == "__main__":
    logger.info("🚀 SFW Protection Bot Started!")
    app.run()
