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
    print("❌ Ошибка: Не заданы переменные окружения")
    exit(1)

# Используем простой URL, который точно должен выдавать результаты
URL = "https://www.propertypal.com/property-for-sale/enniskillen/price-120000"
STATE_FILE = "propertypal_sent.json"

async def get_property_links():
    async with async_playwright() as p:
        print("🌐 Запускаем браузер...")
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1920, "height": 1080}
        )
        page = await context.new_page()
        
        try:
            print(f"🔗 Открываем: {URL}")
            await page.goto(URL, wait_until="domcontentloaded", timeout=30000)
            
            print("⏳ Ждём 5 секунд для прогрузки JavaScript...")
            await page.wait_for_timeout(5000)
            
            # 1. Пробуем прокрутить страницу вниз, чтобы сработал lazy loading
            print("📜 Прокручиваем страницу вниз...")
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await page.wait_for_timeout(2000)
            
            # 2. Пытаемся закрыть баннер cookies, если он есть
            try:
                await page.click('button:has-text("Accept"), button:has-text("Accept All"), button:has-text("I accept"), .cc-accept', timeout=3000)
                print("✅ Баннер cookies закрыт")
                await page.wait_for_timeout(1000)
            except Exception:
                print("ℹ️ Баннер cookies не найден или уже закрыт")

            # 3. Собираем ВСЕ ссылки на странице
            print("🔍 Ищем все ссылки на странице...")
            all_hrefs = await page.eval_on_selector_all(
                'a[href]',
                'elements => elements.map(a => a.getAttribute("href")).filter(h => h && h.startsWith("/"))'
            )
            
            # 4. Фильтруем только те, что ведут на объекты
            property_links = []
            #for href in all_hrefs:
            #    if "/property-for-sale/" in href or "/property-to-rent/" in href:
            #        # Убираем якоря (#) и дубликаты
            #        clean_href = href.split("#")[0]
            #        full_url = f"https://www.propertypal.com{clean_href}"
            #        if full_url not in property_links:
            #            property_links.append(full_url)
            
            print(f"📊 Всего найдено уникальных ссылок на объекты: {len(property_links)}")
            
            # Выводим первые 3 ссылки в лог для проверки
            for i, link in enumerate(property_links[:3], 1):
                print(f"   {i}. {link}")
                
        except Exception as e:
            print(f"❌ Критическая ошибка: {e}")
            property_links = []
        finally:
            await browser.close()
            
        return property_links

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
    print("🚀 Запуск парсера PropertyPal...")
    current_links = await get_property_links()
    
    if not current_links:
        print("❌ Ссылки не найдены. Возможно, сайт показывает капчу или изменил структуру.")
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
        print("\n💤 Новых объявлений нет (все уже были отправлены ранее).")

if __name__ == "__main__":
    asyncio.run(main())
