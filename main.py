import asyncio
import os
import re
from aiohttp import web
from telethon import TelegramClient, events
from telethon.tl.functions.channels import GetForumTopicsRequest

API_ID = 35656569
API_HASH = "f7d00012a8701d50015ae3d051e402fe"
TARGET_GROUP_ID = -1003025094654
MUNDARIJA_LINK = "https://t.me/shaxsiybazamm"

client = TelegramClient(
    "cinema_baza_termux_api1", 
    API_ID, 
    API_HASH
)

TOPICS_CACHE = {}
RAW_GROUP_ID = str(TARGET_GROUP_ID).replace("-100", "").replace("-", "")

def clean_title(text):
    return re.sub(r"[\[\]_*~`]", "", text or "").strip()

async def load_all_topics():
    global TOPICS_CACHE
    print("⏳ Bazadagi barcha mavzular keshlanmoqda...", flush=True)
    try:
        group_peer = await client.get_input_entity(TARGET_GROUP_ID)
        offset_date = 0
        offset_id = 0
        offset_topic = 0
        limit = 100

        while True:
            result = await client(GetForumTopicsRequest(
                channel=group_peer,
                offset_date=offset_date,
                offset_id=offset_id,
                offset_topic=offset_topic,
                limit=limit
            ))
            
            if not result.topics:
                break

            for topic in result.topics:
                TOPICS_CACHE[topic.id] = topic.title.strip()

            if len(result.topics) < limit:
                break

            last_topic = result.topics[-1]
            offset_date = getattr(last_topic, 'date', 0)
            offset_id = last_topic.id
            offset_topic = last_topic.id

        print(f"✅ Baza tayyor: {len(TOPICS_CACHE)} ta mavzu yuklandi.", flush=True)
        if TOPICS_CACHE:
            first_few = list(TOPICS_CACHE.values())[:5]
            print(f"📌 Yuklangan dastlabki kinolar: {first_few}", flush=True)

    except Exception as e:
        print(f"Xatolik mavzularni yuklashda: {e}", flush=True)

def search_movies(query):
    query_clean = re.sub(r"[^\w\s]", "", query.lower()).strip()
    q_words = query_clean.split()
    if not q_words:
        return []

    results = []
    # 1. To'liq moslik yoki barcha so'zlar qatnashgan mavzular
    for t_id, title in TOPICS_CACHE.items():
        title_clean = re.sub(r"[^\w\s]", "", title.lower()).strip()
        if all(word in title_clean for word in q_words):
            results.append((t_id, title))
            if len(results) >= 5:
                return results

    # 2. Agar topilmasa, so'zlardan kamida bittasi qatnashganlari
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

@client.on(events.NewMessage(incoming=True, func=lambda e: e.is_group))
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
        for t_id, title in found:
            clean_name = clean_title(title)
            link = f"https://t.me/c/{RAW_GROUP_ID}/{t_id}"
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
    return web.Response(text="Bot is running 24/7 in groups!")

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
    asyncio.create_task(load_all_topics())
    await client.run_until_disconnected()

if __name__ == "__main__":
    asyncio.run(main())
