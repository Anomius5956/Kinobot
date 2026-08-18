import asyncio
import logging
import aiosqlite
from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.exceptions import TelegramBadRequest

BOT_TOKEN = "8906666148:AAElqL0TuF9lBVUwNQfjBznwbNXmin2OlOU"
ADMIN_ID = 5919763854  # O'zingizning Telegram raqamli ID'ingiz

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# FSM holatlari
class AdminStates(StatesGroup):
    add_channel_id = State()
    add_channel_url = State()
    del_channel = State()
    add_movie_code = State()
    add_movie_file = State()
    del_movie = State()
    broadcast_msg = State()

# Ma'lumotlar bazasini initsializatsiya qilish
async def init_db():
    async with aiosqlite.connect("database.db") as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS movies (
                code TEXT PRIMARY KEY,
                file_id TEXT,
                caption TEXT
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS channels (
                channel_id TEXT PRIMARY KEY,
                invite_link TEXT
            )
        """)
        await db.commit()

# Majburiy obunani tekshirish funksiyasi
async def check_subscription(user_id: int):
    async with aiosqlite.connect("database.db") as db:
        cursor = await db.execute("SELECT channel_id, invite_link FROM channels")
        channels = await cursor.fetchall()

    not_subscribed = []
    for ch_id, link in channels:
        try:
            member = await bot.get_chat_member(chat_id=ch_id, user_id=user_id)
            if member.status in ["left", "kicked"]:
                not_subscribed.append((ch_id, link))
        except TelegramBadRequest:
            continue
    return not_subscribed

# Foydalanuvchilar bazasiga qo'shish
async def register_user(user_id: int):
    async with aiosqlite.connect("database.db") as db:
        await db.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
        await db.commit()

# Admin klaviaturasi
def admin_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎬 Kino qo‘shish", callback_data="admin_add_movie"),
         InlineKeyboardButton(text="🗑 Kino o‘chirish", callback_data="admin_del_movie")],
        [InlineKeyboardButton(text="📢 Kanal qo‘shish", callback_data="admin_add_channel"),
         InlineKeyboardButton(text="❌ Kanal o‘chirish", callback_data="admin_del_channel")],
        [InlineKeyboardButton(text="📊 Statistika", callback_data="admin_stats"),
         InlineKeyboardButton(text="✉️ Xabar tarqatish", callback_data="admin_broadcast")],
        [InlineKeyboardButton(text="📋 Kanallar ro‘yxati", callback_data="admin_list_channels")]
    ])

# /start buyrug'i
@dp.message(CommandStart())
async def start_cmd(message: Message):
    await register_user(message.from_user.id)
    not_subbed = await check_subscription(message.from_user.id)

    if not_subbed:
        buttons = []
        for i, (_, link) in enumerate(not_subbed, 1):
            buttons.append([InlineKeyboardButton(text=f"📢 {i}-kanalga obuna bo‘lish", url=link)])
        buttons.append([InlineKeyboardButton(text="✅ Obunani tekshirish", callback_data="check_sub")])
        
        await message.answer(
            "⚠️ Botdan to‘liq foydalanish uchun quyidagi kanallarga a'zo bo‘ling:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
        )
        return

    await message.answer(
        f"Assalomu alaykum, {message.from_user.full_name}!\n\n"
        f"🎬 Kino ko‘rish uchun kino kodini yuboring (masalan: `100`).",
        parse_mode="Markdown"
    )

# Obunani tekshirish tugmasi
@dp.callback_query(F.data == "check_sub")
async def check_sub_callback(callback: CallbackQuery):
    not_subbed = await check_subscription(callback.from_user.id)
    if not_subbed:
        await callback.answer("❌ Hali barcha kanallarga a'zo bo‘lmadingiz!", show_alert=True)
    else:
        await callback.message.delete()
        await callback.message.answer("✅ Rahmat! Endi kino kodini yuborishingiz mumkin.")

# /admin buyrug'i
@dp.message(Command("admin"), F.from_user.id == ADMIN_ID)
async def admin_panel(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("👑 **Admin boshqaruv paneliga xush kelibsiz:**", reply_markup=admin_keyboard(), parse_mode="Markdown")

# Admin callback boshqaruvi
@dp.callback_query(F.from_user.id == ADMIN_ID, F.data.startswith("admin_"))
async def admin_callbacks(callback: CallbackQuery, state: FSMContext):
    action = callback.data

    if action == "admin_stats":
        async with aiosqlite.connect("database.db") as db:
            c1 = await db.execute("SELECT COUNT(*) FROM users")
            user_count = (await c1.fetchone())[0]
            c2 = await db.execute("SELECT COUNT(*) FROM movies")
            movie_count = (await c2.fetchone())[0]
        await callback.message.answer(f"📊 **Statistika:**\n\n👤 Foydalanuvchilar: `{user_count}` ta\n🎬 Kinolar: `{movie_count}` ta", parse_mode="Markdown")
        await callback.answer()

    elif action == "admin_list_channels":
        async with aiosqlite.connect("database.db") as db:
            cursor = await db.execute("SELECT channel_id, invite_link FROM channels")
            channels = await cursor.fetchall()
        if not channels:
            text = "Kanallar ulanmagan."
        else:
            text = "📋 **Ulangan majburiy kanallar:**\n\n" + "\n".join([f"ID: `{cid}` | [Link]({link})" for cid, link in channels])
        await callback.message.answer(text, parse_mode="Markdown", disable_web_page_preview=True)
        await callback.answer()

    elif action == "admin_add_channel":
        await callback.message.answer("📢 Kanal ID yoki @username'ini kiriting (masalan: `@mening_kanalim` yoki `-100123456789`):\n\n*(Eslatma: Bot ushbu kanalda ADMIN bo‘lishi shart)*")
        await state.set_state(AdminStates.add_channel_id)
        await callback.answer()

    elif action == "admin_del_channel":
        await callback.message.answer("❌ O‘chirmoqchi bo‘lgan kanal ID'sini kiriting:")
        await state.set_state(AdminStates.del_channel)
        await callback.answer()

    elif action == "admin_add_movie":
        await callback.message.answer("🔑 Yangi kino uchun kod kiriting (masalan: `101`):")
        await state.set_state(AdminStates.add_movie_code)
        await callback.answer()

    elif action == "admin_del_movie":
        await callback.message.answer("🗑 O‘chirmoqchi bo‘lgan kino kodini kiriting:")
        await state.set_state(AdminStates.del_movie)
        await callback.answer()

    elif action == "admin_broadcast":
        await callback.message.answer("✉️ Barcha foydalanuvchilarga yuboriladigan xabarni (matn, rasm yoki video) yuboring:")
        await state.set_state(AdminStates.broadcast_msg)
        await callback.answer()

# --- FSM Handlerlar ---

# Kanal qo'shish
@dp.message(AdminStates.add_channel_id)
async def state_add_channel_id(message: Message, state: FSMContext):
    await state.update_data(ch_id=message.text.strip())
    await message.answer("🔗 Ushbu kanal uchun taklif havolasini (https://t.me/...) kiriting:")
    await state.set_state(AdminStates.add_channel_url)

@dp.message(AdminStates.add_channel_url)
async def state_add_channel_url(message: Message, state: FSMContext):
    data = await state.get_data()
    ch_id = data['ch_id']
    link = message.text.strip()
    
    async with aiosqlite.connect("database.db") as db:
        await db.execute("INSERT OR REPLACE INTO channels (channel_id, invite_link) VALUES (?, ?)", (ch_id, link))
        await db.commit()
    
    await message.answer("✅ Kanal muvaffaqiyatli saqlandi!", reply_markup=admin_keyboard())
    await state.clear()

# Kanal o'chirish
@dp.message(AdminStates.del_channel)
async def state_del_channel(message: Message, state: FSMContext):
    ch_id = message.text.strip()
    async with aiosqlite.connect("database.db") as db:
        await db.execute("DELETE FROM channels WHERE channel_id = ?", (ch_id,))
        await db.commit()
    await message.answer(f"✅ `{ch_id}` bazadan o‘chirildi.", reply_markup=admin_keyboard(), parse_mode="Markdown")
    await state.clear()

# Kino qo'shish
@dp.message(AdminStates.add_movie_code)
async def state_add_movie_code(message: Message, state: FSMContext):
    await state.update_data(code=message.text.strip())
    await message.answer("🎬 Endi kinoning videosini (yoki faylini) yuboring:")
    await state.set_state(AdminStates.add_movie_file)

@dp.message(AdminStates.add_movie_file, F.video)
async def state_add_movie_file(message: Message, state: FSMContext):
    data = await state.get_data()
    code = data['code']
    file_id = message.video.file_id
    caption = message.caption or ""

    async with aiosqlite.connect("database.db") as db:
        await db.execute("INSERT OR REPLACE INTO movies (code, file_id, caption) VALUES (?, ?, ?)", (code, file_id, caption))
        await db.commit()

    await message.answer(f"✅ Kino muvaffaqiyatli saqlandi!\n🔑 Kod: `{code}`", reply_markup=admin_keyboard(), parse_mode="Markdown")
    await state.clear()

# Kino o'chirish
@dp.message(AdminStates.del_movie)
async def state_del_movie(message: Message, state: FSMContext):
    code = message.text.strip()
    async with aiosqlite.connect("database.db") as db:
        await db.execute("DELETE FROM movies WHERE code = ?", (code,))
        await db.commit()
    await message.answer(f"✅ `{code}` kodli kino o‘chirildi.", reply_markup=admin_keyboard(), parse_mode="Markdown")
    await state.clear()

# Xabar tarqatish (Broadcast)
@dp.message(AdminStates.broadcast_msg)
async def state_broadcast_msg(message: Message, state: FSMContext):
    async with aiosqlite.connect("database.db") as db:
        cursor = await db.execute("SELECT user_id FROM users")
        users = await cursor.fetchall()

    count = 0
    await message.answer("⏳ Xabar tarqatish boshlandi...")
    for (user_id,) in users:
        try:
            await message.copy_to(chat_id=user_id)
            count += 1
            await asyncio.sleep(0.05)  # Telegram flood limit cheklovidan saqlanish
        except Exception:
            continue

    await message.answer(f"✅ Xabar `{count}` ta foydalanuvchiga muvaffaqiyatli yetkazildi.", reply_markup=admin_keyboard(), parse_mode="Markdown")
    await state.clear()

# Oddiy foydalanuvchi kino kodini yuborganda
@dp.message(F.text)
async def get_movie(message: Message):
    await register_user(message.from_user.id)
    not_subbed = await check_subscription(message.from_user.id)
    
    if not_subbed:
        buttons = []
        for i, (_, link) in enumerate(not_subbed, 1):
            buttons.append([InlineKeyboardButton(text=f"📢 {i}-kanalga obuna bo‘lish", url=link)])
        buttons.append([InlineKeyboardButton(text="✅ Obunani tekshirish", callback_data="check_sub")])
        await message.answer("⚠️ Kino olishdan oldin kanallarga a'zo bo‘ling:", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
        return

    code = message.text.strip()
    async with aiosqlite.connect("database.db") as db:
        cursor = await db.execute("SELECT file_id, caption FROM movies WHERE code = ?", (code,))
        row = await cursor.fetchone()

    if row:
        file_id, caption = row
        await message.answer_video(video=file_id, caption=caption or f"🎬 Kino kodi: {code}")
    else:
        await message.answer("❌ Bu kod bo‘yicha kino topilmadi.")

# Ishga tushirish
async def main():
    logging.basicConfig(level=logging.INFO)
    await init_db()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
