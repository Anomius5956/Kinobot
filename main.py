import asyncio, glob, math, os, re, time
from telethon import TelegramClient, events
from telethon.errors import FloodWaitError, UserAlreadyParticipantError
from telethon.tl.functions.messages import ImportChatInviteRequest, CheckChatInviteRequest
from telethon.tl.types import (
    MessageMediaDocument,
    DocumentAttributeVideo,
    DocumentAttributeAnimated,
    DocumentAttributeFilename,
    InputFileLocation,
    InputDocumentFileLocation
)

API_ID = 35656569
API_HASH = "f7d00012a8701d50015ae3d051e402fe"

INVITE_HASH = "XVjpEsGZUDpkYzgy"
TARGET_CHAT_ID = -1003025094654
TARGET_TOPIC_ID = 53386

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

def clean_and_format_caption(old_text, msg=None):
    text = old_text or ""
    ep = None
    m = re.search(r'(\d+)\s*[-_ ]*qism', text, re.IGNORECASE)
    if m:
        ep = m.group(1)
    else:
        if msg and msg.media and hasattr(msg.media, 'document') and msg.media.document:
            for attr in msg.media.document.attributes:
                if isinstance(attr, DocumentAttributeFilename):
                    fname = attr.file_name or ""
                    m2 = re.search(r'(\d+)\s*[-_ ]*qism', fname, re.IGNORECASE)
                    if m2:
                        ep = m2.group(1); break
                    m3 = re.search(r'(\d+)', fname)
                    if m3:
                        ep = m3.group(1); break

    if ep:
        return f"🎬 Kelin hind seriali {ep}-qism{NEW_SIGNATURE}"

    bad_patterns = [
        r"https?://\S+", r"t\.me/\S+", r"tg://\S+", r"www\.\S+",
        r"@\w+", r"#\w+", r"\[.*?\]", r"\(.*?\)",
        r"(?i)asosiy kanal.*", r"(?i)bizga qo['`]?shiling.*",
        r"(?i)kanalimiz.*", r"(?i)bizning kanal.*",
        r"(?i)kanalga o['`]?tish.*", r"(?i)do['`]?stlarga ulashing.*",
        r"(?i)reklama.*", r"(?i)admin.*", r"(?i)homiy.*", r"(?i)juda kop.*"
    ]
    for p in bad_patterns:
        text = re.sub(p, "", text)

    cleaned = "\n".join([line.strip() for line in text.split("\n") if line.strip()])
    return f"🎬 {cleaned}{NEW_SIGNATURE}" if cleaned else f"🎬 Kelin hind seriali{NEW_SIGNATURE}"

async def send_safely(client, msg, target_peer, topic_id, caption):
    t_start = time.time()
    
    # 1. To'g'ridan-to'g'ri Telegram serveri orqali o'tkazish (eng tez usul, 1-2 soniya)
    try:
        await asyncio.wait_for(
            client.send_message(target_peer, file=msg.media, message=caption, reply_to=topic_id),
            timeout=20.0
        )
        elapsed = round(time.time() - t_start, 2)
        return True, f"server orqali {elapsed} soniyada"
    except Exception:
        pass

    # 2. Agar server ruxsat bermasa, yuklab yuborish
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
        return True, f"yuklab yuborish orqali {elapsed} soniyada"
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
        return

    caption = clean_and_format_caption(msg.text or "", msg)
    try:
        ok, detail = await send_safely(client, msg, target_peer, topic_id, caption)
        if ok:
            print(f"✓ [{msg.id}] Mavzuga joylandi ({detail})")
            save_sig(sig)
        await asyncio.sleep(2)
    except FloodWaitError as e:
        print(f"Telegram cheklovi: {e.seconds}s...")
        await asyncio.sleep(e.seconds + 2)
    except Exception as e:
        print(f"[{msg.id}] Xato: {e}")
        await asyncio.sleep(1)

async def run_worker():
    client = TelegramClient("railway_session", API_ID, API_HASH, auto_reconnect=True, connection_retries=10, retry_delay=5)
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
        print(f"Ulanishda xato: {e}")
        return

    source_peer = await client.get_input_entity(source_chat)
    target_peer = await client.get_input_entity(TARGET_CHAT_ID)

    async for msg in client.iter_messages(source_peer, reverse=True):
        if is_strict_video(msg):
            await process_msg(client, msg, target_peer, TARGET_TOPIC_ID)

    @client.on(events.NewMessage(chats=source_chat.id))
    async def new_vid(event):
        if is_strict_video(event.message):
            await process_msg(client, event.message, target_peer, TARGET_TOPIC_ID)

    await client.run_until_disconnected()

if __name__ == "__main__":
    asyncio.run(run_worker())
