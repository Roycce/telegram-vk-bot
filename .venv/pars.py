import asyncio
import json
import logging
import os

import aiohttp
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import Message, URLInputFile
from dotenv import load_dotenv

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Загрузка токенов из переменных окружения
load_dotenv()  # Загружает переменные из .env
ACCESS_TOKEN = os.getenv("VK_ACCESS_TOKEN")
OWNER_ID = os.getenv("VK_OWNER_ID")
TG_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# Проверка загрузки переменных окружения
if not all([ACCESS_TOKEN, OWNER_ID, TG_TOKEN, CHAT_ID]):
    logger.error("Не удалось загрузить одну или несколько переменных окружения.")
    exit(1)

bot = Bot(token=TG_TOKEN)
dp = Dispatcher()


def load_last_post_id():
    try:
        with open("last_post_id.json", "r") as file:
            data = json.load(file)
            return data.get("last_post_id")
    except FileNotFoundError:
        return None


def save_last_post_id(last_post_id):
    with open("last_post_id.json", "w") as file:
        json.dump({"last_post_id": last_post_id}, file)

last_post_id = load_last_post_id()

async def send_to_telegram(message, image_url=None):
    """Отправляет сообщение в Telegram."""
    try:
        if image_url:
            logger.info(f"Отправка фото в Telegram: {image_url}")
            photo = URLInputFile(image_url)
            await bot.send_photo(
                chat_id=CHAT_ID,
                photo=photo,
                caption=message
            )
        else:
            logger.info(f"Отправка текстового сообщения в Telegram: {message}")
            await bot.send_message(chat_id=CHAT_ID, text=message)
    except Exception as e:
        logger.error(f"Ошибка при отправке сообщения в Telegram: {e}")


async def check_new_posts():
    global last_post_id

    url = "https://api.vk.com/method/wall.get"
    params = {
        "access_token": ACCESS_TOKEN,
        "owner_id": OWNER_ID,
        "filter": "all",
        "count": 5,
        "v": "5.131"
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as response:
                data = await response.json()
                logger.debug(f"Ответ от VK API: {data}")  # Логируем ответ

                if 'response' not in data:
                    logger.error(f"Ошибка в ответе VK API: {data}")
                    return

                for item in data['response'].get('items', []):
                    if "🔔" in item['text']:
                        if last_post_id is None or item['id'] > last_post_id:
                            for attachment in item.get('attachments', []):
                                if attachment['type'] == 'photo':
                                    photo_sizes = attachment['photo']['sizes']
                                    best_size = max(
                                        photo_sizes,
                                        key=lambda x: x['width'] * x['height']
                                    )
                                    photo_url = best_size['url']

                                    message = f"{item['text']}"
                                    await send_to_telegram(message, photo_url)

                            last_post_id = item['id']
                            save_last_post_id(last_post_id)  # Сохраняем новый last_post_id
    except Exception as e:
        logger.error(f"Ошибка при проверке новых постов: {e}")

async def monitor_posts():
    while True:
        await check_new_posts()
        print("Ждём новых постов")
        await asyncio.sleep(60)

@dp.message(Command("start"))
async def on_start(msg: Message):
    await msg.answer("Бот запущен и готов к работе!")

async def main():
    logger.info("Бот запущен")
    try:
        asyncio.create_task(monitor_posts())
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"Ошибка в работе бота: {e}")
    finally:
        logger.info("Бот завершил работу")

if __name__ == '__main__':
    asyncio.run(main())