import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src", "database"))

from db import get_db
from models import Meme

INPUT_FILE = os.path.join(os.path.dirname(__file__), "meme_ids.txt")

TEXT_MEMES = [
    "дедлайн сдан, душа свободна",
    "задание выполнено. можно есть.",
]


def seed():
    if not os.path.exists(INPUT_FILE):
        print(f"Файл '{INPUT_FILE}' не найден.")
        print("Сначала запусти collect_meme_ids.py и отправь мемы боту.")
        return

    db = get_db()
    added = 0
    skipped = 0

    try:
        with open(INPUT_FILE, encoding="utf-8") as f:
            file_ids = [line.strip() for line in f if line.strip()]

        print(f"Найдено file_id: {len(file_ids)}")

        for file_id in file_ids:
            exists = db.query(Meme).filter(Meme.content == file_id).first()
            if exists:
                print(f"  пропуск (уже есть): {file_id[:30]}...")
                skipped += 1
                continue

            db.add(Meme(type="photo", content=file_id))
            added += 1
            print(f"  добавлен: {file_id[:30]}...")

        for text in TEXT_MEMES:
            exists = db.query(Meme).filter(Meme.content == text).first()
            if exists:
                skipped += 1
                continue

            db.add(Meme(type="text", content=text))
            added += 1
            print(f"  добавлен текст: {text}")

        db.commit()
        print(f"\nГотово! Добавлено: {added}, пропущено дублей: {skipped}")

    except Exception as e:
        print(f"Ошибка: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    seed()
