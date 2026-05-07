import easyocr
import os
import re
from typing import Optional, Dict, Any
from dataclasses import dataclass
from datetime import datetime

reader = easyocr.Reader(['ru', 'en'])


def ocr_photo(photo_path):
    try:
        if not os.path.exists(photo_path):
            print(f"Файл не найден: {photo_path}")
            return ""

        result = reader.readtext(photo_path)

        text_lines = []
        for detection in result:
            text = detection[1]
            confidence = detection[2]
            if confidence > 0.5:
                text_lines.append(text)

        return "\n".join(text_lines)

    except Exception as e:
        print(f"Ошибка OCR: {e}")
        return ""


def parse_schedule_from_photo(text):
    lessons = []
    lines = text.split('\n')

    day_pattern = r'\b(пн|вт|ср|чт|пт|сб|вс)\b'
    week_type_pattern = r'\b(odd|even|both)\b'

    # Паттерн для времени: 5:00-6:30 или 5:00 - 6:30 или 12:00-13:30
    time_range_pattern = r'(\d{1,2}:\d{2})\s*[-–—]\s*(\d{1,2}:\d{2})'

    current_day = None

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # Ищем день недели
        day_match = re.search(day_pattern, line.lower())
        if day_match:
            current_day = day_match.group(1)
            # Удаляем день из строки, чтобы он не мешал
            line = re.sub(day_pattern, '', line, flags=re.IGNORECASE)

        # Ищем тип недели
        week_type_match = re.search(week_type_pattern, line.lower())
        week_type = week_type_match.group(1) if week_type_match else "both"
        if week_type_match:
            line = re.sub(week_type_pattern, '', line, flags=re.IGNORECASE)

        # Ищем время
        time_match = re.search(time_range_pattern, line)
        if not time_match:
            continue

        start_time = time_match.group(1)
        end_time = time_match.group(2)

        # Удаляем время из строки
        line = re.sub(time_range_pattern, '', line)

        # Оставшийся текст — это предмет и возможно аудитория
        # Убираем лишние символы
        subject = re.sub(r'[^\w\sа-яА-Я]', '', line)
        subject = re.sub(r'\s+', ' ', subject).strip()

        # Если предмет пустой — пропускаем
        if not subject or not current_day:
            continue

        lesson = {
            "day": current_day,
            "start_time": start_time,
            "end_time": end_time,
            "subject": subject[:50],
            "week_type": week_type
        }
        lessons.append(lesson)

    return lessons


@dataclass
class PhotoData:
    file_id: str
    file_unique_id: str
    width: int
    height: int
    file_size: Optional[int] = None
    uploaded_at: str = None

    def __post_init__(self):
        if not self.uploaded_at:
            self.uploaded_at = datetime.now().isoformat()


class PhotoParser:

    def __init__(self):
        self.photos_cache = {}

    def extract_photo_info(self, message) -> Optional[PhotoData]:
        try:
            if not message.photo:
                return None

            photo = message.photo[-1]

            photo_data = PhotoData(
                file_id=photo.file_id,
                file_unique_id=photo.file_unique_id,
                width=photo.width,
                height=photo.height,
                file_size=getattr(photo, 'file_size', None)
            )

            self.photos_cache[message.message_id] = photo_data
            return photo_data

        except Exception as e:
            print(f"Ошибка извлечения фото: {e}")
            return None

    def get_file_id_only(self, message) -> Optional[str]:
        photo_data = self.extract_photo_info(message)
        return photo_data.file_id if photo_data else None


# Глобальный экземпляр
photo_parser = PhotoParser()


# ===== ФУНКЦИЯ ДЛЯ ИМПОРТА В import_homework =====
def get_photo_file_id_from_message(message) -> Optional[str]:
    return photo_parser.get_file_id_only(message)


def validate_photo_file_id(file_id: str) -> bool:
    if not file_id or not isinstance(file_id, str):
        return False

    if len(file_id) < 20:
        return False

    if re.match(r'^[A-Za-z0-9\-_=\./+]+$', file_id):
        return True

    return False


def extract_photo_metadata(message) -> Optional[Dict[str, Any]]:
    photo_data = photo_parser.extract_photo_info(message)

    if photo_data:
        return {
            'file_id': photo_data.file_id,
            'file_unique_id': photo_data.file_unique_id,
            'width': photo_data.width,
            'height': photo_data.height,
            'file_size': photo_data.file_size,
            'uploaded_at': photo_data.uploaded_at
        }

    return None


def get_photo_info_by_file_id(bot, file_id: str) -> Optional[Dict[str, Any]]:
    try:
        file_info = bot.get_file(file_id)
        return {
            'file_id': file_id,
            'file_path': file_info.file_path,
            'file_size': file_info.file_size,
            'file_unique_id': file_info.file_unique_id
        }
    except Exception as e:
        print(f"Ошибка получения информации о файле: {e}")
        return None


def clear_photo_cache():
    photo_parser.clear_cache()
