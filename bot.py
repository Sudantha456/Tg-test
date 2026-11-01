import os
import sys
import time
import asyncio
from pyrogram import Client, filters, idle
from pyrogram.types import Message

API_ID = int(os.environ.get("API_ID"))
API_HASH = os.environ.get("API_HASH")
BOT_TOKEN = os.environ.get("BOT_TOKEN")

# MTProto Client
app = Client(
    "speed_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
    workers=8
)

def humanbits(size: float) -> str:
    if not size:
        return "0 B"
    power = 1024
    n = 0
    power_labels = {0: '', 1: 'KB', 2: 'MB', 3: 'GB', 4: 'TB'}
    while size >= power and n < len(power_labels) - 1:
        size /= power
        n += 1
    return f"{size:.2f} {power_labels[n]}"

def time_formatter(seconds: float) -> str:
    minutes, sec = divmod(int(seconds), 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours}h {minutes}m {sec}s"
    elif minutes:
        return f"{minutes}m {sec}s"
    return f"{sec}s"

async def progress_bar(current, total, status_msg, action_type, start_time):
    now = time.time()
    diff = now - start_time
    if diff < 0.2:
        return

    if not hasattr(progress_bar, "last_edit"):
        progress_bar.last_edit = 0

    # තත්පර 2කට වරක් progress update කිරීම
    if now - progress_bar.last_edit > 2.0 or current == total:
        progress_bar.last_edit = now
        percentage = (current * 100) / total
        speed = current / diff
        eta = (total - current) / speed if speed > 0 else 0

        filled = int(percentage // 10)
        bar = "▰" * filled + "▱" * (10 - filled)

        text = (
            f"⚡ <b>{action_type}...</b>\n\n"
            f"<code>[{bar}]</code> {percentage:.1f}%\n"
            f"📦 <b>Transferred:</b> {humanbits(current)} / {humanbits(total)}\n"
            f"🚀 <b>Real Speed:</b> {humanbits(speed)}/s\n"
            f"⏱️ <b>ETA:</b> {time_formatter(eta)}"
        )
        try:
            await status_msg.edit_text(text)
        except Exception:
            pass

@app.on_message(filters.document | filters.video | filters.audio)
async def speed_test(client: Client, message: Message):
    media = message.document or message.video or message.audio
    file_size = media.file_size or 0

    status_msg = await message.reply_text(
        f"📊 <b>Starting Pyrogram MTProto Speed Test...</b>\n"
        f"📦 <b>File Size:</b> {humanbits(file_size)}\n"
        f"⚡ <b>Engine:</b> Direct Pyrogram (2GB Mode)"
    )

    # 1. DOWNLOAD STEP
    start_dl = time.time()
    try:
        file_path = await message.download(
            progress=progress_bar,
            progress_args=(status_msg, "📥 Downloading", start_dl)
        )
    except Exception as e:
        await status_msg.edit_text(f"❌ <b>Download Error:</b> {e}")
        return

    dl_time = time.time() - start_dl
    dl_speed = (file_size / dl_time) if dl_time > 0 else 0

    await status_msg.edit_text(
        f"📥 <b>Download Finished!</b>\n"
        f"⏱️ <b>Time:</b> {dl_time:.2f}s\n"
        f"🚀 <b>Speed:</b> {humanbits(dl_speed)}/s\n\n"
        f"📤 <i>Starting Real Upload...</i>"
    )
    await asyncio.sleep(1)

    # 2. UPLOAD STEP
    start_ul = time.time()
    try:
        if message.video:
            sent_msg = await client.send_video(
                chat_id=message.chat.id,
                video=file_path,
                caption="✅ <b>Uploaded via Pyrogram!</b>",
                progress=progress_bar,
                progress_args=(status_msg, "📤 Uploading", start_ul)
            )
        elif message.audio:
            sent_msg = await client.send_audio(
                chat_id=message.chat.id,
                audio=file_path,
                caption="✅ <b>Uploaded via Pyrogram!</b>",
                progress=progress_bar,
                progress_args=(status_msg, "📤 Uploading", start_ul)
            )
        else:
            sent_msg = await client.send_document(
                chat_id=message.chat.id,
                document=file_path,
                caption="✅ <b>Uploaded via Pyrogram!</b>",
                progress=progress_bar,
                progress_args=(status_msg, "📤 Uploading", start_ul)
            )

        ul_time = time.time() - start_ul
        ul_speed = (file_size / ul_time) if ul_time > 0 else 0

        summary = (
            f"🏁 <b>Speed Test Complete!</b>\n\n"
            f"📦 <b>File Size:</b> {humanbits(file_size)}\n"
            f"📥 <b>Download Speed:</b> {humanbits(dl_speed)}/s ({dl_time:.2f}s)\n"
            f"📤 <b>Upload Speed:</b> {humanbits(ul_speed)}/s ({ul_time:.2f}s)"
        )
        await sent_msg.edit_caption(caption=summary)
        await status_msg.delete()

    except Exception as e:
        await status_msg.edit_text(f"❌ <b>Upload Error:</b> {e}")
    finally:
        if file_path and os.path.exists(file_path):
            os.remove(file_path)

async def auto_restart_timer():
    await asyncio.sleep(19800)
    print("Action limit approaching. Stopping bot...")
    await app.stop()
    sys.exit(0)

async def main():
    await app.start()
    print("🚀 Pyrogram Bot is online and listening!")
    asyncio.create_task(auto_restart_timer())
    # Polling updates නිසි ලෙස ක්‍රියාත්මක වීමට idle() භාවිතා කිරීම
    await idle()
    await app.stop()

if __name__ == "__main__":
    app.run(main())
