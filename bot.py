import requests
from bs4 import BeautifulSoup
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

# 🔒 TARGET: Sheinverse Category
TARGET_URL = 'https://www.sheinindia.in/c/sverse-5939-37961'

# ⚡ SPEED: Check every 45 seconds
CHECK_INTERVAL = 45 

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Mobile Safari/537.36',
    'Accept-Language': 'en-US,en;q=0.9',
    'Referer': 'https://www.sheinindia.in/'
}

seen_products = set()
first_run = True

# --- HELPER: TIMESTAMPED LOGS ---
def log(message):
    # Prints logs with current time for easier debugging in Zeabur
    now = datetime.datetime.now().strftime("%H:%M:%S")
    print(f"[{now}] {message}", flush=True)

# --- DUMMY SERVER (Zeabur Fix) ---
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.wfile.write(b"Shein Bot Pro is Running")
    def log_message(self, format, *args): return

def start_dummy_server():
    port = int(os.getenv("PORT", 8080))
    HTTPServer(('0.0.0.0', port), HealthCheckHandler).serve_forever()

# --- TELEGRAM ALERTS ---
async def send_startup():
    if not TELEGRAM_TOKEN or not CHAT_ID: return
    bot = Bot(token=TELEGRAM_TOKEN)
    await bot.send_message(chat_id=CHAT_ID, text=f"🚀 **BOT UPGRADED & ONLINE**\n\n⚡ Speed: 45s\n🎯 Target: Sheinverse", parse_mode='Markdown')

async def send_alert(link, pid):
    if not TELEGRAM_TOKEN or not CHAT_ID: return
    bot = Bot(token=TELEGRAM_TOKEN)
    keyboard = [[InlineKeyboardButton("🛍️ BUY NOW (APP)", url=link)]]
    markup = InlineKeyboardMarkup(keyboard)
    try:
        # We send the Product ID in the message so you can verify it's new
        await bot.send_message(chat_id=CHAT_ID, text=f"🚨 **NEW DROP DETECTED!**\n\n🆔 ID: `{pid}`\n\n👇 Click to grab it:", parse_mode='Markdown', reply_markup=markup)
    except Exception as e:
        log(f"Telegram Error: {e}")

# --- MAIN CHECK LOGIC ---
def check_for_new_products():
    global first_run
    
    try:
        # Timeout lowered to 15s to fail fast and retry if stuck
        response = requests.get(TARGET_URL, headers=HEADERS, timeout=15)
        
        if response.status_code != 200: 
            log(f"Server returned {response.status_code}. Retrying...")
            return

        soup = BeautifulSoup(response.text, 'html.parser')
        links = soup.find_all('a', href=True)
        
        current_scan_count = 0

        for link in links:
            href = link['href']
            # Strict Filter: Must be a product link
            if '-p-' in href or '/p/' in href:
                full_url = "https:" + href if href.startswith('//') else ("https://www.sheinindia.in" + href if not href.startswith('http') else href)
                try:
                    # Extract ID
                    pid = re.search(r'-p-(\d+)', full_url).group(1)
                    current_scan_count += 1
                    
                    if pid not in seen_products:
                        seen_products.add(pid)
                        if not first_run:
                            log(f"🔥 NEW ITEM: {pid}")
                            asyncio.run(send_alert(full_url, pid))
                except: continue
        
        if first_run:
            log(f"Initialized. Memorized {len(seen_products)} items.")
            first_run = False
        else:
            # Only print this every check if you want to see it working
            # log(f"Scanned {current_scan_count} items. No new drops.")
            pass
            
    except requests.exceptions.RequestException:
        log("Network error (Shein might be slow). Retrying next cycle.")
    except Exception as e: 
        log(f"Unexpected Error: {e}")

if __name__ == '__main__':
    threading.Thread(target=start_dummy_server, daemon=True).start()
    
    log("Bot Starting...")
    asyncio.run(send_startup())
    
    while True:
        check_for_new_products()
        time.sleep(CHECK_INTERVAL)
