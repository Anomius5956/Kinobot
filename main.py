import asyncio
import os
import re
import json
from aiohttp import web
from telethon import TelegramClient, events

API_ID = 35656569
API_HASH = "f7d00012a8701d50015ae3d051e402fe"
TARGET_GROUP_ID = -1003025094654
RAW_GROUP_ID = "3025094654"
MUNDARIJA_LINK = "https://t.me/shaxsiybazamm"

client = TelegramClient(
    "cinema_baza_termux_api1", 
    API_ID, 
    API_HASH
)

DATABASE = []
if os.path.exists("topics.json"):
    try:
        with open("topics.json", "r", encoding="utf-8") as f:
            raw_data = json.load(f)
            for k, item in raw_data.items():
                title = item.get("title", k)
                link = item.get("link", f"https://t.me/c/{RAW_GROUP_ID}/{item.get('id', '')}")
                norm = re.sub(r"[^\w\s]", "", title.lower()).strip()
                DATABASE.append({
                    "title": title,
                    "norm": norm,
                    "link": link
                })
        print(f"✅ Baza to'liq yodlandi: {len(DATABASE)} ta kino va serial faol.", flush=True)
    except Exception as e:
        print(f"Baza o'qishda xatolik: {e}", flush=True)

def clean_title(text):
    return re.sub(r"[\[\]_*~`]", "", text or "").strip()

def search_movies(query):
    query_clean = re.sub(r"[^\w\s]", "", query.lower()).strip()
    if not query_clean:
        return []

    q_words = query_clean.split()
    results = []

    # 1. Barcha yozilgan so'zlar nomda to'liq qatnashgan filmlar
    for item in DATABASE:
        if all(word in item["norm"] for word in q_words):
            results.append(item)
            if len(results) >= 5:
                return results

    # 2. Kamida bitta asosiy so'z to'g'ri kelgan filmlar
    if not results and len(query_clean) >= 3:
        for item in DATABASE:
            if item in results:
                continue
            for word in q_words:
                if len(word) >= 3 and word in item["norm"]:
                    results.append(item)
                    break
            if len(results) >= 5:
                break

    return results

# Faqat va faqat sizning guruhingizdagi xabarlarni qabul qilish
@client.on(events.NewMessage(chats=[TARGET_GROUP_ID], incoming=True))
async def auto_reply_handler(event):
    if getattr(event, 'out', False):
        return

    text = (event.raw_text or "").strip()
    if len(text) < 2:
        return

    if text.lower() in ["salom", "qalesiz", "assalomu alaykum", "/start"]:
        reply_msg = (
            "Assalomu alaykum! 🎬\n\n"
            "Kerakli kino yoki serial nomini yozing, havola avtomatik yuboriladi."
        )
        await event.reply(reply_msg)
        return

    found = search_movies(text)
    if found:
        response_text = f"🍿 **'{text}' bo'yicha topilgan natijalar:**\n\n"
        for item in found:
            clean_name = clean_title(item["title"])
            link = item["link"]
            response_text += f"🎬 [{clean_name}]({link})\n"
        response_text += f"\n✨ @FilimHudud Eng Sara Filmlar\n📚 To'liq ro'yxat: {MUNDARIJA_LINK}"
        await event.reply(response_text, link_preview=False)
    else:
        response_text = (
            f"Afsuski, **'{text}'** topilmadi.\n"
            f"Barcha kinolar ro'yxati: {MUNDARIJA_LINK}"
        )
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
