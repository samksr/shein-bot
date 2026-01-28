import asyncio
import json
import logging
import os
import threading
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Dict, List, Optional

import requests
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup

# --- CONFIGURATION ---
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
API_KEY = os.getenv("API_KEY")
CHECK_INTERVAL = int(os.getenv("CHECK_INTERVAL", "300"))
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

# --- TRIPLE ENGINE PROVIDERS ---
PROVIDERS = [
    {
        "name": "Engine 1 (Scraper)",
        "host": "shein-scraper.p.rapidapi.com",
        "url": "https://shein-scraper.p.rapidapi.com/products/search",
        "params": {"cat_id": "sverse-5939-37961", "sort": "7", "country": "IN", "limit": "20"}
    },
    {
        "name": "Engine 2 (Scraper API)",
        "host": "shein-scraper-api.p.rapidapi.com",
        "url": "https://shein-scraper-api.p.rapidapi.com/shein/product/list",
        "params": {"cat_id": "sverse-5939-37961", "sort": "7", "country": "IN", "limit": "20"}
    },
    {
        "name": "Engine 3 (Shein V1)",
        "host": "shein-api-v1.p.rapidapi.com",
        "url": "https://shein-api-v1.p.rapidapi.com/api/v1/product/search",
        "params": {"cat_id": "sverse-5939-37961", "sort": "7", "country": "IN", "limit": "20"}
    }
]

# Global state
current_provider_index = 0
seen_ids_file = "seen_ids.json"
seen_ids = set()
first_run = True

# Setup logging
logging.basicConfig(level=getattr(logging, LOG_LEVEL), format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Load seen IDs
if os.path.exists(seen_ids_file):
    try:
        with open(seen_ids_file, "r") as f:
            seen_ids = set(json.load(f))
    except Exception as e:
        logger.warning(f"Failed to load seen_ids: {e}")

# --- DUMMY SERVER ---
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        status = {"status": "Triple Engine Bot Running", "provider": PROVIDERS[current_provider_index]["name"]}
        self.wfile.write(json.dumps(status).encode())
    def log_message(self, format, *args): return

def start_dummy_server():
    port = int(os.getenv("PORT", 8080))
    logger.info(f"🌍 Server started on port {port}")
    HTTPServer(('0.0.0.0', port), HealthCheckHandler).serve_forever()

# --- TELEGRAM ALERTS ---
async def send_alert(name, price, image, link, pid, description=None):
    if not TELEGRAM_TOKEN or not CHAT_ID: return
    bot = Bot(token=TELEGRAM_TOKEN)
    caption = f"💎 **API DROP DETECTED!**\n\n📦 **{name}**\n💰 Price: {price}\n🆔 `{pid}`"
    if description: caption += f"\n📝 {description[:100]}..."
    keyboard = [[InlineKeyboardButton("🛍️ BUY NOW", url=link)]]
    try:
        await bot.send_photo(chat_id=CHAT_ID, photo=image, caption=caption, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard)) if image else \
        await bot.send_message(chat_id=CHAT_ID, text=caption, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))
        logger.info(f"Alert sent for {pid}")
    except Exception as e:
        logger.error(f"Telegram Error for {pid}: {e}")

async def send_startup(provider_name):
    if not TELEGRAM_TOKEN or not CHAT_ID: return
    bot = Bot(token=TELEGRAM_TOKEN)
    try:
        await bot.send_message(chat_id=CHAT_ID, text=f"✅ **CONNECTED**\n\nUsing: {provider_name}\nWaiting for drops...", parse_mode='Markdown')
    except Exception as e:
        logger.error(f"Startup Error: {e}")

# --- UTILS ---
def save_seen_ids():
    try:
        with open(seen_ids_file, "w") as f: json.dump(list(seen_ids), f)
    except Exception as e: logger.warning(f"Failed to save seen_ids: {e}")

def extract_products(data):
    if isinstance(data, dict):
        for k in ['data', 'result', 'products']:
            if k in data:
                return data[k] if isinstance(data[k], list) else (data[k].get('products', []) if isinstance(data[k], dict) else [])
        if 'info' in data and 'products' in data['info']: return data['info']['products']
    return []

def extract_details(item):
    pid = str(item.get('goods_id') or item.get('id') or item.get('goodsId') or '')
    name = item.get('goods_name') or item.get('goodsName') or item.get('name') or 'Unknown'
    p = item.get('sale_price') or item.get('retailPrice') or item.get('price')
    price = p.get('amountWithSymbol', 'N/A') if isinstance(p, dict) else (f"₹{p}" if isinstance(p, (int, float)) else str(p))
    img = item.get('goods_img') or item.get('main_image') or item.get('mainImage')
    image = f"https:{img}" if img and img.startswith("//") else img
    return {'pid': pid, 'name': name, 'price': price, 'image': image, 'link': f"https://www.sheinindia.in/product-p-{pid}.html"}

async def check_api(provider):
    if not API_KEY: return None
    headers = {"x-rapidapi-key": API_KEY, "x-rapidapi-host": provider['host']}
    try:
        response = requests.get(provider['url'], headers=headers, params=provider['params'], timeout=20)
        if response.status_code == 200:
            return extract_products(response.json())
        logger.warning(f"❌ {provider['name']}: {response.status_code}")
    except Exception as e:
        logger.error(f"🚨 {provider['name']} Error: {e}")
    return None

async def main_loop():
    global first_run, current_provider_index
    if not TELEGRAM_TOKEN or not CHAT_ID or not API_KEY:
        logger.error("❌ MISSING ENV VARS: Set TELEGRAM_TOKEN, CHAT_ID, and API_KEY in Zeabur!")
        return

    while True:
        provider = PROVIDERS[current_provider_index]
        logger.info(f"Testing {provider['name']}...")
        products = await check_api(provider)
        
        if products is None:
            current_provider_index = (current_provider_index + 1) % len(PROVIDERS)
            logger.info(f"Switched to {PROVIDERS[current_provider_index]['name']}")
        else:
            if not products: logger.warning(f"⚠️ No items found.")
            for item in products:
                d = extract_details(item)
                if d['pid'] and d['pid'] not in seen_ids:
                    seen_ids.add(d['pid'])
                    if not first_run:
                        logger.info(f"🔥 NEW: {d['pid']}")
                        await send_alert(**d)
            if first_run: await send_startup(provider['name']); first_run = False
        
        save_seen_ids()
        await asyncio.sleep(CHECK_INTERVAL)

if __name__ == '__main__':
    threading.Thread(target=start_dummy_server, daemon=True).start()
    logger.info("🚀 Advanced Bot Started...")
    asyncio.run(main_loop())
