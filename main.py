import asyncio
import os
import re
import json
from aiohttp import web
from telethon import TelegramClient, events

API_ID = 35656569
API_HASH = "f7d00012a8701d50015ae3d051e402fe"

# Sizning guruhingiz ID'si
TARGET_GROUP_ID = -1003025094654
MUNDARIJA_LINK = "https://t.me/shaxsiybazamm"

client = TelegramClient(
    "cinema_baza_termux_api1", 
    API_ID, 
    API_HASH
)

RAW_GROUP_ID = str(TARGET_GROUP_ID).replace("-100", "").replace("-", "")

# 1. Baza faylini yuklash
TOPICS_CACHE = {}
if os.path.exists("topics.json"):
    try:
        with open("topics.json", "r", encoding="utf-8") as f:
            TOPICS_CACHE = json.load(f)
        print(f"✅ Baza tayyor: {len(TOPICS_CACHE)} ta kino yuklandi.", flush=True)
    except Exception as e:
        print(f"Fayl o'qishda xatolik: {e}", flush=True)
else:
    print("⚠️ topics.json topilmadi!", flush=True)

def clean_title(text):
    return re.sub(r"[\[\]_*~`]", "", text or "").strip()

def search_movies(query):
    query_clean = re.sub(r"[^\w\s]", "", query.lower()).strip()
    q_words = query_clean.split()
    if not q_words:
        return []

    results = []
    # 1. Barcha so'zlar mos kelgan mavzular
    for t_id, title in TOPICS_CACHE.items():
        title_clean = re.sub(r"[^\w\s]", "", title.lower()).strip()
        if all(word in title_clean for word in q_words):
            results.append((t_id, title))
            if len(results) >= 5:
                return results

    # 2. Kamida bitta so'z to'g'ri kelgan mavzular
    if not results and len(query_clean) >= 3:
        for t_id, title in TOPICS_CACHE.items():
            title_clean = re.sub(r"[^\w\s]", "", title.lower()).strip()
            for word in q_words:
                if len(word) >= 3 and word in title_clean:
                    results.append((t_id, title))
                    break
            if len(results) >= 5:
                break

    return results

# FAQAT SIZNING GURUHINGIZGA JAVOB BERADI
@client.on(events.NewMessage(incoming=True))
async def auto_reply_handler(event):
    if getattr(event, 'out', False):
        return

    # Guruh tekshiruvi: faqat -1003025094654 yoki 3025094654 bo'lsa ishlaydi
    chat_id = event.chat_id
    allowed_ids = [TARGET_GROUP_ID, int(RAW_GROUP_ID), -int(RAW_GROUP_ID)]
    if chat_id not in allowed_ids:
        return  # Boshqa guruhlar yoki shaxsiydan yozilsa, jim turadi

    text = (event.raw_text or "").strip()
    if len(text) < 2:
        return

    if text.lower() in ["salom", "qalesiz", "assalomu alaykum", "/start"]:
        reply_msg = (
            "Assalomu alaykum! 🎬\n\n"
            "Kerakli kino nomini yozing, havola avtomatik yuboriladi."
        )
        await event.reply(reply_msg)
        return

    found = search_movies(text)
    if found:
        response_text = f"🍿 **'{text}' bo'yicha topilgan natijalar:**\n\n"
        for t_id, title in found:
            clean_name = clean_title(title)
            link = f"https://t.me/c/{RAW_GROUP_ID}/{t_id}"
            response_text += f"🎬 [{clean_name}]({link})\n"
        response_text += f"\n✨ @FilimHudud Eng Sara Filmlar\n📚 To'liq ro'yxat: {MUNDARIJA_LINK}"
        await event.reply(response_text, link_preview=False)

async def handle_ping(request):
    return web.Response(text="Bot is running 24/7!")

async def start_web():
    app = web.Application()
    app.router.add_get('/', handle_ping)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 10000))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    print(f"🌐 Web-server port {port} da ishga tushdi", flush=True)

async def main():
    await start_web()
    await client.start()
    await client.run_until_disconnected()

if __name__ == "__main__":
    asyncio.run(main())
