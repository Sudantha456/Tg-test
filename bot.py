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

# Local Telegram Bot API Server endpoint එක සැකසීම (is_local=True අනිවාර්ය වේ)
session = AiohttpSession(
    api=TelegramAPIServer.from_base("http://127.0.0.1:8081", is_local=True)
)

bot = Bot(token=BOT_TOKEN, session=session)
dp = Dispatcher()

# Bytes කියවිය හැකි අගයන් (KB, MB, GB) බවට පරිවර්තනය කිරීම
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
    media = message.document or message.video or message.audio
    file_id = media.file_id
    file_size = media.file_size or 0

    status_msg = await message.reply(
        "📊 <b>Starting Speed Test...</b>\n"
        "⚡ <b>Engine:</b> LOCAL BOT API SERVER (2GB Limit)\n"
        f"📦 <b>File Size:</b> {humanbits(file_size)}"
    )

    # ---- 1. DOWNLOAD STEP ----
    start_download = time.time()
    try:
        # Local Server එකෙන් file path එක ලබා ගැනීම
        file_info = await bot.get_file(file_id)
        
        # Local mode එකේදී file_path එක කෙලින්ම local disk path එකක් වේ (Zero-copy transfer)
        source_file_path = file_info.file_path
        
        # Destination folder එකක් සාදා file එක download/copy කිරීම
        download_dest = f"/tmp/dl_{file_info.file_unique_id}"
        await bot.download_file(source_file_path, download_dest)
        
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
        upload_input = FSInputFile(download_dest)
        base_caption = (
            "✅ <b>Speed Test Complete!</b>\n\n"
            "⚡ <b>Server:</b> Local Bot API Server\n"
            f"📦 <b>Size:</b> {humanbits(file_size)}\n"
            f"📥 <b>Download Speed:</b> {humanbits(dl_speed)}/s ({dl_time:.2f}s)\n"
        )

        if message.video:
            sent_msg = await message.reply_video(video=upload_input, caption=base_caption)
        elif message.audio:
            sent_msg = await message.reply_audio(audio=upload_input, caption=base_caption)
        else:
            sent_msg = await message.reply_document(document=upload_input, caption=base_caption)

        ul_time = time.time() - start_upload
        ul_speed = (file_size / ul_time) if ul_time > 0 else 0

        final_caption = base_caption + f"📤 <b>Upload Speed:</b> {humanbits(ul_speed)}/s ({ul_time:.2f}s)"
        await sent_msg.edit_caption(caption=final_caption)

    except Exception as e:
        await status_msg.edit_text(f"❌ <b>Upload Error:</b> {e}")
    finally:
        # Temporary file එක ඉවත් කිරීම (Disk space ඉතිරි කිරීමට)
        if os.path.exists(download_dest):
            os.remove(download_dest)
        try:
            await status_msg.delete()
        except Exception:
            pass

# GitHub Actions limit එකට (පැය 6) පෙර ආරක්ෂිතව නවත්වන ටයිමරය
async def auto_restart_timer():
    await asyncio.sleep(19800) # තත්පර 19800 = පැය 5 විනාඩි 30
    print("Action 6h limit approaching. Stopping dispatcher...")
    await dp.stop_polling()
    sys.exit(0)

async def main():
    print("🚀 Speed Test Bot is starting...")
    
    # 1. Cloud Server එකෙන් Bot එක Log out කිරීම (20MB සීමාව ඉවත් කිරීමට)
    # මේක පළමු වතාවේ පමණක් සාර්ථකව run වේවි. ඉන්පසු error එකක් ආවත් එය bypass වේ.
    try:
        print("Logging out from Telegram Cloud Server...")
        
        # Cloud server එකට request එක යැවීම සඳහා තාවකාලික Cloud session එකක් සෑදීම
        cloud_bot = Bot(token=BOT_TOKEN)
        await cloud_bot.log_out()
        await cloud_bot.session.close()
        
        print("Successfully logged out from Cloud Server.")
    except Exception as e:
        print(f"Log out notice: {e} (This is normal if already logged out)")
    
    # 2. Local API Server එක හරහා Polling ආරම්භ කිරීම
    print("🚀 Bot is now polling via Local Bot Server!")
    asyncio.create_task(auto_restart_timer())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
