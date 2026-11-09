import asyncio, glob, os, re, sys, time
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from telethon.errors import FloodWaitError, UserAlreadyParticipantError
from telethon.tl.functions.messages import ImportChatInviteRequest, CheckChatInviteRequest
from telethon.tl.types import (
    MessageMediaDocument,
    DocumentAttributeVideo,
    DocumentAttributeAnimated,
    DocumentAttributeFilename
)

sys.stdout.reconfigure(line_buffering=True)

API_ID = 35656569
API_HASH = "f7d00012a8701d50015ae3d051e402fe"
SESSION_STRING = "1ApWapzMBu4L8hW97fZ3d1-NcV6PjqYsc1m2b6wpSympVzXQ4DdHrd0usBnvRlNd196R5FCMonCNVhmLu0Xzmdt-bJg4ebVr_r2nuXAuGL2YQ1mfjBN-8FKAuAqEqo305LJC8KIteT5gaJf9ybztJAa5UQPiR39YurtaQh8bdkBarPaM1o1sogImHGexmZsd8HclSGvJiFEr7SoXxx6aOT8we0mePCwYIe__7yA4_PHynWfxH8MLh0pyqPcGSY4qLaiI03dtq-QW-YKMGiARi4ED4kf0v2TwEKduHGA8TFgP9ZK1bkbAPAa6MNUKzHpcbJavL_bt0MTxzdfNtA6LAk7VJyRKQpek="

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
                if item:
                    processed_videos.add(item)
    except Exception:
        pass

print(f"Baza yuklandi: {len(processed_videos)} ta yuborilgan video mavjud.", flush=True)

def save_sig(sig):
    processed_videos.add(sig)
    with open(HISTORY_FILE, "a", encoding="utf-8") as f:
        f.write(f"{sig}\n")
        f.flush()
        os.fsync(f.fileno())

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
                dur = int(getattr(attr, 'duration', 0))
                break
        return f"{doc.size}_{dur}"
    return f"id_{msg.id}"

def get_clean_caption(msg, fallback_ep_num):
    raw_text = msg.text or ""
    found_num = None

    m1 = re.search(r'(\d+)\s*[-_ ]*qism', raw_text, re.IGNORECASE)
    if m1:
        found_num = int(m1.group(1))
    else:
        if msg.media and hasattr(msg.media, 'document') and msg.media.document:
            for attr in msg.media.document.attributes:
                if isinstance(attr, DocumentAttributeFilename):
                    fname = attr.file_name or ""
                    m2 = re.search(r'(\d+)\s*[-_ ]*qism', fname, re.IGNORECASE)
                    if m2:
                        found_num = int(m2.group(1))
                        break
                    m3 = re.search(r'(?:e|ep|episode|\b)(\d+)\b', fname, re.IGNORECASE)
                    if m3:
                        found_num = int(m3.group(1))
                        break

    actual_ep = found_num if found_num else fallback_ep_num
    caption = f"🎬 Kelin hind seriali {actual_ep}-qism{NEW_SIGNATURE}"
    return actual_ep, caption

class ProgressTracker:
    def __init__(self, action_name, ep_num):
        self.action = action_name
        self.ep = ep_num
        self.last_time = 0
        self.start_time = time.time()

    def __call__(self, current, total):
        now = time.time()
        if now - self.last_time >= 3.0 or current == total:
            self.last_time = now
            percent = (current / total) * 100 if total else 0
            cur_mb = current / (1024 * 1024)
            tot_mb = total / (1024 * 1024) if total else 0
            elapsed = now - self.start_time
            speed = (cur_mb / elapsed) if elapsed > 0 else 0
            print(f"[{self.ep}-qism] {self.action}: {percent:.1f}% ({cur_mb:.1f}/{tot_mb:.1f} MB) - {speed:.2f} MB/s", flush=True)

async def send_safely(client, msg, target_peer, topic_id, caption, ep_num):
    t_start = time.time()
    try:
        await asyncio.wait_for(
            client.send_message(target_peer, file=msg.media, message=caption, reply_to=topic_id),
            timeout=15.0
        )
        elapsed = round(time.time() - t_start, 2)
        return True, f"server orqali {elapsed}s da"
    except Exception:
        pass

    temp_file = thumb_path = None
    try:
        print(f"[{ep_num}-qism] Serverga yuklab olish...", flush=True)
        try:
            thumb_path = await client.download_media(msg.media, file=TEMP_DIR, thumb=-1)
        except Exception:
            thumb_path = None

        prog_down = ProgressTracker("Yuklanmoqda", ep_num)
        temp_file = await client.download_media(msg.media, file=TEMP_DIR, progress_callback=prog_down)

        doc_attrs = getattr(msg.media.document, 'attributes', None) if hasattr(msg.media, 'document') else None

        print(f"[{ep_num}-qism] Mavzuga jo'natilmoqda...", flush=True)
        prog_up = ProgressTracker("Jo'natilmoqda", ep_num)

        await client.send_file(
            target_peer,
            file=temp_file,
            caption=caption,
            reply_to=topic_id,
            attributes=doc_attrs,
            thumb=thumb_path,
            supports_streaming=True,
            progress_callback=prog_up
        )
        elapsed = round(time.time() - t_start, 2)
        return True, f"yuklab jo'natish orqali {elapsed}s da"
    except Exception as e:
        return False, str(e)
    finally:
        if temp_file and os.path.exists(temp_file):
            try: os.remove(temp_file)
            except Exception: pass
        if thumb_path and os.path.exists(thumb_path):
            try: os.remove(thumb_path)
            except Exception: pass

async def process_msg(client, msg, target_peer, topic_id, ep_num):
    actual_ep, caption = get_clean_caption(msg, ep_num)

    # 9-qismdan kichiklarini o'tkazib yuborish
    if actual_ep < 13:
        return

    sig = get_sig(msg)
    if sig in processed_videos:
        return

    print(f"\n==========================================", flush=True)
    print(f"➡️ Navbatdagi: {actual_ep}-qism (ID: {msg.id})", flush=True)

    retry_count = 0
    while retry_count < 3:
        try:
            ok, detail = await send_safely(client, msg, target_peer, topic_id, caption, actual_ep)
            if ok:
                print(f"✅ {caption.splitlines()[0]} joylandi! ({detail})", flush=True)
                save_sig(sig)
                await asyncio.sleep(2)
                return
            else:
                print(f"⚠️ [{actual_ep}-qism] Qayta urinilmoqda ({detail})...", flush=True)
                retry_count += 1
                await asyncio.sleep(3)
        except FloodWaitError as e:
            print(f"⏳ FloodWait: {e.seconds}s...", flush=True)
            await asyncio.sleep(e.seconds + 2)
        except Exception as e:
            print(f"❌ Xato: {e}", flush=True)
            retry_count += 1
            await asyncio.sleep(3)

async def run_worker():
    client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH, auto_reconnect=True, connection_retries=20, retry_delay=5)
    await client.connect()
    if not await client.is_user_authorized():
        print("❌ Xato: Sessiya tasdiqlanmagan!", flush=True)
        return

    me = await client.get_me()
    print(f"Bot akkaunti: {me.first_name} faol.", flush=True)
    await client.get_dialogs(limit=30)

    try:
        updates = await client(ImportChatInviteRequest(INVITE_HASH))
        source_chat = updates.chats[0]
    except UserAlreadyParticipantError:
        check = await client(CheckChatInviteRequest(INVITE_HASH))
        source_chat = check.chat
    except Exception as e:
        print(f"Kanalga ulanish xatosi: {e}", flush=True)
        return

    source_peer = await client.get_input_entity(source_chat)
    target_peer = await client.get_input_entity(TARGET_CHAT_ID)

    current_episode_counter = 0

    print("Videolar tekshirilmoqda (13-qismdan boshlanadi)...", flush=True)
    async for msg in client.iter_messages(source_peer, reverse=True):
        if is_strict_video(msg):
            current_episode_counter += 1
            await process_msg(client, msg, target_peer, TARGET_TOPIC_ID, current_episode_counter)

    print("Barcha mavjud qismlar joylandi! Yangi qismlar kutilmoqda...", flush=True)

    @client.on(events.NewMessage(chats=source_chat.id))
    async def new_vid(event):
        nonlocal current_episode_counter
        if is_strict_video(event.message):
            current_episode_counter += 1
            await process_msg(client, event.message, target_peer, TARGET_TOPIC_ID, current_episode_counter)

    await client.run_until_disconnected()

if __name__ == "__main__":
    asyncio.run(run_worker())
