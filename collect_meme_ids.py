import asyncio
import logging
import os
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
OUTPUT_FILE = "meme_ids.txt"

logging.basicConfig(level=logging.WARNING)  

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

collected = 0


@dp.message(F.photo)
async def handle_photo(message: Message):
    global collected

    file_id = message.photo[-1].file_id

    with open(OUTPUT_FILE, "a", encoding="utf-8") as f:
        f.write(file_id + "\n")

    collected += 1
    await message.reply(f"✅ Сохранено ({collected} шт.)\n<code>{file_id}</code>", parse_mode="HTML")


@dp.message(F.text == "/count")
async def handle_count(message: Message):
    await message.reply(f"Собрано file_id: {collected}")


@dp.message(F.text == "/done")
async def handle_done(message: Message):
    await message.reply(f"Готово! Всего собрано: {collected} мемов.\nТеперь запускай seed_memes.py")


async def main():
    print(f"Бот запущен. Отправляй картинки в Telegram.")
    print(f"file_id сохраняются в '{OUTPUT_FILE}'")
    print(f"Команды: /count — сколько собрано, /done — завершить")
    print(f"Чтобы остановить: Ctrl+C\n")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
