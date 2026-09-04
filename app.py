import os
import json
import sqlite3
import asyncio
from aiohttp import web
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardMarkup,
    KeyboardButton,
    WebAppInfo,
    FSInputFile
)

BOT_TOKEN = os.getenv("BOT_TOKEN", "8993449962:AAGB8ZtkHL_b77Za4o3QuseARs5jAHLgm0E")
ADMIN_ID = int(os.getenv("ADMIN_ID", "8423151783"))
RENDER_URL = os.getenv("RENDER_EXTERNAL_URL", "")
PORT = int(os.getenv("PORT", 8080))

EMOJIS = {
    "party": "5989848973974704652",
    "stop": "5974083768233760323",
    "wave": "4983292515932177130",
    "check": "5980930633298350051",
    "cross": "6158841463032519010",
    "warning": "5787656288934564517",
    "link": "5292122921035133343",
    "stats": "5431577498364158238",
    "people": "5402211308017840657",
    "box": "5415750994849976302",
    "green": "5416081784641168838",
    "red": "5420323339723881652",
    "yellow": "5789570564448326827",
    "gear": "5341715473882955310",
    "plus": "5226945370684140473",
    "megaphone": "5836698068061261980",
    "hourglass": "5451646226975955576",
    "repeat": "5264727218734524899",
    "fire": "5424972470023104089",
    "ref_link": "5271604874419647061",
    "claim": "5449816553727998023",
    "referrals": "5985525762973768278",
    "channel": "6035277294036061660",
    "admin_add": "6034851808805918335",
    "stock": "5294118392905623955",
    "broadcast": "5780405967527089720",
    "users": "5985525762973768278",
}

def e(name):
    emoji_id = EMOJIS.get(name)
    return f'<tg-emoji id="{emoji_id}">🔹</tg-emoji>' if emoji_id else "🔹"

conn = sqlite3.connect("giveaway.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    full_name TEXT,
    referrer_id INTEGER,
    verified INTEGER DEFAULT 0,
    device_id TEXT UNIQUE,
    upi_id TEXT,
    joined_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS channels (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT,
    chat_id TEXT,
    invite_link TEXT,
    channel_type TEXT
)
""")
conn.commit()

class AdminStates(StatesGroup):
    add_channel_type = State()
    add_channel_title = State()
    add_channel_id = State()
    add_channel_link = State()
    broadcast_msg = State()

class UserStates(StatesGroup):
    entering_upi = State()

bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)
dp = Dispatcher(storage=MemoryStorage())

async def get_unjoined_channels(user_id: int):
    cursor.execute("SELECT chat_id, title, invite_link, channel_type FROM channels")
    channels = cursor.fetchall()
    unjoined = []
    for chat_id, title, link, c_type in channels:
        try:
            member = await bot.get_chat_member(chat_id=chat_id, user_id=user_id)
            if member.status in ["left", "kicked"]:
                unjoined.append((title, link))
        except Exception:
            unjoined.append((title, link))
    return unjoined

async def webapp_handler(request):
    html = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=no">
    <title>Device Verification</title>
    <script src="https://telegram.org/js/telegram-web-app.js"></script>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { background: radial-gradient(circle at top, #1e1b4b 0%, #090915 100%); color: #fff; font-family: sans-serif; display: flex; align-items: center; justify-content: center; min-height: 100vh; padding: 20px; }
        .card { background: rgba(30, 41, 59, 0.85); backdrop-filter: blur(12px); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 24px; padding: 32px 24px; text-align: center; max-width: 360px; width: 100%; }
        .icon-wrapper { width: 80px; height: 80px; margin: 0 auto 20px; background: radial-gradient(circle, #38bdf8 0%, #1e40af 100%); border-radius: 50%; display: flex; align-items: center; justify-content: center; }
        .icon-wrapper svg { width: 44px; height: 44px; fill: #fff; }
        h2 { font-size: 22px; margin-bottom: 12px; }
        p { font-size: 14px; line-height: 1.5; color: #94a3b8; margin-bottom: 28px; }
        .btn { background: linear-gradient(135deg, #0284c7 0%, #2563eb 100%); color: #fff; border: none; width: 100%; padding: 14px 20px; font-size: 16px; font-weight: 600; border-radius: 14px; cursor: pointer; }
    </style>
</head>
<body>
    <div class="card">
        <div class="icon-wrapper">
            <svg viewBox="0 0 24 24"><path d="M12 1L3 5v6c0 5.55 3.84 10.74 9 12 5.16-1.26 9-6.45 9-12V5l-9-4zm0 2.18l7 3.12v4.7c0 4.54-3.13 8.78-7 9.88-3.87-1.1-7-5.34-7-9.88V6.3l7-3.12z"/></svg>
        </div>
        <h2>Device Verification</h2>
        <p>Complete single-device authorization to unlock full referral rewards & instant voucher claims.</p>
        <button class="btn" onclick="verifyDevice()">Verify Device Now</button>
    </div>
    <script>
        let tg = window.Telegram.WebApp; tg.ready(); tg.expand();
        function generateFingerprint() {
            let canvas = document.createElement('canvas');
            let ctx = canvas.getContext('2d');
            ctx.textBaseline = "top"; ctx.font = "14px 'Arial'"; ctx.fillStyle = "#f60"; ctx.fillRect(125,1,62,20);
            ctx.fillStyle = "#069"; ctx.fillText("fingerprint_auth", 2, 15);
            let hw = screen.width + 'x' + screen.height + 'x' + (navigator.hardwareConcurrency || 4) + 'x' + (navigator.deviceMemory || 4);
            return btoa(canvas.toDataURL() + hw);
        }
        function verifyDevice() {
            let fp = generateFingerprint();
            tg.sendData(JSON.stringify({ action: "verify_device", device_id: fp }));
            tg.close();
        }
    </script>
</body>
</html>"""
    return web.Response(text=html, content_type="text/html")

def main_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🎁 Refer & Earn"), KeyboardButton(text="🏆 Top 20 Leaderboard")],
            [KeyboardButton(text="💳 Update UPI"), KeyboardButton(text="📊 My Stats")]
        ],
        resize_keyboard=True
    )

@dp.message(CommandStart())
async def start_cmd(message: types.Message):
    user_id = message.from_user.id
    username = message.from_user.username or ""
    full_name = message.from_user.full_name or ""
    args = message.text.split()[1:] if len(message.text.split()) > 1 else []
    referrer_id = int(args[0]) if args and args[0].isdigit() and int(args[0]) != user_id else None

    cursor.execute("SELECT verified, device_id FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    if not row:
        cursor.execute("INSERT INTO users (user_id, username, full_name, referrer_id) VALUES (?, ?, ?, ?)", (user_id, username, full_name, referrer_id))
    else:
        cursor.execute("UPDATE users SET username = ?, full_name = ? WHERE user_id = ?", (username, full_name, user_id))
    conn.commit()

    cursor.execute("SELECT verified FROM users WHERE user_id = ?", (user_id,))
    is_verified = cursor.fetchone()[0]

    if not is_verified:
        verify_url = f"{RENDER_URL}/verify" if RENDER_URL else "http://localhost:8080/verify"
        markup = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🛡️ Verify Device Now", web_app=WebAppInfo(url=verify_url))]])
        await message.answer(f"{e('warning')} <b>Device Verification Required!</b>\n\nEk device se sirf ek account verify ho sakta hai.\nNeeche button par click karein:", reply_markup=markup)
        return

    unjoined = await get_unjoined_channels(user_id)
    if unjoined:
        buttons = [[InlineKeyboardButton(text=f"{e('channel')} Join {title}", url=link)] for title, link in unjoined]
        buttons.append([InlineKeyboardButton(text=f"{e('check')} I Have Joined", callback_data="check_channels")])
        await message.answer(f"{e('stop')} <b>Channel Membership Required</b>\n\nGiveaway access karne ke liye channels join karein:", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
        return

    await message.answer(f"{e('party')} <b>Welcome to the Giveaway!</b>\n\n• <b>Top 1-5:</b> Mega Bonus Prize\n• <b>Rank 6-20:</b> Standard Prize", reply_markup=main_menu())

@dp.message(F.web_app_data)
async def webapp_receive(message: types.Message):
    user_id = message.from_user.id
    try:
        data = json.loads(message.web_app_data.data)
        if data.get("action") == "verify_device":
            device_id = data.get("device_id")
            cursor.execute("SELECT user_id FROM users WHERE device_id = ? AND user_id != ?", (device_id, user_id))
            if cursor.fetchone():
                await message.answer(f"{e('cross')} <b>Verification Failed!</b>\nYeh device already registered hai.")
                return
            cursor.execute("UPDATE users SET verified = 1, device_id = ? WHERE user_id = ?", (device_id, user_id))
            conn.commit()
            await message.answer(f"{e('check')} <b>Device Verified Successfully!</b>")
            await start_cmd(message)
    except Exception:
        await message.answer(f"{e('cross')} Verification error. Try again.")

@dp.callback_query(F.data == "check_channels")
async def check_joined_cb(query: types.CallbackQuery):
    unjoined = await get_unjoined_channels(query.from_user.id)
    if unjoined:
        await query.answer("Aapne sabhi channels join nahi kiye!", show_alert=True)
    else:
        await query.message.delete()
        await query.message.answer(f"{e('check')} Channels verified!", reply_markup=main_menu())

@dp.message(F.text == "🎁 Refer & Earn")
async def refer_view(message: types.Message):
    me = await bot.get_me()
    ref_link = f"https://t.me/{me.username}?start={message.from_user.id}"
    await message.answer(f"{e('ref_link')} <b>Referral Link:</b>\n<code>{ref_link}</code>", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=f"{e('link')} Share", url=f"https://t.me/share/url?url={ref_link}")]]))

@dp.message(F.text == "🏆 Top 20 Leaderboard")
async def top20_view(message: types.Message):
    cursor.execute("SELECT u.full_name, COUNT(r.user_id) as total FROM users u LEFT JOIN users r ON u.user_id = r.referrer_id AND r.verified = 1 GROUP BY u.user_id ORDER BY total DESC LIMIT 20")
    rows = cursor.fetchall()
    text = f"{e('fire')} <b>TOP 20 LEADERBOARD</b>\n\n"
    for i, (name, count) in enumerate(rows, start=1):
        tier = f"{e('party')} <i>(Super Reward)</i>" if i <= 5 else ""
        text += f"<b>#{i} {name}</b> — {count} Invites {tier}\n"
    await message.answer(text)

@dp.message(F.text == "📊 My Stats")
async def stats_view(message: types.Message):
    cursor.execute("SELECT COUNT(*) FROM users WHERE referrer_id = ? AND verified = 1", (message.from_user.id,))
    total = cursor.fetchone()[0]
    cursor.execute("SELECT upi_id FROM users WHERE user_id = ?", (message.from_user.id,))
    upi = cursor.fetchone()[0] or "Not set"
    await message.answer(f"{e('stats')} <b>Stats:</b>\n• <b>Invites:</b> {total}\n• <b>UPI:</b> <code>{upi}</code>")

@dp.message(F.text == "💳 Update UPI")
async def upi_entry(message: types.Message, state: FSMContext):
    await state.set_state(UserStates.entering_upi)
    await message.answer(f"{e('claim')} Apni UPI ID bhejein:")

@dp.message(UserStates.entering_upi)
async def upi_save(message: types.Message, state: FSMContext):
    upi = message.text.strip()
    if "@" not in upi:
        await message.answer(f"{e('warning')} Valid UPI address dalein.")
        return
    cursor.execute("UPDATE users SET upi_id = ? WHERE user_id = ?", (upi, message.from_user.id))
    conn.commit()
    await state.clear()
    await message.answer(f"{e('check')} Saved: <code>{upi}</code>")

@dp.message(Command("admin"))
async def admin_cmd(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"{e('admin_add')} Add Channel", callback_data="adm_add_ch")],
        [InlineKeyboardButton(text=f"{e('stats')} Export Top 20 (with UPI)", callback_data="adm_export")]
    ])
    await message.answer(f"{e('gear')} <b>Admin Panel</b>", reply_markup=markup)

@dp.callback_query(F.data == "adm_add_ch")
async def adm_add_type(query: types.CallbackQuery):
    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Public", callback_data="ctype_public")],
        [InlineKeyboardButton(text="Private", callback_data="ctype_private")],
        [InlineKeyboardButton(text="Join Request", callback_data="ctype_join_request")]
    ])
    await query.message.answer("Channel type:", reply_markup=markup)

@dp.callback_query(F.data.startswith("ctype_"))
async def adm_type_chosen(query: types.CallbackQuery, state: FSMContext):
    await state.update_data(c_type=query.data.replace("ctype_", ""))
    await state.set_state(AdminStates.add_channel_title)
    await query.message.answer("Channel Name dalein:")

@dp.message(AdminStates.add_channel_title)
async def adm_got_title(message: types.Message, state: FSMContext):
    await state.update_data(title=message.text)
    await state.set_state(AdminStates.add_channel_id)
    await message.answer("Channel ID/Username dalein:")

@dp.message(AdminStates.add_channel_id)
async def adm_got_id(message: types.Message, state: FSMContext):
    await state.update_data(chat_id=message.text)
    await state.set_state(AdminStates.add_channel_link)
    await message.answer("Channel Link dalein:")

@dp.message(AdminStates.add_channel_link)
async def adm_got_link(message: types.Message, state: FSMContext):
    data = await state.get_data()
    cursor.execute("INSERT INTO channels (title, chat_id, invite_link, channel_type) VALUES (?, ?, ?, ?)", (data["title"], data["chat_id"], message.text, data["c_type"]))
    conn.commit()
    await state.clear()
    await message.answer(f"{e('check')} Channel added!")

@dp.callback_query(F.data == "adm_export")
async def adm_export(query: types.CallbackQuery):
    cursor.execute("SELECT u.user_id, u.full_name, u.username, u.upi_id, COUNT(r.user_id) as invites FROM users u LEFT JOIN users r ON u.user_id = r.referrer_id AND r.verified = 1 GROUP BY u.user_id ORDER BY invites DESC LIMIT 20")
    rows = cursor.fetchall()
    content = "TOP 20 WINNERS\n\n"
    for r, (uid, name, uname, upi, inv) in enumerate(rows, start=1):
        tier = "TOP 5" if r <= 5 else "STANDARD"
        content += f"#{r} [{tier}] {name} (@{uname}) | Invites: {inv} | UPI: {upi or 'N/A'}\n"
    with open("top20.txt", "w", encoding="utf-8") as f:
        f.write(content)
    await query.message.answer_document(FSInputFile("top20.txt"), caption=f"{e('party')} Top 20 Winners!")

async def start_web():
    app = web.Application()
    app.router.add_get("/", lambda r: web.Response(text="Bot is online!"))
    app.router.add_get("/verify", webapp_handler)
    runner = web.AppRunner(app)
    await runner.setup()
    await web.TCPSite(runner, "0.0.0.0", PORT).start()

async def main():
    await start_web()
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
