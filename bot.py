import requests
from bs4 import BeautifulSoup
import time
import asyncio
import os
import re
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup

# --- CONFIGURATION ---
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('CHAT_ID')
TARGET_URL = 'https://www.sheinindia.in/c/sverse-5939-37961'
CHECK_INTERVAL = 300 

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Mobile Safari/537.36',
    'Accept-Language': 'en-US,en;q=0.9',
    'Referer': 'https://www.sheinindia.in/'
}

seen_products = set()
first_run = True

async def send_telegram_alert(product_link):
    if not TELEGRAM_TOKEN or not CHAT_ID: return
    bot = Bot(token=TELEGRAM_TOKEN)
    keyboard = [[InlineKeyboardButton("🔥 OPEN PRODUCT", url=product_link)]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    caption = f"🚨 **NEW SHEINVERSE DROP!**\n\n👇 Check it out below:"
    try:
        await bot.send_message(chat_id=CHAT_ID, text=caption, parse_mode='Markdown', reply_markup=reply_markup)
    except Exception as e:
        print(f"Telegram Error: {e}")

def check_for_new_products():
    global first_run
    print(f"Checking: {TARGET_URL}...")
    try:
        response = requests.get(TARGET_URL, headers=HEADERS, timeout=20)
        if response.status_code != 200: return
        soup = BeautifulSoup(response.text, 'html.parser')
        all_links = soup.find_all('a', href=True)
        for link in all_links:
            href = link['href']
            if '-p-' in href or '/p/' in href:
                full_url = "https:" + href if href.startswith('//') else ("https://www.sheinindia.in" + href if not href.startswith('http') else href)
                try:
                    product_id = re.search(r'-p-(\d+)', full_url).group(1)
                    if product_id not in seen_products:
                        seen_products.add(product_id)
                        if not first_run:
                            print(f"New Drop: {full_url}")
                            asyncio.run(send_telegram_alert(full_url))
                except: continue
        if first_run:
            print(f"Initialized. Tracking {len(seen_products)} items.")
            first_run = False
    except Exception as e: print(f"Error: {e}")

if __name__ == '__main__':
    print("SheinIndia Monitor Started...")
    while True:
        check_for_new_products()
        time.sleep(CHECK_INTERVAL)
