import requests
import time
import asyncio
import os
import json
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup

# --- CONFIGURATION ---
# Load variables from Zeabur (or use defaults for testing)
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
API_KEY = os.getenv("API_KEY")

# API SETTINGS (Engine: shein-scraper-api)
API_HOST = "shein-scraper-api.p.rapidapi.com"
API_URL = "https://shein-scraper-api.p.rapidapi.com/shein/product/list"
CHECK_INTERVAL = 300  # Check every 5 minutes

# SEARCH PARAMS
QUERY_PARAMS = {
    "cat_id": "sverse-5939-37961",
    "sort": "7",        # New Arrivals
    "country": "IN",
    "limit": "20"
}

seen_ids = set()
first_run = True

# --- DUMMY SERVER (Keeps Zeabur Alive) ---
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.wfile.write(b"Bot Running")
    def log_message(self, format, *args): return

def start_server():
    port = int(os.getenv("PORT", 8080))
    print(f"🌍 Web Server listening on {port}")
    HTTPServer(('0.0.0.0', port), HealthCheckHandler).serve_forever()

# --- TELEGRAM FUNCTIONS ---
async def send_alert(name, price, image, link, pid):
    if not TELEGRAM_TOKEN: return
    bot = Bot(token=TELEGRAM_TOKEN)
    caption = f"💎 **NEW DROP!**\n\n📦 **{name}**\n💰 {price}\n🆔 `{pid}`"
    keyboard = [[InlineKeyboardButton("🛍️ BUY NOW", url=link)]]
    try:
        if image:
            await bot.send_photo(chat_id=CHAT_ID, photo=image, caption=caption, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))
        else:
            await bot.send_message(chat_id=CHAT_ID, text=caption, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))
    except Exception as e:
        print(f"Telegram Fail: {e}")

async def send_startup():
    if not TELEGRAM_TOKEN: return
    bot = Bot(token=TELEGRAM_TOKEN)
    await bot.send_message(chat_id=CHAT_ID, text="✅ **BOT RESTARTED & ONLINE**")

# --- MAIN LOOP ---
def check_api():
    global first_run
    print(f"Checking API...", end="", flush=True)
    
    headers = {"x-rapidapi-key": API_KEY, "x-rapidapi-host": API_HOST}

    try:
        response = requests.get(API_URL, headers=headers, params=QUERY_PARAMS, timeout=20)
        
        if response.status_code == 403:
            print(" ❌ 403 ERROR! (You must Subscribe to the API on RapidAPI website)")
            return
        
        if response.status_code != 200:
            print(f" ❌ Error {response.status_code}")
            return

        data = response.json()
        # Extract products safely
        products = data.get('info', {}).get('products', [])
        
        if not products:
            print(" ⚠️ No items found.")
            return

        print(f" ✅ Found {len(products)} items.", flush=True)

        for item in products:
            pid = str(item.get('goods_id'))
            name = item.get('goods_name', 'Unknown')
            price = item.get('sale_price', {}).get('amountWithSymbol', 'N/A')
            img = item.get('goods_img')
            image = f"https:{img}" if img and img.startswith("//") else img
            link = f"https://www.sheinindia.in/product-p-{pid}.html"

            if pid not in seen_ids:
                seen_ids.add(pid)
                if not first_run:
                    print(f" 🔥 NEW: {pid}")
                    asyncio.run(send_alert(name, price, image, link, pid))

        if first_run:
            asyncio.run(send_startup())
            first_run = False

    except Exception as e:
        print(f" Error: {e}")

if __name__ == '__main__':
    # Start Web Server
    threading.Thread(target=start_server, daemon=True).start()
    
    # Start Bot Loop
    print("🚀 Bot Started...")
    while True:
        check_api()
        time.sleep(CHECK_INTERVAL)
