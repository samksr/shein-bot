import requests
import time
import asyncio
import os
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup

# --- CONFIGURATION ---
TELEGRAM_TOKEN = "8166552588:AAEbJnG_Mu3yUmj2gQeJNPtn7h2RgNq4W0o"
CHAT_ID = "1782381176"

# RAPID API CONFIG (Using your verified Key)
API_HOST = "shein-api-v1.p.rapidapi.com"
API_KEY = "ad5228b4c6msh52eb82c89fe6e79p1bd725jsned948331ba28"
API_URL = "https://shein-api-v1.p.rapidapi.com/api/v1/product/search"

# Check every 5 minutes
CHECK_INTERVAL = 300 

QUERY_PARAMS = {
    "keyword": "sverse-5939-37961", 
    "sort": "7",        # New Arrivals
    "country": "IN",
    "language": "en",
    "limit": "20",
    "page": "1"
}

seen_ids = set()
first_run = True

# --- DUMMY SERVER (Keeps Zeabur Happy) ---
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.wfile.write(b"Zeabur API Bot Running")
    def log_message(self, format, *args): return

def start_dummy_server():
    # Zeabur requires us to listen on this specific port
    port = int(os.getenv("PORT", 8080))
    print(f"🌍 Server started on port {port}")
    server = HTTPServer(('0.0.0.0', port), HealthCheckHandler)
    server.serve_forever()

# --- TELEGRAM ALERTS ---
async def send_alert(name, price, image, link, pid):
    bot = Bot(token=TELEGRAM_TOKEN)
    caption = f"💎 **API DROP DETECTED!**\n\n📦 **{name}**\n💰 Price: {price}\n🆔 `{pid}`"
    keyboard = [[InlineKeyboardButton("🛍️ BUY NOW", url=link)]]
    markup = InlineKeyboardMarkup(keyboard)

    try:
        if image:
            await bot.send_photo(chat_id=CHAT_ID, photo=image, caption=caption, parse_mode='Markdown', reply_markup=markup)
        else:
            await bot.send_message(chat_id=CHAT_ID, text=caption, parse_mode='Markdown', reply_markup=markup)
    except Exception as e:
        print(f"Telegram Error: {e}")

async def send_startup(count):
    bot = Bot(token=TELEGRAM_TOKEN)
    await bot.send_message(chat_id=CHAT_ID, text=f"✅ **ZEABUR BOT FIXED**\n\nTracking **{count}** items.", parse_mode='Markdown')

# --- MAIN LOOP ---
def check_api():
    global first_run
    print(f"Contacting API... ", end="", flush=True)
    
    headers = {"x-rapidapi-key": API_KEY, "x-rapidapi-host": API_HOST}

    try:
        response = requests.get(API_URL, headers=headers, params=QUERY_PARAMS, timeout=20)
        if response.status_code != 200:
            print(f"❌ API Error: {response.status_code}")
            return

        data = response.json()
        products = data.get('data', [])
        # Fallback search
        if not products and 'info' in data: products = data['info'].get('products', [])
        
        if not products:
            print(f"⚠️ No products found.")
            return

        print(f"✅ Received {len(products)} items.", flush=True)

        for item in products:
            pid = str(item.get('goods_id') or item.get('id'))
            name = item.get('goods_name') or item.get('name')
            price = item.get('sale_price', {}).get('amountWithSymbol', 'N/A')
            
            img_raw = item.get('goods_img') or item.get('main_image')
            image = f"https:{img_raw}" if img_raw and img_raw.startswith("//") else img_raw
            
            link = f"https://www.sheinindia.in/product-p-{pid}.html"

            if pid not in seen_ids:
                seen_ids.add(pid)
                if not first_run:
                    print(f"🔥 NEW: {pid}", flush=True)
                    asyncio.run(send_alert(name, price, image, link, pid))
        
        if first_run:
            asyncio.run(send_startup(len(seen_ids)))
            first_run = False

    except Exception as e:
        print(f"Error: {e}", flush=True)

if __name__ == '__main__':
    threading.Thread(target=start_dummy_server, daemon=True).start()
    print("🚀 Zeabur Bot Started...", flush=True)
    while True:
        check_api()
        time.sleep(CHECK_INTERVAL)
