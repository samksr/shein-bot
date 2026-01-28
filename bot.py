import cloudscraper
import time
import asyncio
import re
import requests
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup

# --- CREDENTIALS ---
TELEGRAM_TOKEN = "8166552588:AAEbJnG_Mu3yUmj2gQeJNPtn7h2RgNq4W0o"
CHAT_ID = "1782381176"

TARGET_URL = 'https://www.sheinindia.in/c/sverse-5939-37961'
CHECK_INTERVAL = 45

seen_products = set()
first_run = True

async def send_startup(count):
    bot = Bot(token=TELEGRAM_TOKEN)
    await bot.send_message(chat_id=CHAT_ID, text=f"🛡️ **ROBUST BOT ACTIVE**\n\nConnection secured.\nFound **{count}** existing items.", parse_mode='Markdown')

async def send_alert(pid):
    bot = Bot(token=TELEGRAM_TOKEN)
    link = f"https://www.sheinindia.in/product-p-{pid}.html"
    keyboard = [[InlineKeyboardButton("🛍️ BUY NOW (APP)", url=link)]]
    markup = InlineKeyboardMarkup(keyboard)
    try:
        await bot.send_message(chat_id=CHAT_ID, text=f"🚨 **NEW DROP!**\n\n🆔 `{pid}`", parse_mode='Markdown', reply_markup=markup)
    except Exception as e:
        print(f"Telegram Error: {e}")

def check_for_new_products():
    global first_run
    print(f"Scanning... ", end="")
    
    try:
        # Create scraper with specific mobile browser footprint
        scraper = cloudscraper.create_scraper(
            browser={'browser': 'chrome', 'platform': 'android', 'mobile': True}
        )
        
        # Timeout added to prevent hanging
        response = scraper.get(TARGET_URL, timeout=15)
        
        # Check for Hard Block
        if response.status_code == 403 or "Access Denied" in response.text:
            print("❌ BLOCKED. (Toggle Airplane Mode for 5s!)")
            return

        # X-RAY SCAN
        found_ids = set(re.findall(r'-p-(\d+)', response.text))
        found_ids.update(re.findall(r'"goods_id":"(\d+)"', response.text))
        
        if len(found_ids) == 0:
            # DEBUG: Print what the page actually is
            page_title = re.search(r'<title>(.*?)</title>', response.text)
            title_text = page_title.group(1) if page_title else "Unknown Page"
            print(f"⚠️ 0 items. Page Title: [{title_text}]")
            return

        print(f"✅ OK ({len(found_ids)} items)")

        for pid in found_ids:
            if pid not in seen_products:
                seen_products.add(pid)
                if not first_run:
                    print(f"🔥 NEW: {pid}")
                    asyncio.run(send_alert(pid))
        
        if first_run:
            asyncio.run(send_startup(len(seen_products)))
            first_run = False
            
    except requests.exceptions.ConnectionError:
        print("⚠️ No Internet. Waiting...")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == '__main__':
    print("🚀 Robust Bot Started...")
    while True:
        check_for_new_products()
        time.sleep(CHECK_INTERVAL)
