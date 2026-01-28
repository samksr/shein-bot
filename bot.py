import requests
from bs4 import BeautifulSoup
import time
import asyncio
import os
import re
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup

# CONFIGURATION
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('CHAT_ID')
TARGET_URL = 'https://www.sheinindia.in/c/sverse-5939-37961'
CHECK_INTERVAL = 60

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Mobile Safari/537.36',
    'Accept-Language': 'en-US,en;q=0.9',
    'Referer': 'https://www.sheinindia.in/'
}

seen_products = set()
first_run = True

# --- DUMMY SERVER (Keeps Zeabur Happy) ---
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.wfile.write(b"Bot is alive")
    def log_message(self, format, *args): return

def start_dummy_server():
    port = int(os.getenv("PORT", 8080))
    HTTPServer(('0.0.0.0', port), HealthCheckHandler).serve_forever()

# --- TELEGRAM LOGIC ---
async def send_startup():
    if not TELEGRAM_TOKEN or not CHAT_ID: return
    bot = Bot(token=TELEGRAM_TOKEN)
    await bot.send_message(chat_id=CHAT_ID, text="✅ **BOT ONLINE!**\n\nI am connected. I will check for drops every 60 seconds.", parse_mode='Markdown')

async def send_alert(link):
    if not TELEGRAM_TOKEN or not CHAT_ID: return
    bot = Bot(token=TELEGRAM_TOKEN)
    keyboard = [[InlineKeyboardButton("🚀 BUY NOW", url=link)]]
    markup = InlineKeyboardMarkup(keyboard)
    try:
        await bot.send_message(chat_id=CHAT_ID, text=f"🚨 **NEW DROP!**\n\n[Open App]({link})", parse_mode='Markdown', reply_markup=markup)
    except Exception as e:
        print(f"Telegram Error: {e}", flush=True)

# --- MAIN LOOP ---
def check_for_new_products():
    global first_run
    # flush=True forces the logs to appear in Zeabur instantly
    print(f"Checking Shein... (Tracking {len(seen_products)} items)", flush=True) 
    
    try:
        response = requests.get(TARGET_URL, headers=HEADERS, timeout=20)
        if response.status_code != 200: 
            print(f"Status: {response.status_code}", flush=True)
            return

        soup = BeautifulSoup(response.text, 'html.parser')
        links = soup.find_all('a', href=True)
        
        for link in links:
            href = link['href']
            if '-p-' in href or '/p/' in href:
                full_url = "https:" + href if href.startswith('//') else ("https://www.sheinindia.in" + href if not href.startswith('http') else href)
                try:
                    pid = re.search(r'-p-(\d+)', full_url).group(1)
                    if pid not in seen_products:
                        seen_products.add(pid)
                        if not first_run:
                            print(f"New Drop: {pid}", flush=True)
                            asyncio.run(send_alert(full_url))
                except: continue
        
        if first_run:
            print("Initialized.", flush=True)
            first_run = False
            
    except Exception as e: 
        print(f"Error: {e}", flush=True)

if __name__ == '__main__':
    threading.Thread(target=start_dummy_server, daemon=True).start()
    
    print("Bot Starting...", flush=True)
    asyncio.run(send_startup()) # <--- Sends the "Connected" message
    
    while True:
        check_for_new_products()
        time.sleep(CHECK_INTERVAL)
