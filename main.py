import asyncio, glob, os, re, time
from telethon import TelegramClient, events
from telethon.errors import FloodWaitError, UserAlreadyParticipantError
from telethon.tl.functions.messages import ImportChatInviteRequest, CheckChatInviteRequest
from telethon.tl.types import (
    MessageMediaDocument,
    DocumentAttributeVideo,
    DocumentAttributeAnimated,
    DocumentAttributeFilename
)

API_ID = 35656569
API_HASH = "f7d00012a8701d50015ae3d051e402fe"

INVITE_HASH = "XVjpEsGZUDpkYzgy"
TARGET_CHAT_ID = -1003025094654   # FilimHudud
TARGET_TOPIC_ID = 53386           # 53386-mavzu

NEW_SIGNATURE = "\n\n@FilimHudud Eng Sara Filmlar"
HISTORY_FILE = "yuborilgan_xvjp.txt"
TEMP_DIR = "temp_media_xvjp"
os.makedirs(TEMP_DIR, exist_ok=True)

processed_videos = set()
for txt in glob.glob("yuborilgan_*.txt"):
    try:
        with open(txt, "r", encoding="utf-8") as f:
            for line in f:
                item = line.strip()
                if item: processed_videos.add(item)
    except Exception: pass

print(f"Xotiradan {len(processed_videos)} ta yuborilgan video yuklandi.")

def save_sig(sig):
    processed_videos.add(sig)
    with open(HISTORY_FILE, "a", encoding="utf-8") as f:
        f.write(f"{sig}\n"); f.flush(); os.fsync(f.fileno())

def is_strict_video(msg):
    if not msg or not msg.media or getattr(msg, 'photo', None):
        return False
    if isinstance(msg.media, MessageMediaDocument) and msg.media.document:
        doc = msg.media.document
        for attr in doc.attributes:
            if isinstance(attr, DocumentAttributeAnimated) or getattr(attr, 'round_message', False):
                return False
            if isinstance(attr, DocumentAttributeVideo):
                return True
        if doc.mime_type and doc.mime_type.startswith("video/"):
            return True
        for attr in doc.attributes:
            if isinstance(attr, DocumentAttributeFilename):
                ext = (attr.file_name or "").lower()
                if any(ext.endswith(x) for x in ['.mp4','.mkv','.avi','.mov','.flv','.webm','.ts','.m4v']):
                    return True
    return False

def get_sig(msg):
    if msg.media and hasattr(msg.media, 'document') and msg.media.document:
        doc = msg.media.document
        dur = 0
        for attr in doc.attributes:
            if isinstance(attr, DocumentAttributeVideo):
                dur = int(getattr(attr, 'duration', 0)); break
        return f"{doc.size}_{dur}"
    return f"id_{msg.id}"

def clean_and_format_caption(old_text):
    text = old_text or ""
    text = re.sub(r"(https?://\S+|t\.me/\S+|tg://\S+|www\.\S+)", "", text)
    text = re.sub(r"#\w+", "", text)
    text = re.sub(r"@\w+", "", text)
    text = re.sub(r"(?i)(obuna bo['`]?ling|kanalimiz|bizning kanal|kanalga o['`]?tish|do['`]?stlarga ulashing|reklama|admin|homiy).*", "", text)
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    cleaned_base = "\n".join(lines)
    return (cleaned_base + NEW_SIGNATURE) if cleaned_base else "@FilimHudud Eng Sara Filmlar"

async def send_safely(client, msg, target_peer, topic_id, caption):
    t_start = time.time()
    
    # 1-usul: Server orqali to'g'ridan-to'g'ri o'tkazish
    try:
        await asyncio.wait_for(
            client.send_message(
                target_peer,
                file=msg.media,
                message=caption,
                reply_to=topic_id
            ),
            timeout=25.0
        )
        elapsed = round(time.time() - t_start, 2)
        return True, f"server orqali {elapsed} soniyada o'tkazildi"
    except Exception:
        pass

    # 2-usul: Agar server to'g'ridan-to'g'ri bermasa, yuklab yuborish
    temp_file = thumb_path = None
    try:
        try:
            thumb_path = await client.download_media(msg.media, file=TEMP_DIR, thumb=-1)
        except Exception:
            thumb_path = None

        temp_file = await client.download_media(msg.media, file=TEMP_DIR)
        doc_attrs = getattr(msg.media.document, 'attributes', None) if hasattr(msg.media, 'document') else None

        await client.send_file(
            target_peer,
            file=temp_file,
            caption=caption,
            reply_to=topic_id,
            attributes=doc_attrs,
            thumb=thumb_path,
            supports_streaming=True
        )
        elapsed = round(time.time() - t_start, 2)
        return True, f"yuklab yuborish orqali {elapsed} soniyada yakunlandi"
    except Exception as e:
        return False, str(e)
    finally:
        if temp_file and os.path.exists(temp_file):
            try: os.remove(temp_file)
            except: pass
        if thumb_path and os.path.exists(thumb_path):
            try: os.remove(thumb_path)
            except: pass

async def process_msg(client, msg, target_peer, topic_id):
    sig = get_sig(msg)
    if sig in processed_videos:
        print(f"-> [{msg.id}] Oldin yuborilgan, tashlab ketildi.")
        return

    caption = clean_and_format_caption(msg.text or "")
    print(f"-> [{msg.id}] Jarayon boshlandi...")
    try:
        ok, detail = await send_safely(client, msg, target_peer, topic_id, caption)
        if ok:
            print(f"✓ [{msg.id}] 53386-mavzuga joylandi ({detail})")
            save_sig(sig)
        else:
            print(f"✗ [{msg.id}] Xatolik: {detail}")
        await asyncio.sleep(2)
    except FloodWaitError as e:
        print(f"Telegram cheklovi: {e.seconds} soniya kutilmoqda...")
        await asyncio.sleep(e.seconds + 2)
    except Exception as e:
        print(f"[{msg.id}] Kutilmagan xato: {e}")
        await asyncio.sleep(1)

async def run_worker():
    client = TelegramClient("salikhmult_session", API_ID, API_HASH, auto_reconnect=True, connection_retries=10, retry_delay=5)
    await client.connect()

    if not await client.is_user_authorized():
        await client.start()

    await client.get_dialogs(limit=30)

    try:
        updates = await client(ImportChatInviteRequest(INVITE_HASH))
        source_chat = updates.chats[0]
    except UserAlreadyParticipantError:
        check = await client(CheckChatInviteRequest(INVITE_HASH))
        source_chat = check.chat
    except Exception as e:
        print(f"Kanalga ulanishda xato: {e}")
        return

    print(f"Kanal aniqlandi: {getattr(source_chat, 'title', 'Kelin')}")
    source_peer = await client.get_input_entity(source_chat)
    target_peer = await client.get_input_entity(TARGET_CHAT_ID)

    print("\nVideolar 53386-mavzuga ko'chirilmoqda...")
    async for msg in client.iter_messages(source_peer, reverse=True):
        if is_strict_video(msg):
            await process_msg(client, msg, target_peer, TARGET_TOPIC_ID)

    print("\nBarcha qismlar muvaffaqiyatli ko'chirildi!")

    @client.on(events.NewMessage(chats=source_chat.id))
    async def new_vid(event):
        if is_strict_video(event.message):
            print(f"\nYangi qism chiqdi: ID {event.message.id}")
            await process_msg(client, event.message, target_peer, TARGET_TOPIC_ID)

    await client.run_until_disconnected()

if __name__ == "__main__":
    asyncio.run(run_worker())
