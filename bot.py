import requests
import time
import asyncio
import os
import re
import threading
import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup

# --- CONFIGURATION ---
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('CHAT_ID')
TARGET_URL = 'https://www.sheinindia.in/c/sverse-5939-37961'
CHECK_INTERVAL = 60 

# Pretend to be a Desktop PC to get the full source code
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9',
}

seen_products = set()
first_run = True

def log(message):
    now = datetime.datetime.now().strftime("%H:%M:%S")
    print(f"[{now}] {message}", flush=True)

# --- DUMMY SERVER ---
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.wfile.write(b"Shein X-Ray Bot Running")
    def log_message(self, format, *args): return

def start_dummy_server():
    port = int(os.getenv("PORT", 8080))
    HTTPServer(('0.0.0.0', port), HealthCheckHandler).serve_forever()

# --- TELEGRAM ALERTS ---
async def send_startup(count):
    if not TELEGRAM_TOKEN or not CHAT_ID: return
    bot = Bot(token=TELEGRAM_TOKEN)
    await bot.send_message(chat_id=CHAT_ID, text=f"☢️ **X-RAY MODE ACTIVE**\n\nI scanned the raw code and found **{count}** hidden items.\nWaiting for new drops...", parse_mode='Markdown')

async def send_alert(pid):
    if not TELEGRAM_TOKEN or not CHAT_ID: return
    bot = Bot(token=TELEGRAM_TOKEN)
    # Reconstruct the link using the ID
    link = f"https://www.sheinindia.in/product-p-{pid}.html"
    keyboard = [[InlineKeyboardButton("🛍️ BUY NOW (APP)", url=link)]]
    markup = InlineKeyboardMarkup(keyboard)
    
    try:
        await bot.send_message(chat_id=CHAT_ID, text=f"🚨 **NEW DROP DETECTED!**\n\n🆔 `{pid}`\n👇 Click to grab it:", parse_mode='Markdown', reply_markup=markup)
    except Exception as e:
        log(f"Telegram Error: {e}")

# --- X-RAY LOGIC ---
def check_for_new_products():
    global first_run
    
    try:
        response = requests.get(TARGET_URL, headers=HEADERS, timeout=20)
        
        # METHOD: Regex Search on RAW TEXT (Bypasses HTML parsing issues)
        # Finds patterns like "-p-1234567" or "goods_id: 1234567"
        found_ids = set(re.findall(r'-p-(\d+)', response.text))
        
        # Sometimes IDs are hidden in JSON as "goods_id"
        json_ids = set(re.findall(r'"goods_id":"(\d+)"', response.text))
        found_ids.update(json_ids)
        
        if len(found_ids) == 0:
            log("⚠️ Still seeing 0 items. Shein might be serving a CAPTCHA page.")
            # Print a snippet of what we actually got (for debugging)
            log(f"Page Preview: {response.text[:100]}...")
            return

        new_items_count = 0
        
        for pid in found_ids:
            if pid not in seen_products:
                seen_products.add(pid)
                if not first_run:
                    log(f"🔥 NEW ITEM: {pid}")
                    asyncio.run(send_alert(pid))
                    new_items_count += 1
        
        if first_run:
            log(f"Initialized. Memorized {len(seen_products)} hidden items.")
            asyncio.run(send_startup(len(seen_products)))
            first_run = False
        elif new_items_count == 0:
            # Heartbeat log so you know it's working
            # log(f"Scanned {len(found_ids)} items. No changes.")
            pass

    except Exception as e: 
        log(f"Error: {e}")

if __name__ == '__main__':
    threading.Thread(target=start_dummy_server, daemon=True).start()
    log("X-Ray Bot Starting...")
    while True:
        check_for_new_products()
        time.sleep(CHECK_INTERVAL)
