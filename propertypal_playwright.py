import asyncio
import json
import os
import time
import requests
from playwright.async_api import async_playwright
from playwright_stealth import stealth_async

# === НАСТРОЙКИ ===
BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHANNEL_ID = os.environ.get("CHANNEL_ID")

if not BOT_TOKEN or not CHANNEL_ID:
    print("❌ Ошибка: Не заданы переменные окружения")
    exit(1)

URL = "https://www.propertypal.com/property-for-sale/belfast"
STATE_FILE = "propertypal_sent.json"

async def get_property_links():
    async with async_playwright() as p:
        print("🌐 Запускаем браузер с маскировкой (Stealth)...")
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        
        # 1. Включаем Stealth (маскировка от Cloudflare)
        await stealth_async(page)
        
        # 2. Добавляем реалистичные заголовки, как у настоящего браузера
        await page.set_extra_http_headers({
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "en-GB,en-US;q=0.9,en;q=0.8",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
        })

        try:
            print(f"🔗 Открываем: {URL}")
            await page.goto(URL, wait_until="domcontentloaded", timeout=30000)
            
            print("⏳ Ждём 5 секунд для прогрузки JS и обхода проверок Cloudflare...")
            await page.wait_for_timeout(5000)
            
            # Прокрутка вниз для срабатывания lazy loading
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await page.wait_for_timeout(2000)
            
            # 3. ПРОВЕРКА: не попали ли мы на страницу блокировки Cloudflare?
            html = await page.content()
            if "Just a moment..." in html or "cf-ray" in html:
                print("❌ Cloudflare всё ещё блокирует нас (страница-заглушка).")
                return []

            # 4. Сбор ссылок
            print("🔍 Ищем ссылки на объекты...")
            all_hrefs = await page.eval_on_selector_all(
                'a[href]',
                'elements => elements.map(a => a.getAttribute("href")).filter(h => h and h.startswith("/"))'
            )
            
            property_links = []
            for href in all_hrefs:
                if "/property-for-sale/" in href or "/property-to-rent/" in href:
                    clean_href = href.split("#")[0]
                    full_url = f"https://www.propertypal.com{clean_href}"
                    if full_url not in property_links:
                        property_links.append(full_url)
            
            print(f"📊 Найдено уникальных ссылок на объекты: {len(property_links)}")
            for i, link in enumerate(property_links[:3], 1):
                print(f"   {i}. {link}")
                
        except Exception as e:
            print(f"❌ Критическая ошибка: {e}")
            property_links = []
        finally:
            await browser.close()
            
        return list(dict.fromkeys(property_links))

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
        "disable_web_page_preview": False
    }
    response = requests.post(url, json=payload)
    if response.status_code == 200:
        print(f"✅ Отправлено в Telegram")
    else:
        print(f"⚠️ Ошибка Telegram: {response.text}")

async def main():
    print("🚀 Запуск парсера PropertyPal (Anti-Cloudflare)...")
    current_links = await get_property_links()
    
    if not current_links:
        print("❌ Ссылки не найдены. Возможно, Cloudflare заблокировал IP GitHub Actions.")
        return
    
    sent = load_sent()
    new_links = [link for link in current_links if link not in sent]
    
    if new_links:
        print(f"\n🆕 Новых объявлений: {len(new_links)}. Отправляем...")
        for link in new_links:
            send_to_telegram(link)
            sent.add(link)
            await asyncio.sleep(1.5)
        
        save_sent(sent)
        print("\n🎉 Готово!")
    else:
        print("\n💤 Новых объявлений нет.")

if __name__ == "__main__":
    asyncio.run(main())
