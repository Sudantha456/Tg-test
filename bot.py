import os
import sys
import time
import asyncio
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, FSInputFile
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.client.telegram import TelegramAPIServer

# GitHub Secrets මඟින් පරිසර විචල්‍ය ලබා ගැනීම
BOT_TOKEN = os.environ.get("BOT_TOKEN")
LOCAL_SERVER_URL = "http://127.0.0.1:8081"

# Local Bot API Server එකට AiohttpSession එක සකස් කිරීම
session = AiohttpSession(
    api=TelegramAPIServer.from_base(LOCAL_SERVER_URL, is_local=True)
)

bot = Bot(token=BOT_TOKEN, session=session)
dp = Dispatcher()

# Bytes කියවිය හැකි අගයන් බවට පරිවර්තනය කිරීම
def humanbits(size: float) -> str:
    if not size:
        return "0 B"
    power = 1024
    n = 0
    power_labels = {0: '', 1: 'K', 2: 'M', 3: 'G', 4: 'T'}
    while size > power:
        size /= power
        n += 1
    return f"{size:.2f} {power_labels[n]}B"

@dp.message(F.document | F.video | F.audio)
async def speed_test_handler(message: Message):
    # ලැබුණු මාධ්‍ය වර්ගය හඳුනා ගැනීම
    media = message.document or message.video or message.audio
    file_id = media.file_id
    file_name = getattr(media, "file_name", "downloaded_file")
    file_size = media.file_size or 0

    status_msg = await message.reply(
        "📊 <b>Starting Speed Test...</b>\n"
        "⚡ <b>Engine:</b> LOCAL BOT API (Aiogram v3)\n"
        f"📦 <b>File Size:</b> {humanbits(file_size)}"
    )

    # ---- 1. DOWNLOAD STEP ----
    start_download = time.time()
    try:
        # Local Server එකෙන් File තොරතුරු ලබා ගැනීම
        file_info = await bot.get_file(file_id)
        
        # Local server mode (--local) සක්‍රීය විට file_path එක සෘජුවම disk එකේ පවතින absolute path එක වේ
        destination_path = f"/tmp/{file_name}"
        
        await bot.download_file(file_info.file_path, destination_path)
    except Exception as e:
        await status_msg.edit_text(f"❌ <b>Download Error:</b> {e}")
        return

    dl_time = time.time() - start_download
    dl_speed = (file_size / dl_time) if dl_time > 0 else 0

    await status_msg.edit_text(
        f"📥 <b>Download Finished!</b>\n"
        f"⏱️ <b>Time:</b> {dl_time:.2f}s ({humanbits(dl_speed)}/s)\n\n"
        f"📤 Uploading back to Telegram..."
    )

    # ---- 2. UPLOAD STEP ----
    start_upload = time.time()
    try:
        upload_input = FSInputFile(destination_path)

        caption = (
            "✅ <b>Speed Test Complete!</b>\n\n"
            "⚡ <b>Engine:</b> Local Bot API Server\n"
            f"📦 <b>Size:</b> {humanbits(file_size)}\n"
            f"📥 <b>Download Speed:</b> {humanbits(dl_speed)}/s ({dl_time:.2f}s)\n"
        )

        if message.video:
            sent_msg = await message.reply_video(video=upload_input, caption=caption)
        elif message.audio:
            sent_msg = await message.reply_audio(audio=upload_input, caption=caption)
        else:
            sent_msg = await message.reply_document(document=upload_input, caption=caption)

        ul_time = time.time() - start_upload
        ul_speed = (file_size / ul_time) if ul_time > 0 else 0

        # Upload වේගය ද සහිතව Caption එක update කිරීම
        caption += f"📤 <b>Upload Speed:</b> {humanbits(ul_speed)}/s ({ul_time:.2f}s)"
        await sent_msg.edit_caption(caption=caption)

    except Exception as e:
        await status_msg.edit_text(f"❌ <b>Upload Error:</b> {e}")
    finally:
        # තාවකාලික ගොනුව මැකීම
        if os.path.exists(destination_path):
            os.remove(destination_path)
        try:
            await status_msg.delete()
        except Exception:
            pass

# GitHub Actions runner සීමාවට පෙර ආරක්ෂිතව නවත්වන ටයිමරය (පැය 5 විනාඩි 30)
async def auto_restart_timer():
    await asyncio.sleep(19800)
    print("Action 6h limit approaching. Stopping dispatcher...")
    await dp.stop_polling()
    sys.exit(0)

async def main():
    print("🚀 Speed Test Bot is running via Local Bot Server (Aiogram)!")
    asyncio.create_task(auto_restart_timer())
    # Polling ආරම්භ කිරීම
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
