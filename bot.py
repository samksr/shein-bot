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
TARGET_URL = 'https://www.sheinindia.in/c/sverse-5939-37961'
CHECK_INTERVAL = 45

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9',
    'Referer': 'https://www.sheinindia.in/'
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
        self.wfile.write(b"Shein Image Bot Running")
    def log_message(self, format, *args): return

def start_dummy_server():
    port = int(os.getenv("PORT", 8080))
    HTTPServer(('0.0.0.0', port), HealthCheckHandler).serve_forever()

# --- TELEGRAM ALERTS ---
async def send_startup():
    if not TELEGRAM_TOKEN or not CHAT_ID: return
    bot = Bot(token=TELEGRAM_TOKEN)
    await bot.send_message(chat_id=CHAT_ID, text=f"🚀 **BOT RELOADED**\n\n📸 Now sending Images + Links\n⚡ Check Rate: 45s", parse_mode='Markdown')

async def send_alert(link, pid, image_url):
    if not TELEGRAM_TOKEN or not CHAT_ID: return
    bot = Bot(token=TELEGRAM_TOKEN)
    
    keyboard = [[InlineKeyboardButton("🛍️ BUY NOW (APP)", url=link)]]
    markup = InlineKeyboardMarkup(keyboard)
    
    caption = f"🚨 **NEW DROP DETECTED!**\n\n🆔 `{pid}`\n👇 Click to grab it:"
    
    try:
        if image_url:
            await bot.send_photo(chat_id=CHAT_ID, photo=image_url, caption=caption, parse_mode='Markdown', reply_markup=markup)
        else:
            # Fallback if image fails
            await bot.send_message(chat_id=CHAT_ID, text=caption, parse_mode='Markdown', reply_markup=markup)
    except Exception as e:
        log(f"Telegram Error: {e}")

# --- MAIN LOGIC ---
def check_for_new_products():
    global first_run
    
    try:
        response = requests.get(TARGET_URL, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(response.text, 'html.parser')
        links = soup.find_all('a', href=True)
        
        current_count = 0

        for link in links:
            href = link['href']
            if '-p-' in href or '/p/' in href:
                full_url = "https:" + href if href.startswith('//') else ("https://www.sheinindia.in" + href if not href.startswith('http') else href)
                
                try:
                    pid = re.search(r'-p-(\d+)', full_url).group(1)
                    current_count += 1
                    
                    if pid not in seen_products:
                        seen_products.add(pid)
                        
                        if not first_run:
                            # --- IMAGE EXTRACTION LOGIC ---
                            img_tag = link.find('img')
                            image_url = None
                            if img_tag:
                                # Try 'data-src' first (Shein uses this for lazy loading)
                                raw_img = img_tag.get('data-src') or img_tag.get('src')
                                if raw_img:
                                    if raw_img.startswith('//'):
                                        image_url = "https:" + raw_img
                                    elif raw_img.startswith('http'):
                                        image_url = raw_img
                            
                            log(f"🔥 NEW ITEM: {pid} (Img: {'Yes' if image_url else 'No'})")
                            asyncio.run(send_alert(full_url, pid, image_url))
                            
                except: continue
        
        if first_run:
            log(f"Initialized. Memorized {len(seen_products)} items.")
            first_run = False

    except Exception as e: 
        log(f"Error: {e}")

if __name__ == '__main__':
    threading.Thread(target=start_dummy_server, daemon=True).start()
    log("Image Bot Starting...")
    asyncio.run(send_startup())
    while True:
        check_for_new_products()
        time.sleep(CHECK_INTERVAL)
