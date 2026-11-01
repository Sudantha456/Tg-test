import os
import sys
import time
import asyncio
from pyrogram import Client, filters
import pyrogram

# Env Variables (GitHub Secrets මඟින් ලබා ගනී)
API_ID = int(os.environ.get("API_ID"))
API_HASH = os.environ.get("API_HASH")
BOT_TOKEN = os.environ.get("BOT_TOKEN")

app = Client(
    "speed_test_bot",
    bot_token=BOT_TOKEN,
    api_id=API_ID,
    api_hash=API_HASH,
    # Workflow එකේ සකස් කළ Local Bot Server Port එක (8081)
    api_server=pyrogram.raw.types.InputApiServer(
        base_url="http://127.0.0.1:8081",
        fallback_url=""
    )
)

# ප්‍රමාණයන් කියවිය හැකි ලෙස සකසන ශ්‍රිතය (Bytes to KB/MB)
def humanbits(size):
    if not size:
        return "0 B"
    power = 1024
    n = 0
    power_labels = {0: '', 1: 'K', 2: 'M', 3: 'G', 4: 'T'}
    while size > power:
        size /= power
        n += 1
    return f"{size:.2f} {power_labels[n]}B"

# කාලය කියවිය හැකි ලෙස සකසන ශ්‍රිතය (Seconds to Time)
def time_formatter(milliseconds: int) -> str:
    seconds, milliseconds = divmod(int(milliseconds), 1000)
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    days, hours = divmod(hours, 24)
    tmp = ((str(days) + "d, ") if days else "") + \
          ((str(hours) + "h, ") if hours else "") + \
          ((str(minutes) + "m, ") if minutes else "") + \
          ((str(seconds) + "s, ") if seconds else "") + \
          ((str(milliseconds) + "ms, ") if milliseconds else "")
    return tmp[:-2]

# සජීවීව Speed එක සහ Progress එක Telegram එකේ පෙන්වන ප්‍රධාන ශ්‍රිතය
async def progress_bar(current, total, reply_msg, type_of_ps, start_time):
    now = time.time()
    diff = now - start_time
    
    # හැම තත්පර 3කට වරක් පමණක් Message එක Update කරයි (Telegram FloodWait නොවීමට)
    if round(diff % 3.00) == 0 or current == total:
        percentage = current * 100 / total
        speed = current / diff
        elapsed_time = round(diff) * 1000
        time_to_completion = round((total - current) / speed) * 1000
        estimated_total_time = elapsed_time + time_to_completion

        elapsed_time_str = time_formatter(elapsed_time)
        estimated_total_time_str = time_formatter(estimated_total_time)

        # Progress Bar එක සෑදීම
        progress = "".join(["▰" for i in range(int(percentage // 10))])
        remaining = "".join(["▱" for i in range(10 - int(percentage // 10))])
        
        tmp = f"{type_of_ps}...\n" \
              f"<code>[{progress}{remaining}]</code> {percentage:.2f}%\n" \
              f"<b>Completed:</b> {humanbits(current)} / {humanbits(total)}\n" \
              f"<b>Speed:</b> {humanbits(speed)}/s\n" \
              f"<b>Time Elapsed:</b> {elapsed_time_str if elapsed_time_str else '0s'}\n" \
              f"<b>ETA:</b> {time_formatter(time_to_completion) if time_to_completion else '0s'}\n"
        
        try:
            await reply_msg.edit_text(tmp)
        except Exception:
            pass

@app.on_message(filters.document | filters.video | filters.audio)
async def speed_test_handler(client, message):
    # Local Bot Server එක සම්බන්ධ දැයි මුලින්ම පරීක්ෂා කිරීම
    is_local = app.api_server.base_url == "http://127.0.0.1:8081"
    server_status = "⚡ LOCAL BOT SERVER" if is_local else "☁️ TELEGRAM CLOUD"
    
    status_msg = await message.reply_text(f"📊 Starting Speed Test...\n<b>Server:</b> {server_status}")
    
    # ---- 1. DOWNLOAD STEP ----
    start_download = time.time()
    try:
        file_path = await message.download(
            progress=progress_bar,
            progress_args=("📥 <b>Downloading</b>", status_msg, start_download)
        )
    except Exception as e:
        await status_msg.edit_text(f"❌ Download Error: {e}")
        return

    dl_time = time.time() - start_download
    await status_msg.edit_text(f"📥 Download Finished in {dl_time:.2f}s!\nPreparing to upload back...")
    await asyncio.sleep(1)

    # ---- 2. UPLOAD STEP ----
    start_upload = time.time()
    try:
        await client.send_video(
            chat_id=message.chat.id,
            video=file_path,
            caption=f"✅ <b>Speed Test Complete!</b>\n\n"
                    f"⚙️ <b>Server:</b> {server_status}\n"
                    f"⏱️ <b>Download Time:</b> {dl_time:.2f} seconds\n"
                    f"⏱️ <b>Upload Time:</b> {time.time() - start_upload:.2f} seconds",
            progress=progress_bar,
            progress_args=("📤 <b>Uploading</b>", status_msg, start_upload)
        )
    except Exception as e:
        await status_msg.edit_text(f"❌ Upload Error: {e}")
    finally:
        # 3. Disk Space ආරක්ෂා කර ගැනීමට තාවකාලික ෆයිල් එක මැකීම
        if os.path.exists(file_path):
            os.remove(file_path)
        await status_msg.delete()

# GitHub Actions සඳහා පැය 5.5කින් Auto-Shutdown වන Timer එක
async def auto_restart_timer():
    await asyncio.sleep(19800) # තත්පර 19800 = පැය 5 විනාඩි 30
    print("Time limit reached. Stopping bot to trigger Action Auto-Restart...")
    await app.stop()
    sys.exit(0)

async def main():
    await app.start()
    print("🚀 Speed Test Bot is running with Local Bot Server on GitHub Actions!")
    asyncio.create_task(auto_restart_timer())
    await pyrogram.idle()

if __name__ == "__main__":
    asyncio.run(main())
