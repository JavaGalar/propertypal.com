import asyncio
import json
import os
import time
import requests
from playwright.async_api import async_playwright

# === НАСТРОЙКИ ===
BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHANNEL_ID = os.environ.get("CHANNEL_ID")

if not BOT_TOKEN or not CHANNEL_ID:
    print("❌ Ошибка: Не заданы переменные окружения BOT_TOKEN и CHANNEL_ID")
    exit(1)

# URL с сортировкой "Сначала новые"
URL = "https://www.propertypal.com/property-for-sale/belfast/sort-dateHigh"

STATE_FILE = "propertypal_sent.json"

async def get_property_links():
    async with async_playwright() as p:
        print("🌐 Запускаем Playwright Chromium...")
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        
        try:
            print(f"🔗 Открываем {URL}")
            # networkidle = ждем, пока все запросы Next.js завершатся
            await page.goto(URL, wait_until="networkidle", timeout=30000)
            
            print("⏳ Ждем появления карточек...")
            await page.wait_for_selector('a[href*="/property-for-sale/"], a[href*="/property-to-rent/"]', timeout=15000)
            
            # Небольшая пауза на отрисовку остальных карточек
            await page.wait_for_timeout(2000)
            
            print("🔍 Извлекаем ссылки...")
            links = await page.eval_on_selector_all(
                'a[href*="/property-for-sale/"], a[href*="/property-to-rent/"]',
                '''elements => elements.map(a => {
                    let href = a.getAttribute("href").split("#")[0];
                    return href.startsWith("http") ? href : "https://www.propertypal.com" + href;
                })'''
            )
            
        except Exception as e:
            print(f"❌ Ошибка при загрузке страницы: {e}")
            links = []
        finally:
            await browser.close()
        
        # Удаляем дубликаты
        unique = []
        seen = set()
        for link in links:
            if link not in seen:
                unique.append(link)
                seen.add(link)
        
        return unique

def load_sent():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return set(json.load(f))
    return set()

def save_sent(sent_set):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(list(sent_set), f)

def send_to_telegram(link):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHANNEL_ID,
        "text": f"🏡 <b>Новое объявление на PropertyPal!</b>\n\n🔗 {link}",
        "parse_mode": "HTML",
        "disable_web_page_preview": False  # Telegram сам подтянет фото и цену!
    }
    response = requests.post(url, json=payload)
    if response.status_code != 200:
        print(f"⚠️ Ошибка Telegram: {response.text}")
    else:
        print(f"✅ Отправлено: {link}")

async def main():
    print("🚀 Запуск парсера PropertyPal (Playwright)...")
    current_links = await get_property_links()
    
    if not current_links:
        print("❌ Не удалось найти ссылки. Возможно, капча или изменилась структура.")
        return
    
    print(f"📊 Всего найдено ссылок на странице: {len(current_links)}")
    
    sent = load_sent()
    new_links = [link for link in current_links if link not in sent]
    
    if new_links:
        print(f"🆕 Новых объявлений: {len(new_links)}. Отправляем в Telegram...")
        for link in new_links:
            send_to_telegram(link)
            sent.add(link)
            time.sleep(1.5)
        
        save_sent(sent)
        print("🎉 Готово!")
    else:
        print("💤 Новых объявлений нет.")

if __name__ == "__main__":
    asyncio.run(main())
