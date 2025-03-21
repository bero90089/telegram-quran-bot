import os
import re
import random
import asyncio
import subprocess  # Для установки зависимостей

# ✅ Устанавливаем зависимости (если они не установлены)
try:
    import httpx
    import aiogram
    import bs4
    from aiogram import Bot, Dispatcher, types
    from aiogram.types import ParseMode, InlineKeyboardMarkup, InlineKeyboardButton
    from aiogram.utils import executor
    from aiogram.utils.callback_data import CallbackData
    from bs4 import BeautifulSoup
    from dotenv import load_dotenv
except ImportError:
    print("Устанавливаю зависимости...")
    subprocess.run(["pip", "install", "aiogram", "httpx", "beautifulsoup4", "python-dotenv"])
    import httpx
    import aiogram
    import bs4
    from aiogram import Bot, Dispatcher, types
    from aiogram.types import ParseMode, InlineKeyboardMarkup, InlineKeyboardButton
    from aiogram.utils import executor
    from aiogram.utils.callback_data import CallbackData
    from bs4 import BeautifulSoup
    from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")

bot = Bot(token=TOKEN, parse_mode=ParseMode.MARKDOWN)
dp = Dispatcher(bot)

# Кэш для хранения аятов
cache = {}

# Список подписчиков
subscribers = set()

# Коллбэки для кнопок
tafsir_callback = CallbackData("tafsir", "surah", "ayah", "index")
translation_callback = CallbackData("translation", "surah", "ayah", "translator")

# Доступные переводы (пример)
TRANSLATIONS = {
    "kuliev": "Кулиев",
    "osmanov": "Османов",
    "porohova": "Порохова"
}

# Функция получения аята и толкований
async def fetch_ayat(surah, ayah, translator="kuliev"):
    url = f"https://quran-online.ru/{surah}:{ayah}?translator={translator}"

    if (surah, ayah, translator) in cache:
        return cache[(surah, ayah, translator)]
    
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        if response.status_code != 200:
            return None
    
    soup = BeautifulSoup(response.text, "html.parser")

    # Арабский текст
    arabic_text = soup.find("div", class_="ayat-text arabic")
    arabic = arabic_text.text.strip() if arabic_text else "Аят не найден"

    # Перевод
    translation_text = soup.find("div", class_="translation")
    translation = translation_text.text.strip() if translation_text else "Перевод отсутствует"

    # Толкования
    tafsir_divs = soup.find_all("div", class_="tafsir")
    tafsirs = []

    for index, div in enumerate(tafsir_divs):
        author = div.find("strong")
        author_name = author.text.strip() if author else f"Толкователь {index + 1}"
        tafsir_text = div.text.replace(author_name, "").strip()
        tafsirs.append((author_name, tafsir_text))

    if not tafsirs:
        tafsirs.append(("Нет данных", "Толкование отсутствует"))

    cache[(surah, ayah, translator)] = (arabic, translation, tafsirs)

    return arabic, translation, tafsirs

# Команда /start
@dp.message_handler(commands=["start"])
async def send_welcome(message: types.Message):
    await message.reply(
        "Привет! Отправь номер аята в формате `2:67`, и я пришлю его текст, перевод и толкования.\n\n"
        "📌 Команды:\n"
        "`/subscribe` - получать аят дня\n"
        "`/unsubscribe` - отключить рассылку"
    )

# Команда /subscribe (подписка)
@dp.message_handler(commands=["subscribe"])
async def subscribe_user(message: types.Message):
    subscribers.add(message.chat.id)
    await message.reply("✅ Ты подписался на ежедневную рассылку аятов!")

# Команда /unsubscribe (отписка)
@dp.message_handler(commands=["unsubscribe"])
async def unsubscribe_user(message: types.Message):
    subscribers.discard(message.chat.id)
    await message.reply("❌ Ты отписался от рассылки.")

# Отправка аята дня всем подписчикам
async def send_daily_ayat():
    while True:
        await asyncio.sleep(24 * 60 * 60)  # 24 часа

        # Случайный аят (пример)
        surah = random.randint(1, 114)
        ayah = random.randint(1, 7)  # Максимальное число аятов разное

        result = await fetch_ayat(surah, ayah)
        if result:
            arabic, translation, _ = result
            text = f"📖 *Аят дня: {surah}:{ayah}*\n\n**Текст аята:**\n{arabic}\n\n**Перевод:**\n{translation}"

            for user_id in subscribers:
                try:
                    await bot.send_message(user_id, text)
                except:
                    pass  # Если пользователь заблокировал бота

# Запуск бота
if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.create_task(send_daily_ayat())  # Запускаем рассылку аятов
    executor.start_polling(dp, skip_updates=True)
