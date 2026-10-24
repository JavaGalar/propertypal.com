import os
import requests

# Читаем переменные из GitHub Secrets
BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHANNEL_ID = os.environ.get("CHANNEL_ID")

def main():
    print("🔍 Проверка переменных окружения...")
    if not BOT_TOKEN or not CHANNEL_ID:
        print("❌ ОШИБКА: Переменные BOT_TOKEN или CHANNEL_ID не заданы в Secrets!")
        print(f"BOT_TOKEN есть: {bool(BOT_TOKEN)}")
        print(f"CHANNEL_ID есть: {bool(CHANNEL_ID)}")
        exit(1)
    
    print(f"✅ Переменные найдены. Отправляем тест в {CHANNEL_ID}...")
    
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHANNEL_ID,
        "text": "✅ <b>Тест успешен!</b>\n\nGitHub Actions работает, бот подключен и готов к парсингу PropertyPal. 🏡",
        "parse_mode": "HTML"
    }
    
    response = requests.post(url, json=payload)
    
    if response.status_code == 200:
        print("🎉 СООБЩЕНИЕ УСПЕШНО ОТПРАВЛЕНО В TELEGRAM!")
    else:
        print(f"❌ ОШИБКА ОТПРАВКИ: Код {response.status_code}")
        print(f"Ответ Telegram API: {response.text}")

if __name__ == "__main__":
    main()
