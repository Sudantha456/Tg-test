import os
import sys
import time
import asyncio
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.client.telegram import TelegramAPIServer
from aiogram.client.default import DefaultBotProperties

BOT_TOKEN = os.environ.get("BOT_TOKEN")

session = AiohttpSession(
    api=TelegramAPIServer.from_base("http://127.0.0.1:8081", is_local=True)
)

bot = Bot(
    token=BOT_TOKEN, 
    session=session,
    default=DefaultBotProperties(parse_mode="HTML")
)
dp = Dispatcher()

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

async def upload_spinner(msg: Message, start_time: float, file_size_str: str):
    frames = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
    i = 0
    try:
        while True:
            elapsed = time.time() - start_time
            frame = frames[i % len(frames)]
            i += 1
            try:
                await msg.edit_text(
                    f"📤 <b>Uploading to Telegram... {frame}</b>\n\n"
                    f"📦 <b>Size:</b> {file_size_str}\n"
                    f"⏱️ <b>Elapsed Time:</b> {elapsed:.0f}s\n\n"
                    f"<i>⚡ True Zero-Copy mode active.</i>"
                )
            except Exception:
                pass
            await asyncio.sleep(2)
    except asyncio.CancelledError:
        pass

@dp.message(F.document | F.video | F.audio)
async def speed_test_handler(message: Message):
    media = message.document or message.video or message.audio
    file_id = media.file_id
    file_size = media.file_size or 0
    size_str = humanbits(file_size)

    status_msg = await message.reply(
        "📊 <b>Starting Speed Test...</b>\n"
        "⚡ <b>Engine:</b> LOCAL BOT API (True Zero-Copy)\n"
        f"📦 <b>File Size:</b> {size_str}"
    )

    # ---- DOWNLOAD STEP ----
    start_download = time.time()
    try:
        file_info = await bot.get_file(file_id)
        real_file_path = file_info.file_path
        
    except Exception as e:
        await status_msg.edit_text(f"❌ <b>Download Error:</b> {e}")
        return

    dl_time = time.time() - start_download
    dl_speed = (file_size / dl_time) if dl_time > 0 else 0

    await status_msg.edit_text(
        f"📥 <b>Download Finished Instantly!</b>\n"
        f"⏱️ <b>Time:</b> {dl_time:.2f}s (Direct File Mapping)\n\n"
        f"⏳ Preparing to upload..."
    )
    await asyncio.sleep(1)

    # ---- UPLOAD STEP ----
    start_upload = time.time()
    spinner_task = asyncio.create_task(upload_spinner(status_msg, start_upload, size_str))
    
    try:
        # 💡 TRUE ZERO-COPY: FSInputFile වෙනුවට කෙලින්ම file:// URI එක ලබා දීම!
        # මේ නිසා Python file එක read නොකරන අතර Permission error එකක් එන්නේ නැත.
        upload_input = f"file://{real_file_path}"
        
        base_caption = (
            "✅ <b>Speed Test Complete!</b>\n\n"
            "⚡ <b>Server:</b> Local Bot API Server\n"
            f"📦 <b>Size:</b> {size_str}\n"
            f"📥 <b>Download:</b> {humanbits(dl_speed)}/s (Direct)\n"
        )

        if message.video:
            sent_msg = await message.reply_video(video=upload_input, caption=base_caption)
        elif message.audio:
            sent_msg = await message.reply_audio(audio=upload_input, caption=base_caption)
        else:
            sent_msg = await message.reply_document(document=upload_input, caption=base_caption)

        spinner_task.cancel()
        ul_time = time.time() - start_upload
        ul_speed = (file_size / ul_time) if ul_time > 0 else 0

        final_caption = base_caption + f"📤 <b>Upload Speed:</b> {humanbits(ul_speed)}/s ({ul_time:.2f}s)"
        await sent_msg.edit_caption(caption=final_caption)
        
        await status_msg.delete()

    except Exception as e:
        spinner_task.cancel()
        await status_msg.edit_text(f"❌ <b>Upload Error:</b> {e}")

async def auto_restart_timer():
    await asyncio.sleep(19800)
    print("Action limit approaching. Stopping dispatcher...")
    await dp.stop_polling()
    sys.exit(0)

async def main():
    print("🚀 Bot is polling via Local Bot Server (True Zero-Copy)!")
    asyncio.create_task(auto_restart_timer())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
