import asyncio
import os
import re
import json
from aiohttp import web
from telethon import TelegramClient, events

API_ID = 35656569
API_HASH = "f7d00012a8701d50015ae3d051e402fe"
TARGET_GROUP_ID = -1003025094654
MUNDARIJA_LINK = "https://t.me/shaxsiybazamm"

client = TelegramClient(
    "cinema_baza_termux_api1", 
    API_ID, 
    API_HASH
)

RAW_GROUP_ID = "3025094654"

TOPICS_CACHE = {}
if os.path.exists("topics.json"):
    try:
        with open("topics.json", "r", encoding="utf-8") as f:
            raw_data = json.load(f)
            for k, v in raw_data.items():
                if isinstance(v, dict):
                    title = v.get("title", k)
                    link = v.get("link", "")
                    TOPICS_CACHE[k.lower()] = {"title": title, "link": link}
                else:
                    title = str(v)
                    clean_id = re.sub(r"\D", "", str(k))
                    link = f"https://t.me/c/{RAW_GROUP_ID}/{clean_id}"
                    TOPICS_CACHE[title.lower()] = {"title": title, "link": link}
        print(f"✅ Baza tayyor: {len(TOPICS_CACHE)} ta kino yuklandi.", flush=True)
    except Exception as e:
        print(f"Baza o'qishda xatolik: {e}", flush=True)
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
    # 1. To'liq mos kelganlar
    for key, data in TOPICS_CACHE.items():
        title_str = (key + " " + data["title"]).lower()
        title_clean = re.sub(r"[^\w\s]", "", title_str).strip()
        if all(word in title_clean for word in q_words):
            results.append(data)
            if len(results) >= 5:
                return results

    # 2. Qisman mos kelganlar (kamida 3 harf)
    if not results and len(query_clean) >= 3:
        for key, data in TOPICS_CACHE.items():
            title_str = (key + " " + data["title"]).lower()
            title_clean = re.sub(r"[^\w\s]", "", title_str).strip()
            for word in q_words:
                if len(word) >= 3 and word in title_clean:
                    results.append(data)
                    break
            if len(results) >= 5:
                break

    return results

@client.on(events.NewMessage(incoming=True))
async def auto_reply_handler(event):
    # Faqat guruh xabarlariga qaraymiz
    if not event.is_group:
        return

    # O'zimiz yuborgan xabarlarni e'tiborsiz qoldiramiz
    if getattr(event, 'out', False):
        return

    # Guruh ID tekshiruvi: Telethon -100 prefiksisiz yoki prefiks bilan ko'rsatishi mumkin
    chat_str = str(event.chat_id).replace("-100", "").replace("-", "")
    if chat_str != RAW_GROUP_ID:
        return  # Boshqa guruh bo'lsa, javob bermaydi

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
