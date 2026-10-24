import asyncio
import os
import re
import json
from aiohttp import web
from telethon import TelegramClient, events
from telethon.tl.tlobject import TLRequest

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

class RawEditForumTopic(TLRequest):
    CONSTRUCTOR_ID = 0xf40c0224
    SUBCLASS_OF_ID = 0x8af52aac

    def __init__(self, channel, topic_id, closed=None):
        self.channel = channel
        self.topic_id = topic_id
        self.closed = closed

    def to_dict(self):
        return {
            '_': 'EditForumTopicRequest',
            'channel': self.channel,
            'topic_id': self.topic_id,
            'closed': self.closed
        }

    def _bytes(self):
        flags = 0
        if self.closed is not None:
            flags |= 4
        data = self.CONSTRUCTOR_ID.to_bytes(4, 'little')
        data += flags.to_bytes(4, 'little')
        data += self.channel._bytes()
        data += self.topic_id.to_bytes(4, 'little', signed=True)
        if self.closed is not None:
            bool_id = 0x997275b5 if self.closed else 0xbc799737
            data += bool_id.to_bytes(4, 'little')
        return data

DATABASE = []
TOPIC_IDS = []

if os.path.exists("topics.json"):
    try:
        with open("topics.json", "r", encoding="utf-8") as f:
            raw_data = json.load(f)
            for k, item in raw_data.items():
                title = item.get("title", k)
                p_id = item.get("id")
                if not p_id:
                    m = re.findall(r"\d+", item.get("link", ""))
                    p_id = m[-1] if m else re.sub(r"\D", "", str(k))
                
                clean_pid = re.sub(r"\D", "", str(p_id))
                if clean_pid and int(clean_pid) > 1 and int(clean_pid) not in TOPIC_IDS:
                    TOPIC_IDS.append(int(clean_pid))

                link = f"https://t.me/c/{RAW_GROUP_ID}/{p_id}"
                norm = re.sub(r"[^\w\s]", "", title.lower()).strip()
                DATABASE.append({
                    "title": title,
                    "norm": norm,
                    "link": link
                })
        print(f"✅ Baza tayyor: {len(DATABASE)} ta kino yuklandi.", flush=True)
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

    for item in DATABASE:
        if all(word in item["norm"] for word in q_words):
            results.append(item)
            if len(results) >= 5:
                return results

    if not results and len(query_clean) >= 3:
        for item in DATABASE:
            for word in q_words:
                if len(word) >= 3 and word in item["norm"]:
                    results.append(item)
                    break
            if len(results) >= 5:
                break

    return results

@client.on(events.NewMessage(chats=[TARGET_GROUP_ID]))
async def auto_reply_handler(event):
    text = (event.raw_text or "").strip()

    # Maxsus buyruq: faqat siz yozganingizda barcha mavzularni Render orqali yopadi
    if text == "/close_all_topics":
        await event.reply("🔒 Barcha mavzularni yopish boshlandi...")
        entity = await client.get_input_entity(TARGET_GROUP_ID)
        done = 0
        for tid in TOPIC_IDS:
            try:
                await client(RawEditForumTopic(channel=entity, topic_id=tid, closed=True))
                done += 1
                await asyncio.sleep(0.15)
            except Exception:
                continue
        await event.reply(f"✅ Barcha mavzular muvaffaqiyatli yopildi! Jami: {done} ta")
        return

    # O'zimizning oddiy xabarlarimizga javob bermaslik
    if getattr(event, 'out', False):
        return

    if len(text) < 2:
        return

    if text.lower() in ["salom", "qalesiz", "assalomu alaykum", "/start"]:
        reply_msg = (
            "Assalomu alaykum! 🎬\n\n"
            "Kerakli kino yoki serial nomini yozing, havola avtomatik yuboriladi."
        )
        await event.reply(reply_msg, link_preview=False)
        return

    found = search_movies(text)
    if found:
        response_text = f"🍿 **'{text}' bo'yicha topilgan natijalar:**\n\n"
        for item in found:
            clean_name = clean_title(item["title"])
            link = item["link"]
            response_text += f"🎬 **[{clean_name}]({link})**\n\n"
        
        response_text += f"✨ @FilimHudud Eng Sara Filmlar\n📚 Barcha kinolar: {MUNDARIJA_LINK}"
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
