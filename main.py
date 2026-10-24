import asyncio
import os
import re
from aiohttp import web
from telethon import TelegramClient, events
from telethon.tl.types import (
    MessageActionTopicCreate,
    MessageActionTopicEdit
)

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
        async for msg in client.iter_messages(group_peer, reverse=True):
            if msg.action:
                if isinstance(msg.action, MessageActionTopicCreate):
                    TOPICS_CACHE[msg.id] = msg.action.title.strip()
                elif isinstance(msg.action, MessageActionTopicEdit) and msg.action.title:
                    t_id = getattr(msg, 'reply_to_msg_id', None) or msg.id
                    TOPICS_CACHE[t_id] = msg.action.title.strip()

            top_id = getattr(msg.reply_to, 'reply_to_top_id', None) or getattr(msg.reply_to, 'reply_to_msg_id', None)
            if top_id and top_id not in TOPICS_CACHE:
                if msg.text:
                    first_line = msg.text.strip().split('\n')[0][:50]
                    TOPICS_CACHE[top_id] = first_line
        print(f"✅ Baza tayyor: {len(TOPICS_CACHE)} ta mavzu yuklandi.", flush=True)
    except Exception as e:
        print(f"Xatolik mavzularni yuklashda: {e}", flush=True)

def search_movies(query):
    q_words = re.sub(r"[^\w\s]", "", query.lower()).split()
    if not q_words:
        return []
    results = []
    for t_id, title in TOPICS_CACHE.items():
        title_lower = title.lower()
        if all(word in title_lower for word in q_words):
            results.append((t_id, title))
            if len(results) >= 5:
                break
    return results

# Faqat guruhlarda kelgan xabarlarga javob qaytarish
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
        # Guruhda hamma xabarga spam bo'lmasligi uchun faqat aniq kino so'ralganda javob berish ma'qul, 
        # lekin topilmagan xabari kerak bo'lsa:
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
