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
API_KEY = "ad5228b4c6msh52eb82c89fe6e79p1bd725jsned948331ba28"

# --- API PROVIDERS (Dual Engine) ---
PROVIDERS = [
    {
        "name": "Shein V1",
        "host": "shein-api-v1.p.rapidapi.com",
        "url": "https://shein-api-v1.p.rapidapi.com/api/v1/product/search",
        "params": {"keyword": "sverse-5939-37961", "sort": "7", "country": "IN", "limit": "20"}
    },
    {
        "name": "Shein Scraper",
        "host": "shein-scraper-p.rapidapi.com",
        "url": "https://shein-scraper-p.rapidapi.com/products/search",
        "params": {"cat_id": "sverse-5939-37961", "sort": "7", "country": "IN", "limit": "20"}
    }
]

# Start with the first provider
current_provider_index = 0
CHECK_INTERVAL = 300 

seen_ids = set()
first_run = True

# --- DUMMY SERVER ---
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.wfile.write(b"Dual Engine Bot Running")
    def log_message(self, format, *args): return

def start_dummy_server():
    port = int(os.getenv("PORT", 8080))
    print(f"🌍 Server started on port {port}")
    HTTPServer(('0.0.0.0', port), HealthCheckHandler).serve_forever()

# --- TELEGRAM ALERTS ---
async def send_alert(name, price, image, link, pid):
    bot = Bot(token=TELEGRAM_TOKEN)
    caption = f"💎 **API DROP DETECTED!**\n\n📦 **{name}**\n💰 Price: {price}\n🆔 `{pid}`"
    keyboard = [[InlineKeyboardButton("🛍️ BUY NOW", url=link)]]
    try:
        if image:
            await bot.send_photo(chat_id=CHAT_ID, photo=image, caption=caption, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))
        else:
            await bot.send_message(chat_id=CHAT_ID, text=caption, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))
    except Exception as e:
        print(f"Telegram Error: {e}")

async def send_startup(provider_name):
    bot = Bot(token=TELEGRAM_TOKEN)
    await bot.send_message(chat_id=CHAT_ID, text=f"✅ **CONNECTED**\n\nProvider: {provider_name}\nWaiting for drops...", parse_mode='Markdown')

# --- MAIN LOGIC ---
def check_api():
    global first_run, current_provider_index
    
    provider = PROVIDERS[current_provider_index]
    print(f"Testing {provider['name']}... ", end="", flush=True)
    
    headers = {"x-rapidapi-key": API_KEY, "x-rapidapi-host": provider['host']}

    try:
        response = requests.get(provider['url'], headers=headers, params=provider['params'], timeout=20)
        
        # IF BLOCKED (403), SWITCH PROVIDER
        if response.status_code == 403:
            print(f"❌ 403 Forbidden. Switching provider...")
            current_provider_index = (current_provider_index + 1) % len(PROVIDERS)
            return # Try again next loop

        if response.status_code != 200:
            print(f"❌ Error: {response.status_code}")
            return

        data = response.json()
        
        # UNIVERSAL PARSER (Works for both APIs)
        products = []
        # Try finding the list in common locations
        keys_to_check = ['data', 'products', 'result']
        if isinstance(data, dict):
            if 'data' in data and isinstance(data['data'], list): products = data['data']
            elif 'info' in data and 'products' in data['info']: products = data['info']['products']
            elif 'data' in data and 'products' in data['data']: products = data['data']['products']

        if not products:
            print(f"⚠️ No products found.")
            return

        print(f"✅ OK ({len(products)} items).", flush=True)

        for item in products:
            # Extract Data (Handles different naming conventions)
            pid = str(item.get('goods_id') or item.get('id') or item.get('goodsId'))
            name = item.get('goods_name') or item.get('goodsName') or item.get('name')
            
            price = "N/A"
            p_obj = item.get('sale_price') or item.get('retailPrice')
            if isinstance(p_obj, dict): price = p_obj.get('amountWithSymbol', 'N/A')
            
            img = item.get('goods_img') or item.get('main_image') or item.get('mainImage')
            image = f"https:{img}" if img and img.startswith("//") else img
            
            link = f"https://www.sheinindia.in/product-p-{pid}.html"

            if pid and pid not in seen_ids:
                seen_ids.add(pid)
                if not first_run:
                    print(f"🔥 NEW: {pid}", flush=True)
                    asyncio.run(send_alert(name, price, image, link, pid))
        
        if first_run:
            asyncio.run(send_startup(provider['name']))
            first_run = False

    except Exception as e:
        print(f"Error: {e}", flush=True)

if __name__ == '__main__':
    threading.Thread(target=start_dummy_server, daemon=True).start()
    print("🚀 Dual Engine Bot Started...", flush=True)
    while True:
        check_api()
        time.sleep(CHECK_INTERVAL)
